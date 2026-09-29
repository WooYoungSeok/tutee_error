#!/usr/bin/env python3
"""Metrics on one row kind of a mixed evaluation file, side by side for several runs.

Reads <run_dir>/predictions.jsonl of each run (written by eval_descriptive_verifier.py or
eval_api_verifier.py), keeps the rows whose row_source equals --row_source and reports, per run:
rows, correct, accuracy with a question-group bootstrap interval, predicted aligned / not_aligned
and invalid. Every run must hold the same rows (same pair ids), otherwise the script stops.

For a subset of negatives only (e.g. audited_cross_same_question in test_augmented) accuracy is the
share of mismatched descriptions the verifier rejected; 1 - accuracy is its acceptance rate.

Usage (from verifier_sft/):
    python summarize_subset.py --row_source audited_cross_same_question --out reports/<...>.md \
        outputs/strict_contrast_v1_halfA_cont/baseline_test_augmented outputs/...
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verifier_common import ALIGNED, INVALID, NOT_ALIGNED, read_jsonl, resolve  # noqa: E402


def group_bootstrap(rows: list[dict], n_samples: int, seed: int) -> tuple[float, float]:
    import numpy as np

    groups: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        groups[r["question_group_id"]].append(r["prediction"] == r["target"])
    keys = sorted(groups)
    rng = np.random.RandomState(seed)
    values = []
    for _ in range(n_samples):
        picked = [groups[keys[i]] for i in rng.randint(0, len(keys), size=len(keys))]
        flat = [x for g in picked for x in g]
        values.append(sum(flat) / len(flat))
    lo, hi = np.percentile(values, [2.5, 97.5])
    return float(lo), float(hi)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+", help="run directories holding predictions.jsonl")
    parser.add_argument("--row_source", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--bootstrap_samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    results, ids = [], None
    for run in args.runs:
        rows = [r for r in read_jsonl(resolve(run) / "predictions.jsonl") if r.get("row_source") == args.row_source]
        these = sorted(r["pair_id"] for r in rows)
        if not rows:
            raise SystemExit(f"{run}: no rows with row_source {args.row_source}")
        if ids is not None and these != ids:
            raise SystemExit(f"{run}: holds different rows than {args.runs[0]}")
        ids = these
        pred = Counter(r["prediction"] for r in rows)
        correct = sum(r["prediction"] == r["target"] for r in rows)
        lo, hi = group_bootstrap(rows, args.bootstrap_samples, args.seed)
        results.append({"run": run, "n": len(rows), "correct": correct, "accuracy": correct / len(rows), "ci": (lo, hi),
                        "pred": pred, "groups": len({r["question_group_id"] for r in rows}),
                        "targets": Counter(r["target"] for r in rows)})

    first = results[0]
    L = [f"# Subset `{args.row_source}`", "",
         f"{first['n']} rows in {first['groups']} question groups · targets {dict(first['targets'])} · "
         f"95% interval: question-group bootstrap ({args.bootstrap_samples} samples, seed {args.seed}).", "",
         "| run | rows | correct | accuracy [95% interval] | predicted aligned | predicted not_aligned | invalid |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in results:
        L.append(f"| `{r['run']}` | {r['n']} | {r['correct']} | {r['accuracy']:.4f} [{r['ci'][0]:.3f}, {r['ci'][1]:.3f}] | "
                 f"{r['pred'][ALIGNED]} | {r['pred'][NOT_ALIGNED]} | {r['pred'][INVALID]} |")
    out = resolve(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
