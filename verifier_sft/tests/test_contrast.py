"""Offline checks for the same-question contrast candidates and the audit parser."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_contrast import AuditSchemaError, parse_audit  # noqa: E402
from build_contrast_candidates import build_candidates  # noqa: E402


def case(sid, group, solution, description, label, split="train"):
    return {"sample_id": sid, "split": split, "dataset": "eic", "benchmark": "GSM8K", "question_group_id": group,
            "question": "Q", "solution": solution, "error_description": description, "source_error_label": label}


def test_candidates_cover_every_combination_inside_multi_solution_groups():
    cases = [
        case("a", "g1", "(-8)+(-2)=-10", "Uses addition instead of multiplication", "operator_error"),
        case("b", "g1", "(-8)*(-2)=-16", "Gives the product of two negatives a negative sign", "operator_error"),
        case("c", "g2", "only one solution", "desc c", "calculation_error"),
    ]
    rows, _ = build_candidates(cases, {"a": "A", "b": "A", "c": "B"})
    got = {(r["solution_sample_id"], r["description_sample_id"], r["origin"]) for r in rows}
    assert got == {("a", "a", "own"), ("b", "b", "own"), ("a", "b", "cross_same_question"), ("b", "a", "cross_same_question")}
    assert all(r["same_source_label"] for r in rows)  # same label is kept: fine-grained contrasts
    assert all("target" not in r for r in rows)  # labels come from the audit only


def test_cross_row_with_the_own_description_text_is_skipped():
    cases = [case("a", "g1", "s1", "same text", "x"), case("b", "g1", "s2", "Same  text", "y")]
    rows, skipped = build_candidates(cases, {"a": "A", "b": "A"})
    assert {r["origin"] for r in rows} == {"own"} and skipped["same_description_text"] == 2


def test_test_split_rows_get_half_test():
    cases = [case("a", "g1", "s1", "d1", "x", "test"), case("b", "g1", "s2", "d2", "y", "test")]
    rows, _ = build_candidates(cases, {})
    assert {r["half"] for r in rows} == {"test"}


def test_parse_audit_is_strict():
    ok = '{"required_behavior": "r", "observed_behavior": "o", "verdict": "unclear"}'
    assert parse_audit(ok)["verdict"] == "unclear"
    for bad in ('{"required_behavior": "r", "observed_behavior": "o", "verdict": "maybe"}',
                '{"verdict": "aligned"}', "aligned", None):
        with pytest.raises(AuditSchemaError):
            parse_audit(bad)
