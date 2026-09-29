#!/usr/bin/env python3
"""SMOKE ONLY: a tiny prepared dataset for pipeline tests before the real Eedi inputs are on the server.

Problems, reference answers, answer contracts and distractors are copied from KEEP rows of
all_judgements.csv. The misconception descriptions are written for this smoke test (they are not the
Eedi misconception names). Never train a real run on data/smoke/.

Usage (from rl/):  python scripts/make_smoke_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tutee_rl.common import resolve, write_json, write_jsonl  # noqa: E402

# (QuestionId, problem, CorrectAnswerText, AnswerContract, [(option, text, is_target_for)], [description_1, description_2])
PROBLEMS = [
    ("7", r"\( 43.2 \div 10= \)", r"\( 4.32 \)", "NUMBER_OR_STRUCTURED_MATH",
     [("B", r"\( 0.432 \)"), ("C", r"\( 33.2 \)"), ("D", r"\( 43.02 \)")],
     ["Divides by 100 when asked to divide by 10, moving the decimal point two places.",
      "Subtracts 10 from the number instead of dividing by 10."]),
    ("8", "\\(\n\\frac{4}{5}-\\frac{1}{3}=\\frac{\\bigstar}{15}\n\\)\nWhat should replace the star?", r"\( 7 \)", "NUMBER_OR_STRUCTURED_MATH",
     [("B", r"\( 5 \)"), ("C", r"\( 17 \)"), ("D", r"\( 3 \)")],
     ["Subtracts the numerators and subtracts the denominators when subtracting fractions.",
      "Adds the fractions instead of subtracting them."]),
    ("24", "What should replace the star?\n\\[\n\\bigstar \\times 4=108\n\\]", r"\( 27 \)", "NUMBER_OR_STRUCTURED_MATH",
     [("A", r"\( 112 \)"), ("C", r"\( 432 \)"), ("D", r"\( 104 \)")],
     ["Multiplies the two given numbers when finding a missing factor instead of dividing.",
      "Subtracts the given factor from the product to find the missing factor."]),
    ("27", r"If \( d=-2 \) what is the value of \( 10-2 d \) ?", r"\( 14 \)", "NUMBER_OR_STRUCTURED_MATH",
     [("A", r"\( -12 \)"), ("B", r"\( 6 \)"), ("D", r"\( 32 \)")],
     ["Believes that subtracting a negative number makes the result smaller.",
      "Substitutes the value without keeping its negative sign."]),
    ("34", r"What number is \( 10,000 \) less than \( 901,426 \) ?", r"\( 891,426 \)", "NUMBER_OR_STRUCTURED_MATH",
     [("A", r"\( 801,426 \)"), ("B", r"\( 911,426 \)"), ("D", r"\( 90.1426 \)")],
     ["Changes the digit in the hundred-thousands column when subtracting 10,000.",
      "Adds 10,000 when asked for a number that is 10,000 less."]),
    ("35", "Convert this decimal to a percentage\n\\[\n0.6\n\\]", r"\( 60 \% \)", "NUMBER_OR_STRUCTURED_MATH",
     [("B", r"\( 6 \% \)"), ("C", r"\( 0.6 \% \)"), ("D", r"\( 0.006 \% \)")],
     ["Multiplies by 10 instead of 100 when converting a decimal to a percentage.",
      "Writes the decimal digits unchanged and adds a percent sign."]),
    ("37", "Write this fraction as simply as possible:\n\\(\n\\frac{9}{12}\n\\)", r"\( \frac{3}{4} \)", "RATIONAL_OR_EXPRESSION",
     [("A", r"\( \frac{3}{6} \)"), ("B", r"\( \frac{2}{6} \)"), ("D", r"\( \frac{9}{12} \)")],
     ["Divides the numerator and the denominator by different numbers when simplifying.",
      "Subtracts the same number from the numerator and denominator to simplify a fraction."]),
    ("43", r"Calculate: \( \frac{4}{8} \div 2 \)", r"\( \frac{2}{8} \)", "NUMBER_OR_STRUCTURED_MATH",
     [("A", r"\( \frac{2}{4} \)"), ("C", r"\( \frac{2}{16} \)"), ("D", r"\( \frac{4}{4} \)")],
     ["Divides both the numerator and the denominator by the whole number when dividing a fraction by an integer.",
      "Multiplies the fraction by the integer instead of dividing."]),
    ("49", r"\( 2 \) leap years \( =\square \) days", r"\( 732 \)", "NUMBER_OR_STRUCTURED_MATH",
     [("A", r"\( 728 \)"), ("B", r"\( 730 \)"), ("C", r"\( 366 \)")],
     ["Thinks a leap year has 365 days.", "Thinks a leap year has 364 days."]),
    ("59", r"\( 130 \% \) of \( 40= \)", r"\( 52 \)", "NUMBER_OR_STRUCTURED_MATH",
     [("A", r"\( 12 \)"), ("C", r"\( 170 \)")],
     ["Finds only the part over 100% (30%) instead of the whole 130%.",
      "Adds the percentage number to the amount."]),
    ("73", r"What is \( 326 \) rounded to the nearest \( 1000 \) ?", r"\( 0 \)", "NUMBER_OR_STRUCTURED_MATH",
     [("A", r"\( 1000 \)"), ("B", r"\( 3000 \)"), ("C", r"\( 500 \)")],
     ["Always rounds up to the next multiple when rounding.",
      "Rounds to the nearest 500 instead of the nearest 1000."]),
    ("124", "What number belongs in the box?\n\\(\n(-8)-(-5)=\n\\square\\)", r"\( -3 \)", "NUMBER_OR_STRUCTURED_MATH",
     [("A", r"\( -13 \)"), ("B", r"\( 13 \)"), ("C", r"\( 3 \)")],
     ["Treats subtracting a negative number as subtracting a positive number.",
      "Ignores all negative signs and works with the positive numbers."]),
]


def main() -> int:
    out = resolve("data/smoke")
    train, privileged = [], []
    for qid, problem, correct, contract, distractors, descriptions in PROBLEMS:
        for k, description in enumerate(descriptions):
            pair_id = f"{qid}__smoke{k}"
            train.append({"PairId": pair_id, "QuestionId": qid, "MisconceptionId": -1 - k, "problem": problem,
                          "target_misconception_description": description, "group_id": f"smoke_{qid}", "split": "train"})
            privileged.append({"PairId": pair_id, "CorrectAnswerText": correct, "AnswerContract": contract,
                               "TargetDistractors": [], "OtherLabeledDistractors": [],
                               "UnlabeledDistractors": [{"option": o, "text": t, "misconception_id": None} for o, t in distractors],
                               "source": "smoke"})
    write_jsonl(out / "train.jsonl", train)
    write_jsonl(out / "privileged.jsonl", privileged)
    write_json(out / "meta.json", {"SMOKE_ONLY": True, "rows": len(train),
                                   "note": "descriptions written for the smoke test, not Eedi misconception names"})
    print(f"wrote {len(train)} smoke rows to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
