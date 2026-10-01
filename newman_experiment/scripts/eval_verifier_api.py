#!/usr/bin/env python3
"""API models as zero-shot verifiers on the fixed SFT test pairs (user request 2026-10-01).

The same input as the trained verifiers: the exact chat messages the local verifiers get (build_messages: system =
the verifier system prompt, user = the rendered user prompt) are sent as Responses `input` messages with the same roles
(no `instructions` field, no extra text), and the same strict parse (`aligned` / `not_aligned` after stripping whitespace, anything else invalid and wrong).
Request settings come from api_verifier in the config; only configured fields are sent, and an auth / model /
parameter error stops the run (no silent fallback). Each answer is appended as soon as it returns, so rerunning with
the same --run_name continues. A response cut at max_output_tokens is kept and parsed like any other (normally invalid).
A lenient parse (lower case, quotes / backticks / bold / final period removed) is reported beside the strict one.

Usage (from newman_experiment/, `source env.sh`):
  python scripts/eval_verifier_api.py --config configs/verifier_common.yaml --model gpt-5.6-sol [--run_name ...] [--limit N]
Output: outputs/<run_name>/{predictions_raw.jsonl, predictions.jsonl, generation_meta.json, metrics.json},
  run_name = verifier_api_<model>_seed42_<YYYYmmdd_HHMMSS> (Asia/Seoul).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman.common import (  # noqa: E402
    REPO_ROOT,
    append_jsonl,
    default_run_name,
    git_state,
    load_config,
    load_dotenv,
    now_iso,
    read_jsonl,
    rel,
    resolve,
    sha256_file,
    sha256_text,
    write_json,
    write_jsonl,
)
from newman.metrics import bootstrap_ci, verifier_metrics  # noqa: E402
from newman.taxonomy import Taxonomy  # noqa: E402
from newman.verifier_format import _vc, build_messages, load_verifier_prompt, parse_prediction  # noqa: E402


def lenient(text: str | None) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"^[`*\"']+|[`*\"'.]+$", "", t).strip()
    return parse_prediction(t)


async def run(cfg, model: str, rows, prompt, taxonomy, out_file: Path, done: set) -> None:
    from tutee_rl.clients import RewardExecutionError, _backoff, classify_error, openai_api_client, responses_call

    av = cfg["api_verifier"]
    client = openai_api_client(float(av["request_timeout_s"]), int(av["concurrency"]), 600.0)
    sem = asyncio.Semaphore(int(av["concurrency"]))

    async def one(row):
        msgs = build_messages(prompt, taxonomy, row, with_target=False)
        payload = {"model": model,
                   "input": [{"role": m["role"], "content": [{"type": "input_text", "text": m["content"]}]} for m in msgs],
                   "max_output_tokens": int(av["max_output_tokens"])}
        sent_sha = sha256_text(json.dumps([[m["role"], m["content"]] for m in msgs], ensure_ascii=False))
        if av.get("reasoning_effort"):
            payload["reasoning"] = {"effort": av["reasoning_effort"]}
        failures = []
        for attempt in range(int(av["max_attempts"])):
            async with sem:
                try:
                    api = await responses_call(client, payload, float(av["request_timeout_s"]))
                except Exception as exc:  # noqa: BLE001
                    retryable, kind = classify_error(exc)
                    failures.append(f"{kind}: {str(exc)[:200]}")
                    if not retryable:
                        raise RewardExecutionError(f"{model} fatal error {kind}: {exc}") from exc
                    api = None
            if api is not None and (api["status"] == "completed" or api["incomplete_reason"] == "max_output_tokens"):
                append_jsonl(out_file, [{"pair_id": row["pair_id"], "messages_sha256": sent_sha, "raw_output": api["output_text"],
                                         "truncated": api["incomplete_reason"] == "max_output_tokens", "status": api["status"],
                                         "usage": api["usage"], "response_id": api["response_id"], "request_id": api["request_id"],
                                         "latency_s": api["latency_s"], "attempts": attempt + 1, "failures": failures}])
                return
            if api is not None:
                failures.append(f"incomplete: {api['incomplete_reason']}")
            await _backoff(attempt)
        raise RewardExecutionError(f"{model} {row['pair_id']} failed: {failures[-3:]}")

    await asyncio.gather(*[one(r) for r in rows if r["pair_id"] not in done])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default="configs/verifier_common.yaml")
    p.add_argument("--model", required=True)
    p.add_argument("--run_name", default=None, help="continue an existing run")
    p.add_argument("--override", action="append", default=[], help="a.b.c=value, e.g. data_dir=data/prepared/sft_all_type_negatives_test")
    p.add_argument("--limit", type=int, default=None, help="smoke: first N test rows (run name starts with smoke_)")
    args = p.parse_args()
    cfg = load_config(args.config, args.override)
    av = cfg["api_verifier"]
    if not args.limit and args.model not in av["models"]:
        print(f"refusing to start: {args.model} is not in api_verifier.models {av['models']}", file=sys.stderr)
        return 2
    load_dotenv(REPO_ROOT / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set (tutee_error/.env)", file=sys.stderr)
        return 2
    taxonomy = Taxonomy.load(resolve(cfg["taxonomy"]))
    prompt = load_verifier_prompt(cfg["prompts"]["system"], cfg["prompts"]["user"])
    data_path = resolve(cfg["data_dir"]) / cfg["evaluation"]["split_file"]
    rows = read_jsonl(data_path)
    rows = rows[: args.limit] if args.limit else rows
    if any(r["region"] != "test" for r in rows):
        raise SystemExit(f"{data_path} is not the test region")
    experiment = ("smoke_" if args.limit else "") + f"verifier_api_{args.model}"
    run_name = args.run_name or default_run_name(experiment, int(cfg["seed"]))
    out_dir = resolve(cfg["training"]["output_root"]) / run_name
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_file = out_dir / "predictions_raw.jsonl"
    done = {r["pair_id"] for r in read_jsonl(raw_file)} if raw_file.exists() else set()
    started = now_iso()
    print(f"{run_name}: {len(rows) - len(done)} of {len(rows)} rows to request", flush=True)
    asyncio.run(run(cfg, args.model, rows, prompt, taxonomy, raw_file, done))

    by_id = {r["pair_id"]: r for r in read_jsonl(raw_file)}
    # the sent messages must equal the local verifiers' inference messages (same prompt files, same rendering)
    expected = {r["pair_id"]: sha256_text(json.dumps([[m["role"], m["content"]] for m in build_messages(prompt, taxonomy, r, with_target=False)],
                                                     ensure_ascii=False)) for r in rows}
    mismatch = [pid for pid, rec in by_id.items() if pid in expected and rec.get("messages_sha256") != expected[pid]]
    if mismatch:
        raise SystemExit(f"{len(mismatch)} rows were sent with messages that differ from the current verifier prompt: {mismatch[:3]}")
    preds = []
    for r in rows:
        api = by_id[r["pair_id"]]
        pred = parse_prediction(api["raw_output"])
        preds.append({**r, "raw_output": api["raw_output"], "truncated": api["truncated"], "prediction": pred,
                      "prediction_lenient": lenient(api["raw_output"]), "correct": pred == r["target"]})
    write_jsonl(out_dir / "predictions.jsonl", preds)
    ev = cfg["evaluation"]
    metrics = verifier_metrics(preds, int(ev["min_support"]))
    metrics["test_loss"] = None
    metrics["bootstrap_ci_question_groups"] = bootstrap_ci(preds, int(ev["bootstrap_samples"]), int(cfg["seed"]),
                                                               metrics=("accuracy", "macro_f1", "pair_accuracy"))
    lenient_rows = [{**r, "prediction": r["prediction_lenient"], "correct": r["prediction_lenient"] == r["target"]} for r in preds]
    lm = verifier_metrics(lenient_rows, int(ev["min_support"]))
    metrics["lenient_parse"] = {k: lm[k] for k in ("accuracy", "macro_f1", "negative_recall", "negative_false_acceptance",
                                                   "positive_recall", "invalid_rate", "pair_accuracy")}
    usage = [by_id[r["pair_id"]].get("usage") or {} for r in rows]
    gen_meta = {"kind": "api_verifier", "model": args.model, "run_name": run_name, "rows": len(rows), "started_at": started,
                "finished_at": now_iso(), "timezone": "Asia/Seoul",
                "request": {"max_output_tokens": av["max_output_tokens"], "reasoning_effort": av["reasoning_effort"] or "not sent (model default)",
                            "temperature": "not sent", "instructions": "not sent",
                            "input": "build_messages(...) as role messages: system = verifier system prompt, user = rendered verifier user prompt",
                            "messages_identical_to_local_verifier": True},
                "prompt": {k: prompt[k] for k in ("system_path", "user_path", "system_sha256", "user_sha256")},
                "taxonomy_sha256": taxonomy.sha256, "data": {"path": rel(data_path), "sha256": sha256_file(data_path), "limit": args.limit},
                "truncated": sum(1 for r in preds if r["truncated"]),
                "usage_total": {k: sum(u.get(k) or 0 for u in usage) for k in ("input_tokens", "output_tokens")},
                "git": git_state()}
    write_json(out_dir / "generation_meta.json", gen_meta)
    write_json(out_dir / "metrics.json", {"name": run_name, "checkpoint": f"api:{args.model}", "metrics": metrics,
                                          "generation": gen_meta, "data_sha256": gen_meta["data"]["sha256"]})
    print(f"{run_name}: accuracy {metrics['accuracy']:.4f} · macro-F1 {metrics['macro_f1']:.4f} · neg. false acceptance "
          f"{metrics['negative_false_acceptance']:.4f} · invalid {metrics['invalid_rate']:.4f} (lenient invalid "
          f"{metrics['lenient_parse']['invalid_rate']:.4f}) -> {rel(out_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
