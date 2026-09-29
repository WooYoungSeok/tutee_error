#!/usr/bin/env python3
"""Same-question contrast candidates from the existing four datasets (strict verifier, source 1).

For every question group that holds two or more different solutions in the source data, every
(solution, error description) combination inside the group becomes one candidate row:

  origin "own"                  the solution with its own description (the existing positive)
  origin "cross_same_question"  the solution with the description written for another solution of
                                the same question; the source labels may be equal or different

No target is assigned here. Every candidate is labelled later by the audit (audit_contrast.py):
aligned / not_aligned / unclear (unclear rows are dropped from training).

Split and half follow the source: a question group lies in one v2 split, and train/validation
groups lie in one trval half (A or B), so all rows of a group stay together. Test groups get
half "test" and are only used for the held-out contrast evaluation.

Usage (from verifier_sft/):
    python build_contrast_candidates.py --config config/strict_contrast_v1.json
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verifier_common import (  # noqa: E402
    ALIGNED,
    label_key,
    load_config,
    read_jsonl,
    resolve,
    sha256_file,
    text_key,
    write_json,
    write_jsonl,
)

SPLITS = ("train", "validation", "test")


def source_cases(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One case per positive row: the anchor's solution with its own description."""
    return sorted(
        (
            {
                "sample_id": r["anchor_sample_id"],
                "split": r["split"],
                "dataset": r["dataset"],
                "benchmark": r["benchmark"],
                "question_group_id": r["question_group_id"],
                "question": r["question"],
                "solution": r["solution"],
                "error_description": r["error_description"],
                "source_error_label": r["anchor_source_error_label"],
            }
            for r in rows
            if r["target"] == ALIGNED
        ),
        key=lambda c: c["sample_id"],
    )


def candidate_row(sol: dict[str, Any], desc: dict[str, Any], half: str) -> dict[str, Any]:
    own = sol["sample_id"] == desc["sample_id"]
    return {
        "candidate_id": f"{sol['sample_id']}::desc::{desc['sample_id']}",
        "source": "v2_same_question",
        "origin": "own" if own else "cross_same_question",
        "split": sol["split"],
        "half": half,
        "dataset": sol["dataset"],
        "benchmark": sol["benchmark"],
        "question_group_id": sol["question_group_id"],
        "solution_sample_id": sol["sample_id"],
        "description_sample_id": desc["sample_id"],
        "solution_source_label": sol["source_error_label"],
        "description_source_label": desc["source_error_label"],
        "same_source_label": label_key(sol["source_error_label"]) == label_key(desc["source_error_label"]),
        "question": sol["question"],
        "solution": sol["solution"],
        "error_description": desc["error_description"],
    }


def build_candidates(cases: list[dict[str, Any]], half_of: dict[str, str]) -> tuple[list[dict[str, Any]], Counter]:
    """All ordered (solution, description) combinations inside groups with several distinct solutions.

    A cross row is skipped when its description text equals the solution's own description
    (it would repeat the positive). Returns rows sorted by candidate_id and skip counts.
    """
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in cases:
        groups[c["question_group_id"]].append(c)
    rows, skipped = [], Counter()
    for gid, members in groups.items():
        if len({text_key(c["solution"]) for c in members}) < 2:
            continue
        for sol in members:
            half = half_of.get(sol["sample_id"], "test" if sol["split"] == "test" else None)
            if half is None:
                raise SystemExit(f"{sol['sample_id']} ({sol['split']}) has no half assignment")
            for desc in members:
                if desc is not sol:
                    if text_key(desc["solution"]) == text_key(sol["solution"]):
                        skipped["same_solution_text"] += 1
                        continue
                    if text_key(desc["error_description"]) == text_key(sol["error_description"]):
                        skipped["same_description_text"] += 1
                        continue
                rows.append(candidate_row(sol, desc, half))
    return sorted(rows, key=lambda r: r["candidate_id"]), skipped


def run_checks(rows: list[dict[str, Any]]) -> list[tuple[str, bool, str]]:
    by_group: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for r in rows:
        by_group[r["question_group_id"]].add((r["split"], r["half"]))
    spread = [g for g, s in by_group.items() if len(s) > 1]
    ids = Counter(r["candidate_id"] for r in rows)
    return [
        ("each question group in one split and one half", not spread, f"{len(spread)} groups"),
        ("candidate ids unique", all(v == 1 for v in ids.values()), ""),
        ("test rows carry half test and only test rows do",
         all((r["split"] == "test") == (r["half"] == "test") for r in rows), ""),
        ("cross rows pair different solutions of the same question",
         all(r["solution_sample_id"] != r["description_sample_id"] for r in rows if r["origin"] != "own"), ""),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    cfg = config["candidates"]["v2_same_question"]

    src_dir = resolve(cfg["source_data_dir"])
    cases = []
    for split in SPLITS:
        cases += source_cases(read_jsonl(src_dir / f"{split}.jsonl"))
    half_of = {r["sample_id"]: r["half"] for r in read_jsonl(resolve(cfg["half_assignment"]))}

    rows, skipped = build_candidates(cases, half_of)
    checks = run_checks(rows)
    ok = all(c[1] for c in checks)

    out = resolve(config["output"]["candidates"])
    write_jsonl(out, rows)
    counts = Counter((r["split"], r["half"], r["origin"], r["same_source_label"]) for r in rows)
    meta = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "config": {"path": config["_config_path"], "sha256": config["_config_sha256"]},
        "source": {f"{s}.jsonl": sha256_file(src_dir / f"{s}.jsonl") for s in SPLITS},
        "half_assignment_sha256": sha256_file(resolve(cfg["half_assignment"])),
        "rows": len(rows),
        "question_groups": len({r["question_group_id"] for r in rows}),
        "skipped": dict(skipped),
        "by_dataset": dict(Counter(r["dataset"] for r in rows)),
        "counts": [
            {"split": s, "half": h, "origin": o, "same_source_label": sl, "rows": n}
            for (s, h, o, sl), n in sorted(counts.items())
        ],
        "checks_passed": ok,
    }
    write_json(out.with_suffix(".meta.json"), meta)

    print(f"{len(rows)} candidates in {meta['question_groups']} question groups -> {out}")
    print(f"  skipped {dict(skipped)} · by dataset {meta['by_dataset']}")
    for c in meta["counts"]:
        print(f"  {c['split']:10s} half {c['half']:4s} {c['origin']:20s} same label {str(c['same_source_label']):5s} {c['rows']:5d}")
    for name, passed, detail in checks:
        print(f"  [{'ok' if passed else 'FAIL'}] {name} {detail if not passed else ''}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
