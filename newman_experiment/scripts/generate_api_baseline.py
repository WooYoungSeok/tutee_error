#!/usr/bin/env python3
"""API baselines on the Student test conditions (plan 10.1).

The same Student input as the trained models (system = the instruction with the condition's (N, E) names and
definitions, user = the question), no per-problem error description, api_baselines.samples_per_condition
independent samples per condition through the Responses API. Only configured settings are sent; an auth / model /
parameter error stops the run (never a silent fallback to other settings). Every sample is appended as soon as it
returns, so a rerun continues where it stopped. A response cut at max_output_tokens is kept as a truncated sample
(scored with the truncation penalty, as a local rollout at the length limit).

Usage (from newman_experiment/):
  python scripts/generate_api_baseline.py --config configs/student_likeness.yaml --model gpt-5.6-sol [--limit N]
Output: outputs/api_baselines/<model>/{completions.jsonl, generation_meta.json}; then
  python scripts/evaluate_student.py --config ... --out outputs/<run>/test_eval --api_dirs outputs/api_baselines/<model>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman import approvals, preflight  # noqa: E402
from newman.common import REPO_ROOT, append_jsonl, load_config, load_dotenv, now_iso, read_jsonl, resolve, sha256_text, write_json  # noqa: E402
from newman.taxonomy import Taxonomy  # noqa: E402
from newman.verifier_format import load_student_template, student_messages  # noqa: E402


async def run(cfg, model: str, rows, taxonomy, template, out_file: Path, done: set) -> None:
    from tutee_rl.clients import RewardExecutionError, _backoff, classify_error, openai_api_client, responses_call

    ab = cfg["api_baselines"]
    client = openai_api_client(float(ab["request_timeout_s"]), int(ab["concurrency"]), 600.0)
    sem = asyncio.Semaphore(int(ab["concurrency"]))

    async def one(row, k):
        msgs = student_messages(template, taxonomy, row)
        payload = {"model": model, "instructions": msgs[0]["content"],
                   "input": [{"role": "user", "content": [{"type": "input_text", "text": msgs[1]["content"]}]}],
                   "max_output_tokens": int(ab["max_output_tokens"])}
        if ab.get("reasoning_effort"):
            payload["reasoning"] = {"effort": ab["reasoning_effort"]}
        failures = []
        for attempt in range(int(ab["max_attempts"])):
            async with sem:
                try:
                    api = await responses_call(client, payload, float(ab["request_timeout_s"]))
                except Exception as exc:  # noqa: BLE001
                    retryable, kind = classify_error(exc)
                    failures.append(f"{kind}: {str(exc)[:200]}")
                    if not retryable:
                        raise RewardExecutionError(f"{model} fatal error {kind}: {exc}") from exc
                    api = None
            if api is not None and (api["status"] == "completed" or api["incomplete_reason"] == "max_output_tokens"):
                usage = api["usage"] or {}
                append_jsonl(out_file, [{"condition_id": row["condition_id"], "k": k, "text": api["output_text"],
                                         "truncated": api["incomplete_reason"] == "max_output_tokens", "status": api["status"],
                                         "incomplete_reason": api["incomplete_reason"], "output_tokens": usage.get("output_tokens"),
                                         "usage": usage, "response_id": api["response_id"], "request_id": api["request_id"],
                                         "latency_s": api["latency_s"], "attempts": attempt + 1, "failures": failures}])
                return
            if api is not None:
                failures.append(f"incomplete: {api['incomplete_reason']}")
            await _backoff(attempt)
        raise RewardExecutionError(f"{model} {row['condition_id']} k={k} failed: {failures[-3:]}")

    n = int(ab["samples_per_condition"])
    await asyncio.gather(*[one(r, k) for r in rows for k in range(n) if (r["condition_id"], k) not in done])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--out_root", default="outputs/api_baselines")
    args = p.parse_args()
    cfg = load_config(args.config)
    ab = cfg["api_baselines"]
    problems = preflight.required_problems(cfg, ["api_baselines.models", "api_baselines.reasoning_effort", "api_baselines.max_output_tokens"])
    problems += approvals.problems(["taxonomy_definitions", "student_prompt"],
                                   {"student_prompt": [cfg["prompts"]["student"]], "taxonomy_definitions": [cfg["paths"]["taxonomy"]]})
    problems += preflight.data_problems(f"{cfg['paths']['prepared_dir']}/meta.json")
    if problems and not args.limit:
        print("refusing to start:\n  - " + "\n  - ".join(problems), file=sys.stderr)
        return 2
    if not args.limit and args.model not in ab["models"]:
        print(f"refusing to start: {args.model} is not in api_baselines.models {ab['models']}", file=sys.stderr)
        return 2
    load_dotenv(REPO_ROOT / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set (tutee_error/.env)", file=sys.stderr)
        return 2
    rows = read_jsonl(resolve(cfg["paths"]["prepared_dir"]) / f"{cfg['evaluation']['split']}.jsonl")
    rows = rows[: args.limit] if args.limit else rows
    taxonomy = Taxonomy.load(resolve(cfg["paths"]["taxonomy"]))
    template = load_student_template(cfg["prompts"]["student"])
    out_dir = resolve(args.out_root) / (args.model + (f"_limit{args.limit}" if args.limit else ""))
    out_file = out_dir / "completions.jsonl"
    done = {(r["condition_id"], r["k"]) for r in read_jsonl(out_file)} if out_file.exists() else set()
    started = now_iso()
    asyncio.run(run(cfg, args.model, rows, taxonomy, template, out_file, done))
    recs = read_jsonl(out_file)
    write_json(out_dir / "generation_meta.json", {
        "kind": "api", "model": args.model, "conditions": len(rows), "rollouts": len(recs), "started_at": started, "finished_at": now_iso(),
        "timezone": "Asia/Seoul", "request": {"max_output_tokens": ab["max_output_tokens"], "reasoning_effort": ab["reasoning_effort"],
                                              "temperature": "not sent", "samples_per_condition": ab["samples_per_condition"]},
        "student_prompt_sha256": sha256_text(template), "taxonomy_sha256": taxonomy.sha256,
        "truncated": sum(1 for r in recs if r["truncated"]),
        "usage_total": {k: sum((r.get("usage") or {}).get(k) or 0 for r in recs) for k in ("input_tokens", "output_tokens")},
        "prepared_test": json.dumps({"path": cfg["paths"]["prepared_dir"], "limit": args.limit})})
    print(f"{args.model}: {len(recs)} samples -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
