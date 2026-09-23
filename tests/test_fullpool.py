"""Full labeling pool: deduplication by sample id, EIC benchmark selection."""

import json

import pytest

from errdesc.adapters import NormalizedRecord, adapt_eic, eic_root
from errdesc.fullpool import FULL_SPLIT, build_pool, index_row


def record(sample_id, source_id, label="x", eligible=True, reason=""):
    return NormalizedRecord(
        sample_id=sample_id,
        dataset="ds",
        source_id=source_id,
        source_file="data/raw/ds/f.json",
        source_revision="r",
        question="q",
        incorrect_solution="s",
        source_error_label=label,
        eligible=eligible,
        exclusion_reason=reason,
    )


def test_pool_has_one_request_per_sample_id_and_keeps_every_source():
    records = [
        record("ds:a", "f.json#0"),
        record("ds:b", "f.json#1"),
        record("ds:a", "f.json#2"),
        record("ds:c", "f.json#3", eligible=False, reason="non_error_label"),
    ]
    pool, stats = build_pool(records)
    assert [r["sample_id"] for r in pool] == ["ds:a", "ds:b"]
    assert pool[0]["source_ids"] == ["f.json#0", "f.json#2"]
    assert pool[0]["source_id"] == "f.json#0"  # first occurrence is the representative
    assert all(r["split"] == FULL_SPLIT for r in pool)
    assert stats["unique_requests"] == 2
    assert stats["eligible_records"] == 3
    assert stats["duplicate_records"] == 1
    assert stats["exclusions"] == {"non_error_label": 1}
    # the index keeps ineligible records too, so the export can explain them
    assert index_row(records[3])["exclusion_reason"] == "non_error_label"


@pytest.mark.skipif(not eic_root("MathQA").exists(), reason="raw EIC MathQA files not downloaded")
def test_eic_benchmarks_are_opt_in():
    default = list(adapt_eic())
    assert {r.annotations["source_benchmark"] for r in default} == {"GSM8K"}

    mathqa = list(adapt_eic(benchmarks=["MathQA"]))
    assert {r.annotations["source_benchmark"] for r in mathqa} == {"MathQA"}
    assert all(r.source_file.startswith("data/raw/eic/data/generated_cases_MathQA/") for r in mathqa)
    path = eic_root("MathQA") / "operator_error" / "operator_error_100" / "generated_cases_clean.jsonl"
    raw_first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    first = next(r for r in mathqa if r.source_id.endswith("operator_error_100/generated_cases_clean.jsonl#0"))
    assert first.incorrect_solution == raw_first["transformed_solution"]
    assert first.source_error_label == raw_first["wrong_type"]
    # same eligibility rules as GSM8K: the step-position ablation and labels
    # outside the nine error types are excluded
    reasons = {r.exclusion_reason.split(":")[0] for r in mathqa if not r.eligible}
    assert reasons == {"non_error_type_directory", "label_outside_canonical_set"}


def test_unknown_eic_benchmark_is_an_error():
    with pytest.raises(ValueError):
        list(adapt_eic(benchmarks=["SVAMP"]))
