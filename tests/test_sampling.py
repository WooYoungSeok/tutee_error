"""Stratified sampling: allocation, exhaustion, duplicates, splits, determinism."""

from errdesc.adapters import NormalizedRecord
from errdesc.sampling import assign_splits, plan_allocation, redistribute, sample_dataset


def make_records(spec: dict[str, int], dataset="ds", group_prefix="g") -> list[NormalizedRecord]:
    records = []
    index = 0
    for label, count in spec.items():
        for _ in range(count):
            records.append(
                NormalizedRecord(
                    sample_id=f"{dataset}:{index:05d}",
                    dataset=dataset,
                    source_id=str(index),
                    source_file="f",
                    source_revision="r",
                    question=f"question {index}",
                    incorrect_solution="solution",
                    source_error_label=label,
                    question_group_id=f"{group_prefix}{index}",
                    stratum=label,
                )
            )
            index += 1
    return records


def test_allocation_matches_handoff_targets():
    assert sorted(plan_allocation(50, ["a", "b", "c"], {"a": 314, "b": 232, "c": 64}).values()) == [16, 17, 17]
    six = plan_allocation(50, list("abcdef"), {k: 100 - i for i, k in enumerate("abcdef")})
    assert sorted(six.values()) == [8, 8, 8, 8, 9, 9]
    nine = plan_allocation(50, list("abcdefghi"), {k: 100 for k in "abcdefghi"})
    assert sorted(nine.values()) == [5, 5, 5, 5, 6, 6, 6, 6, 6]
    assert sorted(plan_allocation(50, list("abcde"), {k: 100 for k in "abcde"}).values()) == [10] * 5


def test_redistribution_when_a_stratum_is_short():
    planned = {"a": 10, "b": 10, "c": 10}
    final, added, exhausted, deficit = redistribute(planned, {"a": 3, "b": 50, "c": 50})
    assert final["a"] == 3
    assert exhausted == ["a"]
    assert sum(final.values()) == 30
    assert deficit == 0
    assert sum(added.values()) == 7


def test_shortfall_is_reported_not_padded():
    records = make_records({"x": 4, "y": 4})
    selected, report = sample_dataset("ds", records, target=50, seed=42, used_question_groups=set())
    assert len(selected) == 8
    assert report.shortfall == 42
    assert len({r.sample_id for r in selected}) == 8
    assert report.notes and "exhausted" in report.notes[0]


def test_one_case_per_question_group_within_and_across_datasets():
    records = make_records({"x": 6}, dataset="a", group_prefix="shared")
    used: set[str] = set()
    first, _ = sample_dataset("a", records, target=3, seed=42, used_question_groups=used)
    other = make_records({"x": 6}, dataset="b", group_prefix="shared")
    second, _ = sample_dataset("b", other, target=3, seed=42, used_question_groups=used)
    groups_first = {r.question_group_id for r in first}
    groups_second = {r.question_group_id for r in second}
    assert not (groups_first & groups_second)
    assert len(groups_first) == 3


def test_duplicate_groups_inside_one_dataset_are_collapsed():
    records = make_records({"x": 5})
    for record in records:
        record.question_group_id = "same"
    selected, report = sample_dataset("ds", records, target=5, seed=42, used_question_groups=set())
    assert len(selected) == 1
    assert report.shortfall == 4


def test_sampling_is_deterministic_for_a_seed():
    records = make_records({"x": 40, "y": 40})
    first, _ = sample_dataset("ds", records, target=20, seed=42, used_question_groups=set())
    second, _ = sample_dataset("ds", records, target=20, seed=42, used_question_groups=set())
    third, _ = sample_dataset("ds", records, target=20, seed=7, used_question_groups=set())
    assert [r.sample_id for r in first] == [r.sample_id for r in second]
    assert [r.sample_id for r in first] != [r.sample_id for r in third]


def test_split_is_stratum_balanced_and_disjoint():
    records = make_records({"x": 25, "y": 25})
    selected, _ = sample_dataset("ds", records, target=50, seed=42, used_question_groups=set())
    assign_splits("ds", selected, dev_n=10, seed=42)
    dev = [r for r in selected if r.split == "dev"]
    holdout = [r for r in selected if r.split == "holdout"]
    assert len(dev) == 10 and len(holdout) == 40
    assert not ({r.question_group_id for r in dev} & {r.question_group_id for r in holdout})
    assert {r.stratum for r in dev} == {"x", "y"}


def test_ineligible_records_never_enter_the_pool():
    records = make_records({"x": 10})
    for record in records[:8]:
        record.eligible = False
        record.exclusion_reason = "test"
    selected, report = sample_dataset("ds", records, target=10, seed=42, used_question_groups=set())
    assert len(selected) == 2
    assert report.pool_size == 2
