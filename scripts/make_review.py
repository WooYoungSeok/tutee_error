#!/usr/bin/env python3
"""Build the human review sheet (CSV + HTML) and the run summary for a run."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from errdesc.paths import FULL_POOL, OUTPUTS_DIR, REPORTS_DIR, SAMPLE_MANIFEST, ensure_dirs  # noqa: E402
from errdesc.review import REVIEW_COLUMNS, build_review_rows, render_html, summarize  # noqa: E402
from errdesc.util import read_json, read_jsonl  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", help="run id (directory name under outputs/runs/)")
    parser.add_argument("--out-dir", default=None, help="defaults to reports/")
    parser.add_argument(
        "--compare-run",
        nargs="+",
        default=None,
        metavar="RUN_ID",
        help="other run ids whose descriptions are added as extra columns, in order "
             "(e.g. --compare-run v1_run v2_run when reviewing v3)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    run_dir = OUTPUTS_DIR / "runs" / args.run_id
    parsed_path = run_dir / "parsed.jsonl"
    meta_path = run_dir / "run_meta.json"
    if not parsed_path.exists():
        raise SystemExit(f"no parsed results found: {parsed_path}")

    parsed_rows = list(read_jsonl(parsed_path))
    run_meta = read_json(meta_path) if meta_path.exists() else {"run_id": args.run_id}
    # a full run covers cases outside the fixed sample; their Q/R live in the pool
    manifest_path = FULL_POOL if run_meta.get("split") == "full" else SAMPLE_MANIFEST
    manifest = {row["sample_id"]: row for row in read_jsonl(manifest_path)}

    compares: list[tuple[str, dict]] = []
    for compare_run in args.compare_run or []:
        compare_path = OUTPUTS_DIR / "runs" / compare_run / "parsed.jsonl"
        if not compare_path.exists():
            raise SystemExit(f"no parsed results for --compare-run: {compare_path}")
        compares.append(
            (compare_run, {row["sample_id"]: row for row in read_jsonl(compare_path)})
        )

    rows = build_review_rows(parsed_rows, manifest, compares=compares)
    out_dir = Path(args.out_dir) if args.out_dir else REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    columns = list(REVIEW_COLUMNS)
    if compares:
        # name this run's own description column too, so every C column says which
        # run produced it
        own_column = f"description__{args.run_id}"
        columns[columns.index("description")] = own_column
        for row in rows:
            row[own_column] = row["description"]
        for offset, (compare_run, _) in enumerate(compares):
            columns.insert(columns.index(own_column) + 1 + offset, f"description__{compare_run}")
            for row in rows:
                row[f"description__{compare_run}"] = row["compare_descriptions"][compare_run]

    csv_path = out_dir / f"review_{args.run_id}.csv"
    # utf-8-sig so Excel opens the file with the right encoding
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    html_path = out_dir / f"review_{args.run_id}.html"
    html_path.write_text(
        render_html(
            rows,
            f"Error description review — {args.run_id}",
            self_label=args.run_id if compares else "",
        ),
        encoding="utf-8",
    )

    summary_path = out_dir / f"summary_{args.run_id}.md"
    summary_path.write_text(summarize(rows, run_meta), encoding="utf-8")

    print(f"review CSV  -> {csv_path}")
    print(f"review HTML -> {html_path}")
    print(f"summary     -> {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
