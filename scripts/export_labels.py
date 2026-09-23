#!/usr/bin/env python3
"""Export the full-run descriptions onto copies of the raw source files.

data/raw is only read. For every raw file the adapters read, a copy with one
added key per row (`generated_error_description`) is written under
data/labeled/, keeping the raw directory layout. MathEDU leave_one_out files
hold exact copies of the time_series_split rows and are labeled through them.

Also written:
data/labeled/labels.jsonl    one row per unique case: Q, R, A, C, status, evidence, source ids
data/labeled/labels.csv      the same table for Excel (utf-8-sig)
data/labeled/export_meta.json  run, prompt, model, and per-file / per-dataset counts
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from errdesc.config import load_config  # noqa: E402
from errdesc.export import (  # noqa: E402
    LABEL_FIELD,
    attach,
    attach_by_identity,
    labels_by_source_file,
    payload_counts,
    read_rows,
    row_key,
    write_rows,
)
from errdesc.paths import (  # noqa: E402
    CONFIG_DIR,
    FULL_POOL,
    FULL_RECORD_INDEX,
    LABELED_DIR,
    OUTPUTS_DIR,
    PROJECT_ROOT,
    RAW_DIR,
)
from errdesc.util import read_json, read_jsonl, utc_now, write_json, write_jsonl  # noqa: E402

MATHEDU_COPY_GLOB = "mathedu/dataset/leave_one_out/*/*.json"

TABLE_COLUMNS = [
    "dataset",
    "sample_id",
    "benchmark",
    "source_error_label",
    "description",
    "status",
    "evidence_quote",
    "processing_status",
    "question",
    "incorrect_solution",
    "source_ids",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(CONFIG_DIR / "full.json"))
    parser.add_argument("--run-id", default=None, help="default: <prompt_version>__<model>__full")
    parser.add_argument("--out-dir", default=str(LABELED_DIR))
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="export even if some eligible cases have no successful result",
    )
    return parser.parse_args()


def rel_to_raw(source_file: str) -> Path:
    path = PROJECT_ROOT / source_file
    return path.relative_to(RAW_DIR)


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    run_id = args.run_id or f"{config['prompt_version']}__{config['model']}__full"
    run_dir = OUTPUTS_DIR / "runs" / run_id
    out_dir = Path(args.out_dir).resolve()
    if out_dir == RAW_DIR.resolve() or RAW_DIR.resolve() in out_dir.parents:
        raise SystemExit("refusing to write inside data/raw")

    parsed_path = run_dir / "parsed.jsonl"
    if not parsed_path.exists():
        raise SystemExit(f"no parsed results: {parsed_path}")
    results = {row["sample_id"]: row for row in read_jsonl(parsed_path)}
    pool = list(read_jsonl(FULL_POOL))
    missing = [r["sample_id"] for r in pool if (results.get(r["sample_id"]) or {}).get("processing_status") != "ok"]
    if missing and not args.allow_missing:
        raise SystemExit(
            f"{len(missing)} of {len(pool)} cases have no successful result in {run_id} "
            f"(e.g. {missing[:3]}). Re-run the generation (it resumes) or pass --allow-missing."
        )

    index_rows = list(read_jsonl(FULL_RECORD_INDEX))
    labels = labels_by_source_file(index_rows, results, run_id)
    dataset_of = {row["source_file"]: row["dataset"] for row in index_rows}

    file_counts: dict[str, dict] = {}
    dataset_counts: dict[str, Counter] = defaultdict(Counter)
    mathedu_rows: dict[str, dict] = {}
    for source_file in sorted(labels):
        rel = rel_to_raw(source_file)
        rows, fmt = read_rows(RAW_DIR / rel)
        labeled = attach(rows, labels[source_file], source_file)
        write_rows(out_dir / rel, labeled, fmt)
        counts = payload_counts(labeled)
        file_counts[str(rel).replace("\\", "/")] = dict(sorted(counts.items()))
        dataset_counts[dataset_of[source_file]].update(counts)
        if dataset_of[source_file] == "mathedu":
            for row in labeled:
                mathedu_rows[row_key(row)] = row[LABEL_FIELD]

    copies = sorted(RAW_DIR.glob(MATHEDU_COPY_GLOB)) if mathedu_rows else []
    for path in copies:
        rel = path.relative_to(RAW_DIR)
        rows, fmt = read_rows(path)
        labeled = attach_by_identity(rows, mathedu_rows, str(rel))
        write_rows(out_dir / rel, labeled, fmt)
        file_counts[str(rel).replace("\\", "/")] = dict(sorted(payload_counts(labeled).items()))

    # one row per unique case
    table = []
    for record in pool:
        result = results.get(record["sample_id"]) or {}
        table.append(
            {
                "dataset": record["dataset"],
                "sample_id": record["sample_id"],
                "benchmark": record["annotations"].get("source_benchmark", ""),
                "source_error_label": record["source_error_label"],
                "description": result.get("description"),
                "status": result.get("status"),
                "evidence_quote": result.get("evidence_quote"),
                "processing_status": result.get("processing_status", "missing"),
                "question": record["question"],
                "incorrect_solution": record["incorrect_solution"],
                "source_ids": record["source_ids"],
            }
        )
    write_jsonl(out_dir / "labels.jsonl", table)
    with (out_dir / "labels.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TABLE_COLUMNS)
        writer.writeheader()
        for row in table:
            writer.writerow({**row, "source_ids": " ".join(row["source_ids"])})

    run_meta_path = run_dir / "run_meta.json"
    run_meta = read_json(run_meta_path) if run_meta_path.exists() else {}
    status_by_dataset: dict[str, Counter] = defaultdict(Counter)
    for row in table:
        status_by_dataset[row["dataset"]][row["status"] or f"(none: {row['processing_status']})"] += 1
    meta = {
        "created_at_utc": utc_now(),
        "run_id": run_id,
        "label_field": LABEL_FIELD,
        "model": run_meta.get("model"),
        "prompt_file": run_meta.get("prompt_file"),
        "prompt_version": run_meta.get("prompt_version"),
        "prompt_sha256": run_meta.get("prompt_sha256"),
        "generation": run_meta.get("generation"),
        "unique_cases": len(pool),
        "cases_without_result": len(missing),
        "model_status_by_dataset": {k: dict(sorted(v.items())) for k, v in sorted(status_by_dataset.items())},
        "rows_by_dataset": {k: dict(sorted(v.items())) for k, v in sorted(dataset_counts.items())},
        "files": file_counts,
    }
    write_json(out_dir / "export_meta.json", meta)

    for dataset, counts in sorted(dataset_counts.items()):
        labeled_rows = sum(v for k, v in counts.items() if k.startswith("labeled:"))
        print(f"[{dataset}] rows={sum(counts.values())} labeled={labeled_rows}")
    print(f"files written : {len(file_counts)} under {out_dir}")
    print(f"table         -> {out_dir / 'labels.jsonl'} ({len(table)} cases), labels.csv")
    print(f"meta          -> {out_dir / 'export_meta.json'}")
    if missing:
        print(f"WARNING: {len(missing)} case(s) exported without a description (not_generated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
