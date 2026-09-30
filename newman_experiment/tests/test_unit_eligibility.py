"""Unit-conversion eligibility: the vendored allowlist, its corrections, content check, linking (True/False/None)."""

from __future__ import annotations

import json

import pytest

from newman.common import resolve
from newman.unit_eligibility import Eligibility, EligibilityError, content_audit, corrected_rows, load_allowlist
from newman.verifier_format import question_key

ALLOW = load_allowlist(resolve("data/unit_conversion_allowlist_gsm8k.json"))


def test_vendored_allowlist_gives_the_plan_counts():
    rows = corrected_rows(ALLOW, {"train": 7473, "test": 1319})
    assert sum(1 for s, _ in rows if s == "train") == 845
    assert sum(1 for s, _ in rows if s == "test") == 203
    corrections = {g: v["correction"] for g, v in ALLOW["groups"]["train"].items()}
    assert corrections == {"시간단위": -2, "길이단위": -2, "화폐단위": -2, "거리단위": 0, "무게/부피": 0, "묶음단위": 0}
    assert ALLOW["source"]["commit"] == "972f0c3866a48520c87c254f45dcd9c875da8797"


def tiny_allowlist(correction=-2):
    return {"groups": {"train": {"시간단위": {"correction": correction, "indices": [3, 5]}}, "test": {}},
            "expected_unique_rows": {"train": 2, "test": 0}}


def test_out_of_range_index_is_rejected():
    with pytest.raises(EligibilityError):
        corrected_rows({"groups": {"train": {"시간단위": {"correction": 0, "indices": [10]}}}}, {"train": 5})


def test_content_audit_finds_the_correction():
    qs = ["no unit"] * 8
    qs[1] = qs[3] = "It takes 3 hours"
    audit = content_audit(tiny_allowlist(), {"train": qs, "test": []})
    assert audit["problems"] == []
    shifted = content_audit(tiny_allowlist(correction=0), {"train": qs, "test": []})
    assert shifted["problems"]  # the unit words peak at -2, not at the configured 0


def gsm8k_rows():
    return [{"split": "train", "row": i, "question": f"Question number {i} about minutes"} for i in range(8)]


def test_linking_gives_true_false_and_none(tmp_path):
    elig = Eligibility(gsm8k_rows(), tiny_allowlist(), question_key)
    assert elig.lookup("Question number 1 about minutes") == (True, "gsm8k:train:1")      # 3 - 2
    assert elig.lookup("question number 2 about minutes!")[0] is False                    # linked, not listed
    assert elig.lookup("A MathQA question") == (None, "unlinked")                          # never guessed
    assert not elig.allowed("A MathQA question")
    extra = tmp_path / "extra.jsonl"
    extra.write_text(json.dumps({"question": "A MathQA question"}) + "\n" + json.dumps({"question": "Question number 2 about minutes"}) + "\n")
    elig = Eligibility(gsm8k_rows(), tiny_allowlist(), question_key, [{"path": extra}])
    assert elig.lookup("A MathQA question")[0] is True
    assert elig.lookup("Question number 2 about minutes")[0] is None                       # disagreement -> None
    assert elig.conflicts
