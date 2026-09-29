#!/usr/bin/env python3
"""Build data/prepared/ from the Eedi model inputs and the privileged grading annotations.

Inputs (put them in rl/data/raw/):
  train_model_inputs.jsonl               PairId, QuestionId, MisconceptionId, problem, target_misconception_description
  train_privileged_annotations.jsonl     build_dataset output (preferred), or
  all_judgements.csv                     the audit CSV; the privileged rows are rebuilt from it

Outputs (data/prepared/):
  train.jsonl, test.jsonl                Student inputs only (+ PairId, group id); no validation split
  privileged.jsonl                       grading info per PairId (reward code only)
  split_manifest.jsonl, meta.json        split per question group, input hashes, checks

Usage (from rl/):  python scripts/prepare_eedi.py [--config configs/common.yaml]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tutee_rl.common import load_config, resolve, write_json, write_jsonl  # noqa: E402
from tutee_rl.data import DataError, prepare  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="configs/common.yaml")
    args = parser.parse_args()
    cfg = load_config(args.config)
    paths = cfg["paths"]
    try:
        result = prepare(
            model_inputs_path=resolve(paths["model_inputs"]),
            privileged_path=resolve(paths["privileged"]),
            judgements_path=resolve(paths["judgements"]),
            test_ratio=cfg["split"]["test_ratio"],
            seed=cfg["split"]["seed"],
        )
    except (DataError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    out = resolve(paths["prepared_dir"])
    for split, rows in result["splits"].items():
        write_jsonl(out / f"{split}.jsonl", rows)
    write_jsonl(out / "privileged.jsonl", result["privileged"])
    write_jsonl(out / "split_manifest.jsonl", result["manifest"])
    report = {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **result["report"]}
    write_json(out / "meta.json", report)
    print(f"wrote {out}")
    for split, c in report["counts"].items():
        print(f"  {split}: {c['pairs']} pairs, {c['questions']} questions, {c['groups']} groups")
    for w in report["warnings"]:
        print(f"  warning: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
