#!/usr/bin/env python3
"""Fix the two real MathEDU wrong-answer examples used by the student-likeness judge.

Reads ../data/normalized/mathedu.jsonl (MathEDU train split joined with its MathQA question by the
repo's adapter) and copies question + student_process text byte-for-byte: no spelling or math fixes.
Example 1 = MathEDU id 13427 (approved). Example 2 = id 8584 (approved 2026-09-29;
student_likeness.examples_approved in the config gates real runs).

Usage (from rl/):  python scripts/prepare_mathedu_examples.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tutee_rl.common import REPO_ROOT, resolve, sha256_file, sha256_text, write_json  # noqa: E402

EXAMPLES = [(13427, "approved"), (8584, "approved")]  # example 2 approved by the user on 2026-09-29


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default=str(REPO_ROOT / "data" / "normalized" / "mathedu.jsonl"))
    parser.add_argument("--out", default="data/mathedu_student_examples.json")
    args = parser.parse_args()

    source = Path(args.source)
    wanted = {mid: status for mid, status in EXAMPLES}
    found: dict[int, dict] = {}
    with open(source, encoding="utf-8") as handle:
        for line in handle:
            rec = json.loads(line)
            ann = rec["annotations"]
            mid = ann.get("mathedu_id")
            if mid in wanted and ann.get("mathedu_split_file") == "train":
                if mid in found:
                    print(f"error: MathEDU id {mid} appears twice in {source}", file=sys.stderr)
                    return 1
                found[mid] = rec
    examples = []
    for position, (mid, status) in enumerate(EXAMPLES, 1):
        rec = found.get(mid)
        if rec is None:
            print(f"error: MathEDU id {mid} not found in the train split of {source}", file=sys.stderr)
            return 1
        ann = rec["annotations"]
        if ann.get("correct_or_not") != "wrong":
            print(f"error: MathEDU id {mid} is not a wrong answer ({ann.get('correct_or_not')})", file=sys.stderr)
            return 1
        examples.append({
            "position": position,
            "status": status,
            "mathedu_id": mid,
            "student_id": ann.get("student_id"),
            "split": ann.get("mathedu_split_file"),
            "correct_or_not": ann.get("correct_or_not"),
            "question": rec["question"],
            "student_solution": rec["incorrect_solution"],
            "question_sha256": sha256_text(rec["question"]),
            "student_solution_sha256": sha256_text(rec["incorrect_solution"]),
            "provenance": {
                "sample_id": rec["sample_id"],
                "source_id": rec["source_id"],
                "source_file": rec["source_file"],
                "source_revision": rec["source_revision"],
                "question_join": "MathQA Problem joined by MathEDU id (concat train/validation/test index), see src/errdesc/adapters.py",
            },
            "withheld_from_judge": ["source_error_label", "teacher review", "teacher advice"],
        })
    out = {
        "description": "Fixed MathEDU train wrong-answer examples for the student-likeness judge. Same two examples, "
                       "same order, in every step and every A/B pair. Not used for evaluation.",
        "source": str(source.relative_to(REPO_ROOT)),
        "source_sha256": sha256_file(source),
        "examples": examples,
    }
    write_json(resolve(args.out), out)
    print(f"wrote {resolve(args.out)}")
    for ex in examples:
        print(f"  example {ex['position']}: MathEDU {ex['mathedu_id']} student {ex['student_id']} [{ex['status']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
