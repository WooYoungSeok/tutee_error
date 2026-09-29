from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tutee_rl.data import DataError, distractors_from_judgement, group_key, prepare, split_groups  # noqa: E402

HEADER = ["Split", "QuestionId", "CorrectAnswer", "QuestionText", "AnswerAText", "AnswerBText", "AnswerCText", "AnswerDText",
          "MisconceptionAId", "MisconceptionBId", "MisconceptionCId", "MisconceptionDId", "Decision", "AnswerContract",
          "CorrectAnswerText"]


def _write_inputs(tmp: Path, n_questions: int = 10):
    rows, judg = [], []
    for q in range(n_questions):
        text = f"What is {q} + {q}?\n\\( {q}+{q} \\)"
        judg.append(["train", str(q), "A", text, str(2 * q), str(q), str(q * q), str(3 * q), "", "101", "101", "202",
                     "KEEP", "NUMBER_OR_STRUCTURED_MATH", str(2 * q)])
        rows.append({"PairId": f"{q}__101", "QuestionId": str(q), "MisconceptionId": 101, "problem": text,
                     "target_misconception_description": "Adds wrongly."})
        if q % 2 == 0:
            rows.append({"PairId": f"{q}__202", "QuestionId": str(q), "MisconceptionId": 202, "problem": text,
                         "target_misconception_description": "Multiplies instead."})
    inputs = tmp / "inputs.jsonl"
    inputs.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    jpath = tmp / "judg.csv"
    with open(jpath, "w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(HEADER)
        w.writerows(judg)
    return inputs, jpath, rows


def test_group_key_normalises_whitespace_and_nfkc():
    assert group_key("a  b\n c d") == "a b c d"


def test_split_rule_matches_plan():
    import numpy as np

    keys = [f"k{i}" for i in range(11)]
    out = split_groups(keys, 0.2, 42)
    unique = sorted(set(keys))
    perm = np.random.RandomState(42).permutation(len(unique))
    expected_test = {unique[i] for i in perm[: math.ceil(11 * 0.2)]}
    assert {k for k, s in out.items() if s == "test"} == expected_test
    assert set(out.values()) == {"train", "test"}


def test_prepare_rebuilds_privileged_and_keeps_questions_together(tmp_path):
    inputs, jpath, rows = _write_inputs(tmp_path)
    result = prepare(inputs, tmp_path / "missing.jsonl", jpath, 0.2, 42)
    assert sum(len(v) for v in result["splits"].values()) == len(rows)
    for split_rows in result["splits"].values():
        for r in split_rows:
            assert set(r) == {"PairId", "QuestionId", "MisconceptionId", "problem", "target_misconception_description", "group_id", "split"}
    q_split = {}
    for split, split_rows in result["splits"].items():
        for r in split_rows:
            assert q_split.setdefault(r["QuestionId"], split) == split
    priv = {p["PairId"]: p for p in result["privileged"]}
    assert priv["0__101"]["CorrectAnswerText"] == "0"
    assert [d["option"] for d in priv["2__101"]["TargetDistractors"]] == ["B", "C"]
    assert [d["option"] for d in priv["2__202"]["TargetDistractors"]] == ["D"]
    assert [d["option"] for d in priv["2__202"]["OtherLabeledDistractors"]] == ["B", "C"]


def test_prepare_rejects_non_keep(tmp_path):
    inputs, jpath, _ = _write_inputs(tmp_path)
    text = jpath.read_text(encoding="utf-8").replace(",KEEP,", ",DROP,", 1)
    jpath.write_text(text, encoding="utf-8")
    with pytest.raises(DataError):
        prepare(inputs, None, jpath, 0.2, 42)


def test_prepare_checks_privileged_one_to_one(tmp_path):
    inputs, jpath, rows = _write_inputs(tmp_path)
    priv = tmp_path / "priv.jsonl"
    lines = [{"PairId": r["PairId"], "CorrectAnswerText": "x", "AnswerContract": "c", "TargetDistractorsJSON": "[]",
              "OtherLabeledDistractorsJSON": "[]", "UnlabeledDistractorsJSON": "[]"} for r in rows[:-1]]
    priv.write_text("".join(json.dumps(x) + "\n" for x in lines), encoding="utf-8")
    with pytest.raises(DataError):
        prepare(inputs, priv, jpath, 0.2, 42)


def test_distractors_nan_is_unlabeled():
    rec = {"CorrectAnswer": "B", "AnswerAText": "a", "AnswerBText": "b", "AnswerCText": "c", "AnswerDText": "d",
           "MisconceptionAId": float("nan"), "MisconceptionBId": 5.0, "MisconceptionCId": 7.0, "MisconceptionDId": 9.0}
    out = distractors_from_judgement(rec, 7)
    assert [d["option"] for d in out["TargetDistractors"]] == ["C"]
    assert [d["option"] for d in out["OtherLabeledDistractors"]] == ["D"]
    assert [d["option"] for d in out["UnlabeledDistractors"]] == ["A"]
