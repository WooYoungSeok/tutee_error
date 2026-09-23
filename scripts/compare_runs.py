#!/usr/bin/env python3
"""Compare two or more runs over the same sample (e.g. prompt v1 / v2 / v3).

Writes a side-by-side CSV and a markdown summary. It reports what changed;
it does not decide which description is better.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from errdesc.paths import OUTPUTS_DIR, REPORTS_DIR, SAMPLE_MANIFEST, ensure_dirs  # noqa: E402
from errdesc.review import build_review_rows  # noqa: E402
from errdesc.util import read_json, read_jsonl  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", help="run ids, baseline first")
    parser.add_argument(
        "--out-name",
        default=None,
        help="base name for the output files (default: compare_<run1>__vs__<run2>…)",
    )
    return parser.parse_args()


def load_run(run_id: str, manifest: dict) -> tuple[dict, dict]:
    run_dir = OUTPUTS_DIR / "runs" / run_id
    parsed_path = run_dir / "parsed.jsonl"
    if not parsed_path.exists():
        raise SystemExit(f"no parsed results for run {run_id}: {parsed_path}")
    parsed = list(read_jsonl(parsed_path))
    meta_path = run_dir / "run_meta.json"
    meta = read_json(meta_path) if meta_path.exists() else {"run_id": run_id}
    rows = {row["sample_id"]: row for row in build_review_rows(parsed, manifest)}
    return rows, meta


def make_labels(run_ids: list[str]) -> dict[str, str]:
    """Short, unambiguous column labels for a set of run ids.

    Run ids look like ``<prompt>__<model>__<split>``. Only the parts that
    actually differ between the compared runs are kept, so comparing prompt
    versions gives ``v1 / v2``, and comparing models gives ``gpt-5.4-mini /
    gpt-5.6-luna``.
    """
    parts = [run_id.split("__") for run_id in run_ids]
    if len({len(p) for p in parts}) == 1:
        width = len(parts[0])
        varying = [i for i in range(width) if len({p[i] for p in parts}) > 1]
        if varying:
            labels = {
                run_id: "__".join(p[i] for i in varying) for run_id, p in zip(run_ids, parts)
            }
            if len(set(labels.values())) == len(run_ids):
                return labels
    return {run_id: run_id for run_id in run_ids}


def main() -> int:
    args = parse_args()
    if len(args.runs) < 2:
        raise SystemExit("give at least two run ids")
    ensure_dirs()
    manifest = {row["sample_id"]: row for row in read_jsonl(SAMPLE_MANIFEST)}

    runs = {run_id: load_run(run_id, manifest) for run_id in args.runs}
    labels = make_labels(args.runs)
    shared = sorted(set.intersection(*(set(rows) for rows, _ in runs.values())))
    if not shared:
        raise SystemExit("the runs have no sample in common")

    base_name = args.out_name or ("compare_" + "__vs__".join(labels[r] for r in args.runs))
    out_csv = REPORTS_DIR / f"{base_name}.csv"

    columns = [
        "dataset",
        "sample_id",
        "split",
        "source_error_label",
        "question",
        "incorrect_solution",
    ]
    for run_id in args.runs:
        tag = labels[run_id]
        columns += [f"description__{tag}", f"status__{tag}", f"evidence__{tag}"]
    for run_id in args.runs:
        tag = labels[run_id]
        columns += [f"words__{tag}", f"question_tokens__{tag}", f"evidence_verbatim__{tag}",
                    f"processing__{tag}"]
    columns += ["status_varies", "review_which_is_better", "review_comment"]

    with out_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for sample_id in shared:
            first = runs[args.runs[0]][0][sample_id]
            row = {
                "dataset": first["dataset"],
                "sample_id": sample_id,
                "split": first["split"],
                "source_error_label": first["source_error_label"],
                "question": first["question"],
                "incorrect_solution": first["incorrect_solution"],
                "review_which_is_better": "",
                "review_comment": "",
            }
            statuses = set()
            for run_id in args.runs:
                tag = labels[run_id]
                r = runs[run_id][0][sample_id]
                statuses.add(r["status"])
                row[f"description__{tag}"] = r["description"]
                row[f"status__{tag}"] = r["status"]
                row[f"evidence__{tag}"] = r["evidence_quote"]
                row[f"words__{tag}"] = r["word_count"]
                row[f"question_tokens__{tag}"] = r["shared_question_tokens"]
                row[f"evidence_verbatim__{tag}"] = r["evidence_quote_found_in_solution"]
                row[f"processing__{tag}"] = r["processing_status"]
            row["status_varies"] = len(statuses) > 1
            writer.writerow(row)

    def stats(run_id: str) -> dict:
        rows, meta = runs[run_id]
        values = [rows[s] for s in shared]
        described = [r for r in values if r["description"]]
        lengths = sorted(r["word_count"] for r in described)
        return {
            "prompt_version": meta.get("prompt_version"),
            "prompt_sha256": str(meta.get("prompt_sha256"))[:16],
            "model": meta.get("model"),
            "described": len(described),
            "median_words": lengths[len(lengths) // 2] if lengths else 0,
            "outside_5_15": sum(1 for r in described if r["length_outside_5_15_words"]),
            "shares_question_token": sum(1 for r in values if r["shared_question_tokens"]),
            "evidence_verbatim": sum(1 for r in values if r["evidence_quote_found_in_solution"]),
            "processing": dict(Counter(r["processing_status"] for r in values)),
            "status": dict(Counter(r["status"] or "(none)" for r in values)),
            "usage": meta.get("usage_totals"),
        }

    all_stats = {run_id: stats(run_id) for run_id in args.runs}

    lines = [f"# Run comparison — {', '.join(args.runs)}", ""]
    lines.append(f"Cases compared: {len(shared)}")
    lines.append("")
    lines.append("| | " + " | ".join(labels[r] for r in args.runs) + " |")
    lines.append("| --- |" + "|".join([" --- "] * len(args.runs)) + "|")
    for label, key in [
        ("prompt version", "prompt_version"),
        ("prompt sha256", "prompt_sha256"),
        ("model", "model"),
        ("cases with a description", "described"),
        ("median description words", "median_words"),
        ("descriptions outside 5-15 words", "outside_5_15"),
        ("shares an uncommon question token", "shares_question_token"),
        ("evidence_quote found verbatim", "evidence_verbatim"),
        ("processing status", "processing"),
        ("model status", "status"),
        ("token usage", "usage"),
    ]:
        lines.append(
            f"| {label} | " + " | ".join(str(all_stats[r][key]) for r in args.runs) + " |"
        )
    lines.append("")

    varies = [
        s
        for s in shared
        if len({runs[r][0][s]["status"] for r in args.runs}) > 1
    ]
    lines.append(f"## Cases where the status differs between runs ({len(varies)})")
    lines.append("")
    if varies:
        lines.append("| dataset | sample_id | label | " + " | ".join(labels[r] for r in args.runs) + " |")
        lines.append("| --- | --- | --- |" + "|".join([" --- "] * len(args.runs)) + "|")
        for sample_id in varies:
            first = runs[args.runs[0]][0][sample_id]
            cells = " | ".join(str(runs[r][0][sample_id]["status"]) for r in args.runs)
            lines.append(
                f"| {first['dataset']} | {sample_id} | {first['source_error_label']} | {cells} |"
            )
    else:
        lines.append("None.")
    lines.append("")

    lines.append("## Descriptions side by side")
    lines.append("")
    for dataset in sorted({runs[args.runs[0]][0][s]["dataset"] for s in shared}):
        lines.append(f"### {dataset}")
        lines.append("")
        for sample_id in [s for s in shared if runs[args.runs[0]][0][s]["dataset"] == dataset]:
            first = runs[args.runs[0]][0][sample_id]
            lines.append(f"- **{first['source_error_label']}**")
            for run_id in args.runs:
                r = runs[run_id][0][sample_id]
                lines.append(f"  - {labels[run_id]}: {r['description']}  `[{r['status']}]`")
        lines.append("")
    lines.append(
        "Counts and flags above are descriptive only. Which description is better "
        "is a human judgement; fill in `review_which_is_better` in the CSV."
    )

    out_md = REPORTS_DIR / f"{base_name}.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"comparison CSV -> {out_csv}")
    print(f"comparison MD  -> {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
