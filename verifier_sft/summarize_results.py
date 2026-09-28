#!/usr/bin/env python3
"""Put several evaluation runs side by side (e.g. baseline vs SFT) in reports/verifier_results.md.

    python summarize_results.py baseline sft [sft_no_solution ...]

Runs are compared only if they used the same data file; ablation runs are
listed as auxiliary diagnostics.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verifier_common import load_config, resolve  # noqa: E402


def fmt(v):
    return "-" if v is None else f"{v:.4f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="+")
    parser.add_argument("--config", default=None)
    parser.add_argument("--out", default=None, help="default: <output.report_dir>/verifier_results.md")
    args = parser.parse_args()
    config = load_config(args.config)
    base = resolve(config["evaluation"]["output_dir"])
    runs = []
    for name in args.names:
        path = base / name / "metrics.json"
        if not path.exists():
            raise SystemExit(f"no metrics for {name}: {path}")
        runs.append(json.loads(path.read_text(encoding="utf-8")))
    if len({r["data_sha256"] for r in runs}) > 1 or len({r.get("limit") for r in runs}) > 1:
        raise SystemExit("runs used different data files or limits; they are not comparable")

    rows = [
        ("accuracy", lambda m: m["overall"]["accuracy"]),
        ("macro-F1", lambda m: m["overall"]["macro_f1"]),
        ("aligned F1", lambda m: m["overall"]["per_class"]["aligned"]["f1"]),
        ("not_aligned F1", lambda m: m["overall"]["per_class"]["not_aligned"]["f1"]),
        ("negative acceptance rate", lambda m: m["overall"]["negative_acceptance_rate"]),
        ("positive rejection rate", lambda m: m["overall"]["positive_rejection_rate"]),
        ("invalid rate", lambda m: m["overall"]["invalid_rate"]),
        ("pair accuracy", lambda m: m["overall"]["pair_accuracy"]),
    ]
    L = ["# Verifier results", ""]
    L += [f"split `{runs[0]['split']}` · data sha256 `{runs[0]['data_sha256'][:16]}` · rows {runs[0]['overall']['n']}", ""]
    L += ["Agreement with automatic targets (other-label negatives, no semantic review). Ablation runs "
          "(no_solution, description_only) are shortcut diagnostics, not model conditions.", ""]
    L += ["| metric | " + " | ".join(f"{r['name']} ({r['ablation']})" for r in runs) + " |"]
    L += ["| --- |" + "|".join([" --- "] * len(runs)) + "|"]
    for label, get in rows:
        L += [f"| {label} | " + " | ".join(fmt(get(r)) for r in runs) + " |"]
    L += ["| accuracy 95% CI | " + " | ".join(
        f"[{fmt(r['bootstrap_ci_question_groups']['accuracy']['low'])}, {fmt(r['bootstrap_ci_question_groups']['accuracy']['high'])}]"
        for r in runs) + " |"]
    L += ["| macro-F1 95% CI | " + " | ".join(
        f"[{fmt(r['bootstrap_ci_question_groups']['macro_f1']['low'])}, {fmt(r['bootstrap_ci_question_groups']['macro_f1']['high'])}]"
        for r in runs) + " |", ""]
    datasets = sorted({d for r in runs for d in r["by_dataset"]})
    for title, key in (("Accuracy by dataset", "accuracy"), ("Macro-F1 by dataset", "macro_f1")):
        L += [f"## {title}", ""]
        L += ["| dataset | " + " | ".join(r["name"] for r in runs) + " |", "| --- |" + "|".join([" --- "] * len(runs)) + "|"]
        for d in datasets:
            L += [f"| {d} | " + " | ".join(fmt((r["by_dataset"].get(d) or {}).get(key)) for r in runs) + " |"]
        L += [""]
    out = resolve(args.out or f"{config['output'].get('report_dir', 'reports')}/verifier_results.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
