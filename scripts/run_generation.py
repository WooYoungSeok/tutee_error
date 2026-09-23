#!/usr/bin/env python3
"""Generate error descriptions (C) for the fixed sample.

Examples
--------
  python scripts/run_generation.py --split dev --dry-run
  python scripts/run_generation.py --split dev --mock
  python scripts/run_generation.py --split dev --model <model-id>
  python scripts/run_generation.py --split holdout --model <model-id>
  python scripts/run_generation.py --config config/full.json --source full

`--source full` sends every case in data/full/pool.jsonl (scripts/build_full_pool.py)
instead of the fixed 200-case sample; the run id ends in `__full`.

The run is resumable: re-running the same command skips the cases that already
produced a valid response under the same prompt hash, input hash, model and
generation settings.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from errdesc.config import load_config, prompt_path  # noqa: E402
from errdesc.mock import MockClient, make_mock_call  # noqa: E402
from errdesc.paths import FULL_POOL, OUTPUTS_DIR, PROJECT_ROOT, SAMPLE_MANIFEST, ensure_dirs  # noqa: E402
from errdesc.prompt import input_hash, input_values, load_prompt, render_prompt  # noqa: E402
from errdesc.runner import (  # noqa: E402
    FatalAPIError,
    GenerationSettings,
    call_once,
    load_dotenv,
    run_batch,
)
from errdesc.util import read_jsonl, utc_now, write_json, write_jsonl  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", default=None)
    parser.add_argument(
        "--source",
        default="manifest",
        choices=["manifest", "full"],
        help="manifest: the fixed 200-case sample (default); full: data/full/pool.jsonl",
    )
    parser.add_argument(
        "--split",
        default=None,
        choices=["dev", "holdout", "all"],
        help="split of the fixed sample (default dev); not used with --source full",
    )
    parser.add_argument("--datasets", nargs="*", default=None)
    parser.add_argument(
        "--sample-ids", nargs="+", default=None, metavar="SAMPLE_ID", help="only these cases"
    )
    parser.add_argument("--model", default=None, help="explicit model id (required to call the API)")
    parser.add_argument(
        "--prompt-file",
        default=None,
        help="prompt template to use instead of the one in the config (e.g. prompts/error_description_v2.txt)",
    )
    parser.add_argument(
        "--prompt-version",
        default=None,
        help="version tag recorded with the run; defaults to the config value, "
             "or to the --prompt-file stem suffix (…_v2.txt -> v2)",
    )
    parser.add_argument("--limit", type=int, default=None, help="only the first N cases")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--concurrency", type=int, default=None)
    parser.add_argument("--max-output-tokens", type=int, default=None)
    parser.add_argument("--reasoning-effort", default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument(
        "--json-mode",
        action="store_true",
        help="ask for a JSON object response format (only if the model supports it)",
    )
    parser.add_argument("--dry-run", action="store_true", help="no API call; show what would be sent")
    parser.add_argument("--mock", action="store_true", help="no API call; use the offline mock")
    parser.add_argument(
        "--price-input",
        type=float,
        default=None,
        help="USD per 1M input tokens (only used if you confirmed the price)",
    )
    parser.add_argument("--price-output", type=float, default=None, help="USD per 1M output tokens")
    return parser.parse_args()


def load_samples(
    source: str,
    split: str,
    datasets: list[str] | None,
    limit: int | None,
    sample_ids: list[str] | None = None,
) -> list[dict]:
    if source == "full":
        if not FULL_POOL.exists():
            raise SystemExit(
                f"full pool not found: {FULL_POOL}\nRun scripts/build_full_pool.py first."
            )
        rows = list(read_jsonl(FULL_POOL))
    else:
        if not SAMPLE_MANIFEST.exists():
            raise SystemExit(
                f"sample manifest not found: {SAMPLE_MANIFEST}\nRun scripts/build_samples.py first."
            )
        rows = list(read_jsonl(SAMPLE_MANIFEST))
        if split != "all":
            rows = [r for r in rows if r.get("split") == split]
    if datasets:
        rows = [r for r in rows if r["dataset"] in datasets]
    if sample_ids:
        wanted = set(sample_ids)
        unknown = wanted - {r["sample_id"] for r in rows}
        if unknown:
            raise SystemExit(f"sample id(s) not in the selected rows: {', '.join(sorted(unknown))}")
        rows = [r for r in rows if r["sample_id"] in wanted]
    rows.sort(key=lambda r: (r["dataset"], r["sample_id"]))
    if limit:
        rows = rows[:limit]
    return rows


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    ensure_dirs()
    applied = load_dotenv(PROJECT_ROOT / ".env")
    if applied:
        print(f"loaded from .env : {', '.join(applied)} (project .env takes precedence)")

    if args.prompt_file:
        config = dict(config)
        config["prompt_file"] = args.prompt_file
    template, prompt_hash = load_prompt(prompt_path(config))
    prompt_version = args.prompt_version or (
        Path(config["prompt_file"]).stem.rsplit("_", 1)[-1]
        if args.prompt_file
        else config["prompt_version"]
    )

    gen = dict(config["generation"])
    model = args.model or config.get("model")
    settings = GenerationSettings(
        model=model or "",
        max_output_tokens=args.max_output_tokens or gen["max_output_tokens"],
        temperature=args.temperature if args.temperature is not None else gen["temperature"],
        reasoning_effort=args.reasoning_effort or gen["reasoning_effort"],
        response_format_json=args.json_mode or gen["response_format_json"],
        request_timeout_s=gen["request_timeout_s"],
        max_retries=gen["max_retries"],
        concurrency=args.concurrency or gen["concurrency"],
    )

    if args.source == "full":
        if args.split:
            raise SystemExit("--split selects part of the fixed sample; it is not used with --source full")
        split = "full"
    else:
        split = args.split or "dev"
    args.split = split
    rows = load_samples(args.source, split, args.datasets, args.limit, args.sample_ids)
    if not rows:
        raise SystemExit(f"no sample rows for source={args.source} split={split}")

    slug = (model or "unset-model").replace("/", "-").replace(":", "-")
    run_id = args.run_id or f"{prompt_version}__{slug}__{split}"
    run_dir = OUTPUTS_DIR / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_path = run_dir / "raw.jsonl"
    parsed_path = run_dir / "parsed.jsonl"

    print(f"run id        : {run_id}")
    print(f"cases         : {len(rows)} (split={args.split})")
    print(f"prompt        : {config['prompt_file']} version={prompt_version} sha256={prompt_hash[:16]}")
    print(f"model         : {model or '(NOT SET)'}")
    print(f"generation    : {settings.signature()}")
    print(f"concurrency   : {settings.concurrency}")
    print(f"output dir    : {run_dir}")

    if args.dry_run:
        example = rows[0]
        rendered = render_prompt(template, input_values(example))
        (run_dir / "dry_run_example_request.txt").write_text(rendered, encoding="utf-8")
        preview = {
            "created_at_utc": utc_now(),
            "run_id": run_id,
            "split": args.split,
            "cases": len(rows),
            "by_dataset": {
                ds: sum(1 for r in rows if r["dataset"] == ds)
                for ds in sorted({r["dataset"] for r in rows})
            },
            "model": model,
            "prompt_version": prompt_version,
            "prompt_sha256": prompt_hash,
            "generation": settings.signature(),
            "example_sample_id": example["sample_id"],
            "example_input_hash": input_hash(example),
            "example_request_chars": len(rendered),
            "total_request_chars": sum(
                len(render_prompt(template, input_values(r))) for r in rows
            ),
        }
        approx_input_tokens = preview["total_request_chars"] / 4
        preview["approx_input_tokens_rule_of_thumb"] = int(approx_input_tokens)
        if args.price_input is not None and args.price_output is not None:
            est_out = len(rows) * settings.max_output_tokens
            preview["cost_estimate_usd"] = round(
                approx_input_tokens / 1e6 * args.price_input
                + est_out / 1e6 * args.price_output,
                4,
            )
            preview["cost_estimate_note"] = (
                "Upper bound on output tokens (max_output_tokens per case). "
                "Reasoning tokens, if the model produces any, are billed as output "
                "tokens and are not predictable in advance."
            )
        else:
            preview["cost_estimate_usd"] = None
            preview["cost_estimate_note"] = (
                "No price given (--price-input / --price-output), so no cost is estimated."
            )
        write_json(run_dir / "dry_run.json", preview)
        print("")
        print(f"DRY RUN: no API call was made.")
        print(f"  by dataset      : {preview['by_dataset']}")
        print(f"  request chars   : {preview['total_request_chars']}")
        print(f"  ~input tokens   : {preview['approx_input_tokens_rule_of_thumb']} (chars/4 heuristic)")
        print(f"  cost estimate   : {preview['cost_estimate_usd']} ({preview['cost_estimate_note']})")
        print(f"  example request : {run_dir / 'dry_run_example_request.txt'}")
        print(f"  summary         : {run_dir / 'dry_run.json'}")
        return 0

    if args.mock:
        client = MockClient()
        call = make_mock_call()
        settings.model = model or "mock-model"
    else:
        if not model:
            raise SystemExit(
                "No model id is set. Pass --model <id> or set \"model\" in the config.\n"
                "No API call was made. Data preparation and --dry-run work without it."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise SystemExit(f"the openai package is required: {exc}") from exc
        import os

        if not os.environ.get("OPENAI_API_KEY"):
            raise SystemExit(
                "OPENAI_API_KEY is not set in the environment (or .env). No API call was made."
            )
        client = OpenAI(max_retries=0)  # retries are handled in runner.run_one
        call = call_once

    done = 0
    total = len(rows)

    def progress(row: dict) -> None:
        nonlocal done
        done += 1
        flag = "reuse" if row.get("reused_from_previous_run") else row.get("processing_status")
        print(f"  [{done}/{total}] {row['sample_id']} -> {flag}", flush=True)

    print("")
    try:
        results = run_batch(
            client=client,
            records=rows,
            prompt_template=template,
            prompt_hash=prompt_hash,
            prompt_version=prompt_version,
            settings=settings,
            raw_path=raw_path,
            call=call,
            on_result=progress,
        )
    except FatalAPIError as exc:
        print("")
        print(f"FATAL: {exc}")
        print("This is a configuration-level error (auth, model id or parameters).")
        print(f"Partial results (if any) are in {raw_path}")
        return 2

    by_id = {r["sample_id"]: r for r in rows}
    parsed_rows = []
    for row in sorted(results, key=lambda r: (r["dataset"], r["sample_id"])):
        record = by_id[row["sample_id"]]
        parsed = row.get("parsed") or {}
        parsed_rows.append(
            {
                "sample_id": row["sample_id"],
                "dataset": row["dataset"],
                "split": row["split"],
                "source_error_label": record["source_error_label"],
                "description": parsed.get("description"),
                "evidence_quote": parsed.get("evidence_quote"),
                "status": parsed.get("status"),
                "processing_status": row.get("processing_status"),
                "error": row.get("error", ""),
                "model": row["generation"]["model"],
                "prompt_version": row["prompt_version"],
                "prompt_hash": row["prompt_hash"],
                "input_hash": row["input_hash"],
                "response_id": row.get("response_id"),
                "request_id": row.get("request_id"),
                "usage": row.get("usage"),
                "latency_ms": row.get("latency_ms"),
                "attempts": len(row.get("attempts", [])),
                "reused_from_previous_run": row.get("reused_from_previous_run", False),
            }
        )
    write_jsonl(parsed_path, parsed_rows)

    status_counts: dict[str, int] = {}
    for row in parsed_rows:
        status_counts[row["processing_status"]] = status_counts.get(row["processing_status"], 0) + 1
    usage_totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for row in parsed_rows:
        usage = row.get("usage") or {}
        for key in usage_totals:
            value = usage.get(key)
            if isinstance(value, int):
                usage_totals[key] += value

    meta = {
        "run_id": run_id,
        "finished_at_utc": utc_now(),
        "split": args.split,
        "cases": total,
        "model": settings.model,
        "mock": bool(args.mock),
        "prompt_version": prompt_version,
        "prompt_file": config["prompt_file"],
        "prompt_sha256": prompt_hash,
        "generation": settings.signature(),
        "concurrency": settings.concurrency,
        "processing_status_counts": status_counts,
        "usage_totals": usage_totals,
        "raw_path": str(raw_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "parsed_path": str(parsed_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
    }
    write_json(run_dir / "run_meta.json", meta)

    print("")
    print(f"processing status: {status_counts}")
    print(f"token usage      : {usage_totals}")
    print(f"raw    -> {raw_path}")
    print(f"parsed -> {parsed_path}")
    print(f"meta   -> {run_dir / 'run_meta.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
