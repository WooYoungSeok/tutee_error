#!/usr/bin/env python3
"""API baseline on the Eedi test set (user request 2026-10-03: gpt-5.1), scored afterwards by rl/scripts/evaluate.py.

Same Student input as the trained models (tutee_rl.common.student_messages: system = rl/prompts/student.txt with the
misconception description, user = the problem; options hidden), sent as Responses role messages; `samples` per pair
(default 1, as the Newman API baselines, user 2026-10-02); reasoning not sent, max_output_tokens 8000. Each answer is
appended as it arrives, so a rerun continues. The text is tokenized with the policy tokenizer (+ EOS when the response
completed) so evaluate.py --stage score can read it like a local rollout.

Usage (from rl/, `source env.sh`):
  python ../distractor_rl/scripts/api_baseline_eedi.py --model gpt-5.1
Output: distractor_rl/outputs/api_baselines_eedi/test_eval/api_<model>/{api_raw.jsonl, completions.jsonl, generation_meta.json}
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parent
sys.path.insert(0, str(REPO / "rl" / "src"))

from tutee_rl.common import (  # noqa: E402
    append_jsonl, load_config, load_dotenv, read_jsonl, read_template, resolve, sha256_text, student_messages, write_json, write_jsonl,
)


async def generate(cfg, model, rows, template, raw_file, done, samples, concurrency, max_tokens):
    from tutee_rl.clients import _backoff, classify_error, openai_api_client, responses_call

    client = openai_api_client(600.0, concurrency, 600.0)
    sem = asyncio.Semaphore(concurrency)

    async def one(r, k):
        msgs = student_messages(template, r)
        payload = {"model": model, "max_output_tokens": max_tokens,
                   "input": [{"role": m["role"], "content": [{"type": "input_text", "text": m["content"]}]} for m in msgs]}
        failures = []
        for attempt in range(6):
            async with sem:
                try:
                    api = await responses_call(client, payload, 600.0)
                except Exception as exc:  # noqa: BLE001
                    retryable, kind = classify_error(exc)
                    failures.append(f"{kind}: {str(exc)[:300]}")
                    if not retryable:
                        raise
                    api = None
            if api is not None and (api["status"] == "completed" or api["incomplete_reason"] == "max_output_tokens"):
                append_jsonl(raw_file, [{"PairId": r["PairId"], "k": k, "text": api["output_text"], "status": api["status"],
                                         "truncated": api["incomplete_reason"] == "max_output_tokens", "usage": api["usage"],
                                         "response_id": api["response_id"], "request_id": api["request_id"], "attempts": attempt + 1}])
                return
            if api is not None:
                failures.append(f"incomplete: {api['incomplete_reason']}")
            await _backoff(attempt)
        raise RuntimeError(f"{model} {r['PairId']} k={k} failed: {failures[-3:]}")

    await asyncio.gather(*[one(r, k) for r in rows for k in range(samples) if (r["PairId"], k) not in done])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", required=True)
    p.add_argument("--config", default=str(HERE / "configs" / "student_likeness.yaml"))
    p.add_argument("--samples", type=int, default=1)
    p.add_argument("--concurrency", type=int, default=64)
    p.add_argument("--max_output_tokens", type=int, default=8000)
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    cfg = load_config(args.config)
    load_dotenv(REPO / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set")
    rows = read_jsonl(resolve(cfg["paths"]["prepared_dir"]) / "test.jsonl")
    rows = rows[: args.limit] if args.limit else rows
    template = read_template(cfg["prompts"]["student"])
    out = HERE / "outputs" / "api_baselines_eedi" / ("test_eval" + (f"_limit{args.limit}" if args.limit else "")) / f"api_{args.model}"
    out.mkdir(parents=True, exist_ok=True)
    raw = out / "api_raw.jsonl"
    done = {(r["PairId"], r["k"]) for r in read_jsonl(raw)} if raw.exists() else set()
    started = __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")
    asyncio.run(generate(cfg, args.model, rows, template, raw, done, args.samples, args.concurrency, args.max_output_tokens))

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(cfg["policy"]["model"])
    recs = [r for r in read_jsonl(raw) if r["k"] < args.samples]
    comps = []
    for r in recs:
        ids = tok((r["text"] or "").strip(), add_special_tokens=False)["input_ids"]
        comps.append({"PairId": r["PairId"], "k": r["k"], "token_ids": ids + ([] if r["truncated"] else [tok.eos_token_id]),
                      "finish_reason": "length" if r["truncated"] else "stop"})
    write_jsonl(out / "completions.jsonl", comps)
    write_json(out / "generation_meta.json", {
        "kind": "api", "model": args.model, "pairs": len(rows), "rollouts": len(recs), "samples_per_pair": args.samples,
        "started_at": started, "request": {"reasoning_effort": "not sent", "temperature": "not sent", "max_output_tokens": args.max_output_tokens},
        "student_prompt_sha256": sha256_text(template), "split": "test", "truncated": sum(r["truncated"] for r in recs),
        "usage_total": {k: sum((r.get("usage") or {}).get(k) or 0 for r in recs) for k in ("input_tokens", "output_tokens")},
        "note": "text tokenized with the policy tokenizer (+EOS if completed) for rl/scripts/evaluate.py --stage score"})
    print(f"{args.model}: {len(recs)} samples -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
