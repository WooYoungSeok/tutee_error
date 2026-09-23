"""Adapter field mapping, checked against the downloaded raw files."""

import json

import pytest

from errdesc.adapters import (
    MissingFieldMapping,
    adapt_eic,
    adapt_mathclean,
    adapt_mathedu,
    adapt_stepwise,
)
from errdesc.paths import RAW_DIR

stepwise_file = RAW_DIR / "stepwise" / "dataset" / "dataset.json"
mathclean_file = RAW_DIR / "mathclean" / "check_type_answer" / "simple.json"
eic_dir = RAW_DIR / "eic" / "data" / "generated_cases_GSM8K"


@pytest.mark.skipif(not stepwise_file.exists(), reason="raw stepwise file not downloaded")
def test_stepwise_mapping_and_step_join():
    raw = json.loads(stepwise_file.read_text(encoding="utf-8"))
    records = list(adapt_stepwise())
    assert len(records) == len(raw)
    first = records[0]
    assert first.question == raw[0]["problem"]
    assert first.source_error_label == raw[0]["error_category"]
    assert first.incorrect_solution == "\n".join(raw[0]["student_incorrect_solution"])
    assert first.annotations["student_incorrect_solution_steps"] == raw[0]["student_incorrect_solution"]
    assert "error_description" in first.annotations
    # "None of the above" is not an error label
    assert all(
        r.exclusion_reason == "non_error_label"
        for r in records
        if r.source_error_label == "None of the above"
    )


@pytest.mark.skipif(not mathclean_file.exists(), reason="raw mathclean file not downloaded")
def test_mathclean_answer_is_the_evaluated_solution():
    raw = json.loads(mathclean_file.read_text(encoding="utf-8"))
    records = [r for r in adapt_mathclean() if r.source_id.startswith("check_type_answer/simple.json")]
    assert len(records) == len(raw)
    assert records[0].question == raw[0]["question"]
    assert records[0].incorrect_solution == raw[0]["answer"]
    assert records[0].source_error_label == raw[0]["type"]
    assert records[0].annotations["extent"] == raw[0]["extent"]
    assert {r.source_error_label for r in records} <= {
        "logic error",
        "computing error",
        "expression error",
    }


@pytest.mark.skipif(not eic_dir.exists(), reason="raw eic files not downloaded")
def test_eic_uses_transformed_solution_and_keeps_original_labels():
    records = list(adapt_eic())
    eligible = [r for r in records if r.eligible]
    assert eligible
    path = eic_dir / "unit_conversion_error" / "unit_conversion_error_100" / "generated_cases_clean.jsonl"
    raw_first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    match = [r for r in records if r.source_id.endswith("unit_conversion_error_100/generated_cases_clean.jsonl#0")]
    assert match, "expected the first unit conversion case"
    record = match[0]
    assert record.question == raw_first["question"]
    assert record.incorrect_solution == raw_first["transformed_solution"]
    assert record.source_error_label == raw_first["wrong_type"]
    assert record.annotations["original_solution"] == raw_first["original_solution"]
    assert all(r.annotations.get("is_single_error") is True for r in eligible)


def test_mathedu_requires_an_explicit_field_map(tmp_path, monkeypatch):
    import errdesc.adapters as adapters

    root = tmp_path / "mathedu"
    root.mkdir()
    (root / "sample.json").write_text(
        json.dumps([{"Problem": "q", "Student Process": "r", "Error Type": "t"}]),
        encoding="utf-8",
    )
    monkeypatch.setattr(adapters, "RAW_DIR", tmp_path)
    with pytest.raises(MissingFieldMapping) as excinfo:
        list(adapt_mathedu(field_map={}))
    # the error lists what was actually found, instead of guessing key names
    assert "Problem" in str(excinfo.value)

    records = list(
        adapt_mathedu(
            field_map={
                "question": "Problem",
                "incorrect_solution": "Student Process",
                "source_error_label": "Error Type",
            }
        )
    )
    assert len(records) == 1
    assert records[0].question == "q"
    assert records[0].incorrect_solution == "r"
    assert records[0].source_error_label == "t"


mathedu_dir = RAW_DIR / "mathedu" / "dataset" / "time_series_split"
mathqa_file = RAW_DIR / "mathqa" / "train.json"


@pytest.mark.skipif(
    not (mathedu_dir.exists() and mathqa_file.exists()),
    reason="raw mathedu/mathqa files not downloaded",
)
def test_mathedu_joins_the_question_from_mathqa_by_id():
    from errdesc.adapters import adapt_mathedu, load_mathqa_index

    mathqa = load_mathqa_index()
    assert len(mathqa) == 37297  # train 29837 + validation 4475 + test 2985

    records = list(adapt_mathedu())
    by_source = {r.source_id: r for r in records}
    raw = json.loads((mathedu_dir / "test.json").read_text(encoding="utf-8"))
    record = by_source["dataset/time_series_split/test.json#0"]
    assert record.incorrect_solution == raw[0]["student_process"]
    assert record.question == mathqa[raw[0]["id"]]["Problem"]
    assert record.annotations["mathedu_id"] == raw[0]["id"]
    assert record.annotations["student_id"] == raw[0]["student_id"]


@pytest.mark.skipif(
    not (mathedu_dir.exists() and mathqa_file.exists()),
    reason="raw mathedu/mathqa files not downloaded",
)
def test_mathedu_eligibility_rules():
    from errdesc.adapters import adapt_mathedu

    records = list(adapt_mathedu())
    eligible = [r for r in records if r.eligible]
    assert eligible
    for record in eligible:
        assert record.annotations["correct_or_not"] == "wrong"
        assert record.annotations["error_counts"] == 1
        assert record.source_error_label == record.annotations["teacher_review_errors"][0]["error_type"]
        assert record.question.strip() and record.incorrect_solution.strip()
    # correct answers and multi-error cases are excluded with an explicit reason
    reasons = {r.exclusion_reason.split(":")[0] for r in records if not r.eligible}
    assert "not_an_incorrect_answer" in reasons
    assert "multiple_annotated_errors" in reasons
