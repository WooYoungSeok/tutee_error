#!/usr/bin/env python3
"""Evaluate an OpenAI API model as the verifier on a fixed split (reference point, no training).

Same system/user messages and the same exact-match scoring as eval_descriptive_verifier.py:
an answer counts only if, after stripping whitespace, it is exactly `aligned` or
`not_aligned`. Differences from the local evaluation, recorded in metrics.json:
  * decoding is the API's (no greedy option; temperature is left unset);
  * max_output_tokens includes reasoning tokens, so it is much larger than max_new_tokens.

Every response is appended to outputs/<name>/api_responses.jsonl as it arrives, so a
re-run with the same settings only calls the rows that are still missing. Rows whose
call failed are not scored: the script stops and a re-run retries them.

Usage (from verifier_sft/, OPENAI_API_KEY in ../.env):
    python eval_api_verifier.py --api_model gpt-5.6-sol --name gpt-5.6-sol --limit 10   # pilot
    python eval_api_verifier.py --api_model gpt-5.6-sol --name gpt-5.6-sol
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from errdesc.runner import _response_to_record, load_dotenv  # noqa: E402
from eval_descriptive_verifier import score_and_report  # noqa: E402
from verifier_common import build_messages, load_config, load_prompt, read_jsonl, resolve  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=None)
    parser.add_argument("--api_model", required=True, help="e.g. gpt-5.6-sol")
    parser.add_argument("--name", required=True, help="output name, e.g. gpt-5.6-sol")
    parser.add_argument("--split", default=None, help="default: evaluation.split (test)")
    parser.add_argument("--ablation", default="none", choices=["none", "no_solution", "description_only"])
    parser.add_argument("--limit", type=int, default=None, help="pilot: first N rows")
    parser.add_argument("--reasoning_effort", default=None, help="default: the model's own default")
    parser.add_argument("--max_output_tokens", type=int, default=4000, help="includes reasoning tokens")
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=180, help="seconds per request")
    parser.add_argument("--max_retries", type=int, default=4, help="SDK retries on 429 / 5xx / timeouts")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    split = args.split or config["evaluation"]["split"]
    data_path = resolve(config["output"]["data_dir"]) / f"{split}.jsonl"
    rows = read_jsonl(data_path)
    if args.limit:
        rows = rows[: args.limit]
    prompt = load_prompt(config, ablation=args.ablation)

    settings = {
        "api_model": args.api_model,
        "reasoning_effort": args.reasoning_effort,
        "max_output_tokens": args.max_output_tokens,
        "ablation": args.ablation,
        "system_sha256": prompt["system_sha256"],
        "user_sha256": prompt["user_sha256"],
    }
    cache_path = resolve(config["evaluation"]["output_dir"]) / args.name / "api_responses.jsonl"
    done: dict[str, dict[str, Any]] = {}
    if cache_path.exists():
        for rec in read_jsonl(cache_path):
            if rec["settings"] == settings and rec.get("error") is None:
                done[rec["pair_id"]] = rec
    todo = [r for r in rows if r["pair_id"] not in done]
    print(f"{len(rows)} rows · {len(rows) - len(todo)} cached · {len(todo)} to call · model {args.api_model}")

    if todo:
        load_dotenv(HERE.parent / ".env")
        from openai import OpenAI

        client = OpenAI(max_retries=args.max_retries, timeout=args.timeout)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        lock = threading.Lock()
        counter = {"n": 0}

        def call(row: dict[str, Any]) -> None:
            payload: dict[str, Any] = {
                "model": args.api_model,
                "input": build_messages(prompt, row, with_target=False),
                "max_output_tokens": args.max_output_tokens,
            }
            if args.reasoning_effort:
                payload["reasoning"] = {"effort": args.reasoning_effort}
            rec: dict[str, Any] = {"pair_id": row["pair_id"], "settings": settings, "error": None}
            try:
                response = client.responses.create(**payload)
                rec.update(_response_to_record(response), response_model=getattr(response, "model", None))
            except Exception as exc:  # noqa: BLE001 - recorded; the row stays uncached and is retried next run
                rec["error"] = f"{type(exc).__name__}: {exc}"
            with lock:
                with cache_path.open("a", encoding="utf-8", newline="\n") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if rec["error"] is None:
                    done[row["pair_id"]] = rec
                counter["n"] += 1
                if counter["n"] % 25 == 0 or counter["n"] == len(todo):
                    print(f"  {counter['n']}/{len(todo)}", flush=True)

        with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
            list(pool.map(call, todo))

    missing = [r["pair_id"] for r in rows if r["pair_id"] not in done]
    if missing:
        print(f"{len(missing)} row(s) failed; not scoring. Re-run the same command to retry them. "
              f"Errors are in {cache_path}")
        return 1

    records = [done[r["pair_id"]] for r in rows]
    raw_outputs = [rec["output_text"] or "" for rec in records]
    usage = Counter()
    for rec in records:
        u = rec.get("usage") or {}
        usage["input_tokens"] += u.get("input_tokens") or 0
        usage["output_tokens"] += u.get("output_tokens") or 0
        usage["reasoning_tokens"] += (u.get("output_tokens_details") or {}).get("reasoning_tokens") or 0
    api_info = {
        "api": {
            **settings,
            "response_models": sorted({str(rec.get("response_model")) for rec in records}),
            "status_counts": dict(Counter(str(rec.get("response_status")) for rec in records)),
            "incomplete_reasons": dict(Counter(rec["incomplete_reason"] for rec in records if rec.get("incomplete_reason"))),
            "usage_totals": dict(usage),
        }
    }
    decoding = {
        "backend": "openai-responses",
        "temperature": None,
        "reasoning_effort": args.reasoning_effort or "model default",
        "max_output_tokens": args.max_output_tokens,
    }
    score_and_report(
        config, rows, raw_outputs, name=args.name, model=f"api:{args.api_model}", split=split,
        data_path=data_path, limit=args.limit, prompt=prompt, decoding=decoding, extra=api_info,
    )
    print(f"api status {api_info['api']['status_counts']} · tokens {dict(usage)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
