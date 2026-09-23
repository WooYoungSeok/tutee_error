"""Offline checks: keys, prompt, parsing, metrics, split and negative rules."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import prepare_descriptive_pairs as prep  # noqa: E402
from verifier_common import (  # noqa: E402
    INVALID,
    build_messages,
    compute_metrics,
    label_key,
    load_config,
    load_prompt,
    parse_prediction,
    question_group_id,
    question_key,
    render_user,
    text_key,
)


# --- keys ------------------------------------------------------------------


def test_label_key_only_normalizes_notation():
    assert label_key("Calculation_Error ") == label_key("calculation  error") == "calculation error"
    assert label_key("Arithmetical error") != label_key("calculation error")  # no merging by meaning


def test_question_key_ignores_whitespace_and_punctuation():
    a = "It takes 5 minutes, what is his speed?"
    b = "it takes 5 minutes . What is his speed"
    assert question_key(a) == question_key(b)
    assert question_group_id(a) == question_group_id(b)
    assert question_key("costs 5 dollars") != question_key("costs 6 dollars")


def test_duplicate_key_keeps_operators():
    assert text_key("20% - 20%") != text_key("20% + 20%")
    assert text_key("a +  b\n") == text_key("A + b")


# --- prompt ----------------------------------------------------------------


def test_prompt_is_the_fixed_template_and_substitution_is_single_pass():
    config = load_config()
    prompt = load_prompt(config)
    assert prompt["system"].startswith("You are a mathematical error verifier.")
    assert prompt["system"].endswith("Do not provide an explanation or any other text.")
    record = {"question": "Q {solution}", "solution": "S", "error_description": "C", "target": "aligned"}
    assert render_user(prompt["user"], record) == (
        "Question:\nQ {solution}\n\nIncorrect solution:\nS\n\nError description:\nC"
    )
    messages = build_messages(prompt, record, with_target=True)
    assert [m["role"] for m in messages] == ["system", "user", "assistant"]
    assert messages[-1]["content"] == "aligned"
    assert len(build_messages(prompt, record, with_target=False)) == 2


def test_model_input_holds_no_label_or_donor_information():
    prompt = load_prompt(load_config())
    record = {"question": "Q", "solution": "S", "error_description": "C", "target": "not_aligned",
              "anchor_source_error_label": "SECRET_A", "donor_source_error_label": "SECRET_B",
              "donor_sample_id": "SECRET_ID"}
    text = " ".join(m["content"] for m in build_messages(prompt, record, with_target=False))
    assert "SECRET" not in text


# --- parsing and metrics ---------------------------------------------------


@pytest.mark.parametrize("raw,expected", [
    ("aligned", "aligned"),
    (" not_aligned\n", "not_aligned"),
    ("Aligned", INVALID),
    ("aligned.", INVALID),
    ("not aligned", INVALID),
    ("aligned not_aligned", INVALID),
    ("The answer is aligned", INVALID),
    ("", INVALID),
    (None, INVALID),
])
def test_parse_prediction_is_strict(raw, expected):
    assert parse_prediction(raw) == expected


def _row(anchor, target, prediction, group="g"):
    return {"anchor_sample_id": anchor, "target": target, "prediction": prediction, "question_group_id": group}


def test_invalid_counts_as_wrong_everywhere():
    rows = [
        _row("a", "aligned", "aligned"), _row("a", "not_aligned", "not_aligned"),
        _row("b", "aligned", INVALID), _row("b", "not_aligned", "aligned"),
    ]
    m = compute_metrics(rows)
    assert m["accuracy"] == 0.5
    assert m["invalid_rate"] == 0.25
    assert m["per_class"]["aligned"]["recall"] == 0.5  # the invalid positive lowers recall
    assert m["per_class"]["aligned"]["precision"] == 0.5
    assert m["per_class"]["not_aligned"]["recall"] == 0.5
    assert m["negative_acceptance_rate"] == 0.5
    assert m["positive_rejection_rate"] == 0.0  # invalid is not a rejection; reported separately
    assert m["pairs"] == 2 and m["pair_accuracy"] == 0.5
    assert m["macro_f1"] == pytest.approx((m["per_class"]["aligned"]["f1"] + m["per_class"]["not_aligned"]["f1"]) / 2)


# --- split and negatives ---------------------------------------------------


def _case(sid, dataset, label, question, description="desc", solution=None):
    return {
        "sample_id": sid, "dataset": dataset, "benchmark": "", "question": question,
        "solution": solution or f"solution of {sid}", "source_error_label": label,
        "error_description": f"{description} {sid}", "description_status": "ok",
        "question_group_id": question_group_id(question), "exclusion_reason": "",
    }


def _cases():
    cases = []
    for i in range(60):
        cases.append(_case(f"ds:{i:03d}", "ds", ["A", "B", "C"][i % 3], f"question {i // 2}"))
    for i in range(30):
        cases.append(_case(f"other:{i:03d}", "other", ["X", "Y"][i % 2], f"other question {i}"))
    return cases


def test_split_keeps_groups_together_and_moves_dev_groups_out_of_test():
    cases = _cases()
    dev_keys = {question_key("question 3"), question_key("question 7")}
    info = prep.assign_splits(cases, {"train": 0.8, "validation": 0.1, "test": 0.1}, dev_keys, seed=42)
    splits_by_group = {}
    for c in cases:
        splits_by_group.setdefault(c["question_group_id"], set()).add(c["split"])
    assert all(len(s) == 1 for s in splits_by_group.values())
    for c in cases:
        if question_key(c["question"]) in dev_keys:
            assert c["split"] == "train" and c["prompt_dev_group"]
    assert len(info["forced_train_groups"]) == 2
    assert {c["split"] for c in cases} == {"train", "validation", "test"}


def test_negatives_follow_the_rules_and_are_deterministic():
    cases = _cases()
    prep.assign_splits(cases, {"train": 0.8, "validation": 0.1, "test": 0.1}, set(), seed=42)
    by_id = {c["sample_id"]: c for c in cases}
    pairs, manifest = prep.make_pairs(cases, seed=42)
    for p in pairs:
        anchor, donor = by_id[p["anchor_sample_id"]], by_id[p["donor_sample_id"]]
        assert p["question"] == anchor["question"] and p["solution"] == anchor["solution"]
        assert p["error_description"] == donor["error_description"]
        if p["target"] == "aligned":
            assert donor is anchor
        else:
            assert donor["split"] == anchor["split"]
            assert donor["dataset"] == anchor["dataset"]
            assert label_key(donor["source_error_label"]) != label_key(anchor["source_error_label"])
            assert donor["question_group_id"] != anchor["question_group_id"]
    again, _ = prep.make_pairs(sorted(cases, key=lambda c: c["sample_id"], reverse=True), seed=42)
    assert [p["donor_sample_id"] for p in pairs] == [p["donor_sample_id"] for p in again]  # input order does not matter
    assert all(e["n_candidates"] > 0 for e in manifest if e["status"] == "paired")


def test_anchor_without_candidate_is_excluded_not_filled_from_elsewhere():
    cases = [_case("ds:1", "ds", "A", "q1"), _case("ds:2", "ds", "A", "q2"), _case("x:1", "x", "B", "q3")]
    for c in cases:
        c["split"] = "test"
    pairs, manifest = prep.make_pairs(cases, seed=42)
    assert pairs == []
    assert {e["reason"] for e in manifest} == {"no_candidate"}


def test_duplicate_records_are_removed_but_different_labels_kept():
    cases = [
        _case("ds:1", "ds", "A", "q", solution="x = 20% - 20%"),
        _case("ds:2", "ds", "A", "q", solution="x  =  20% - 20%"),
        _case("ds:3", "ds", "A", "q", solution="x = 20% + 20%"),
        _case("ds:4", "ds", "B", "q", solution="x = 20% - 20%"),
    ]
    prep.remove_duplicates(cases)
    assert [c["exclusion_reason"] for c in cases] == ["", "duplicate_record_of:ds:1", "", ""]
