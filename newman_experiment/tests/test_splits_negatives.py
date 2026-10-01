"""Global split, halves, negatives and RL conditions on synthetic cases with the real taxonomy."""

from __future__ import annotations

from collections import Counter

from newman.common import resolve
from newman.negatives import make_pairs
from newman.rl_conditions import assign, select_questions
from newman.splits import assign_halves, assign_split, assign_validation, build_groups, region
from newman.taxonomy import Taxonomy
from newman.verifier_format import question_group_id

TAX = Taxonomy.load(resolve("configs/taxonomy.yaml"))


def cases(n_per_type=12):
    out = []
    for t in TAX.types.values():
        for i in range(n_per_type):
            q = f"{t.dataset} question {i} for {t.id}"
            out.append({"sample_id": f"{t.id}:{i:03d}", "dataset": t.dataset, "benchmark": "GSM8K" if t.dataset == "eic" else "",
                        "question_group_id": question_group_id(q), "question": q, "solution": f"solution {i}",
                        "error_id": t.id, "newman_stage": t.newman_stage, "unit_conversion_eligible": (i % 3 == 0) if t.dataset == "eic" else None,
                        "unit_eligibility_source": "test"})
    return out


def gsm8k(n, offset=0):
    return [{"split": "train", "row": offset + i, "question": f"gsm8k only question {offset + i}"} for i in range(n)]


def split_all(cs, rows, forced_train=None, forced_a=None):
    groups = build_groups(cs, rows, question_group_id, lambda s, r: r % 5 == 0)
    assign_split(groups, 0.2, 42, forced_train or {})
    assign_halves(groups, 42, forced_a or {})
    for c in cs:
        g = groups[c["question_group_id"]]
        c.update(split=g.split, half=g.half, region=region(g.split, g.half))
    return groups


def test_sft_question_and_same_gsm8k_question_are_one_group():
    cs = cases(2)
    rows = [{"split": "test", "row": 0, "question": cs[0]["question"].upper() + " ?"}]
    groups = build_groups(cs, rows, question_group_id, lambda s, r: False)
    g = groups[cs[0]["question_group_id"]]
    assert g.gsm8k == [("test", 0)] and g.sft_ids and not g.stratum.startswith("gsm8k_only")


def test_sft_split_does_not_move_when_gsm8k_only_groups_change():
    a = split_all(cases(), gsm8k(50))
    b = split_all(cases(), gsm8k(400, offset=1000))
    sft = [gid for gid, g in a.items() if g.sft_ids]
    assert all((a[g].split, a[g].half) == (b[g].split, b[g].half) for g in sft)


def test_split_ratio_halves_and_forced_groups():
    cs = cases()
    forced = cs[5]["question_group_id"]
    groups = split_all(cs, gsm8k(200), forced_train={forced: ["judge_example"]}, forced_a={forced: ["judge_example"]})
    assert groups[forced].split == "train" and groups[forced].half == "A"
    sft = [g for g in groups.values() if g.sft_ids]
    test_share = sum(1 for g in sft if g.split == "test") / len(sft)
    assert 0.15 < test_share < 0.25
    halves = Counter(g.half for g in sft if g.split == "train")
    assert abs(halves["A"] - halves["B"]) <= len({g.stratum for g in sft}) + 1
    assert all(g.half is None for g in groups.values() if g.split == "test" or not g.sft_ids)


def test_negatives_follow_the_plan_rules():
    cs = cases()
    split_all(cs, gsm8k(20))
    pairs, manifest = make_pairs(cs, TAX, 42)
    pos = {p["anchor_sample_id"]: p for p in pairs if p["target"] == "aligned"}
    neg = {p["anchor_sample_id"]: p for p in pairs if p["target"] == "not_aligned"}
    assert set(pos) == set(neg) == {c["sample_id"] for c in cs}
    for sid, n in neg.items():
        t = TAX.types[n["target_error_id"]]
        assert n["target_error_id"] != n["anchor_error_id"]
        assert n["target_dataset"] == t.dataset == n["dataset"]                # plan 4.3: same source dataset
        assert n["negative_dataset_relation"] == "same_dataset"
        assert n["target_newman_stage"] == t.newman_stage                     # N' = mapping(E')
        assert n["question"] == pos[sid]["question"] and n["solution"] == pos[sid]["solution"]
        if t.unit_related:
            assert n["unit_conversion_eligible"] is True
        assert n["negative_kind"] == ("same_stage" if t.newman_stage == n["anchor_newman_stage"] else "different_stage")
    measurement = [n for n in neg.values() if n["target_error_id"] == "mathedu.measurement_error"]
    assert not measurement                                                  # MathEDU questions are never allowlisted here
    assert all(len(m["candidates"]) + len(m["unit_types_removed"]) == len(TAX.types_for_dataset(m["dataset"])) - 1
               for m in manifest)
    for m in manifest:  # unit priority: an allowlisted non-unit anchor gets a unit-related negative when its dataset has one
        own_unit = TAX.types[m["anchor_error_id"]].unit_related
        unit_available = any(TAX.types[c].unit_related for c in m["candidates"])
        if m["unit_conversion_eligible"] is True and not own_unit and unit_available:
            assert m["draw"] == "unit_priority" and TAX.types[m["negative_error_id"]].unit_related
        else:
            assert m["draw"] == "uniform"
    assert any(m["unit_types_removed"] for m in manifest)
    cross, _ = make_pairs(cs, TAX, 42, scope="all_adopted_types")           # the dropped variant still works
    assert {p["negative_dataset_relation"] for p in cross if p["target"] == "not_aligned"} == {"same_dataset", "other_dataset"}

def test_negatives_are_fixed_and_regions_independent():
    cs = cases()
    split_all(cs, gsm8k(20))
    first, _ = make_pairs(cs, TAX, 42)
    again, _ = make_pairs(list(reversed(cs)), TAX, 42)
    assert first == again
    without_b = [c for c in cs if c["region"] != "half_b"]
    only, _ = make_pairs(without_b, TAX, 42)
    assert [p for p in first if p["region"] == "half_a"] == [p for p in only if p["region"] == "half_a"]


def test_anchor_without_candidate_is_dropped_with_its_positive(monkeypatch):
    cs = [c for c in cases(1) if c["dataset"] == "mathclean"]
    for c in cs:
        c.update(split="train", half="A", region="half_a")
    monkeypatch.setattr(TAX, "types_for_dataset", lambda ds: [TAX.types[cs[0]["error_id"]]])
    pairs, manifest = make_pairs(cs[:1], TAX, 42)
    assert pairs == [] and manifest[0]["reason"] == "no_negative_candidate"


def rl_questions(n):
    return [{"gsm8k_split": "train", "gsm8k_row": i, "question": f"q{i}", "question_group_id": f"g{i}", "split": "train",
             "unit_conversion_eligible": i % 4 == 0} for i in range(n)]


def test_rl_conditions_balanced_and_unit_restricted():
    rows = assign(rl_questions(320), TAX, 1, "balanced", 42, "train")
    assert len(rows) == 320
    counts = Counter(r["source_error_id"] for r in rows)
    assert max(counts.values()) - min(counts.values()) <= 2
    for r in rows:
        assert r["newman_stage"] == TAX.stage_of(r["source_error_id"])
        if TAX.types[r["source_error_id"]].unit_related:
            assert r["unit_conversion_eligible"] is True
    k2 = assign(rl_questions(40), TAX, 2, "balanced", 42, "train")
    per_q = Counter(r["gsm8k_row"] for r in k2)
    assert set(per_q.values()) == {2} and len({(r["gsm8k_row"], r["source_error_id"]) for r in k2}) == 80
    every = assign(rl_questions(4), TAX, None, "all_types", 42, "train")
    assert Counter(r["gsm8k_row"] for r in every) == {0: 16, 1: 14, 2: 14, 3: 14}
    assert assign(rl_questions(40), TAX, 1, "balanced", 42, "train") == assign(rl_questions(40), TAX, 1, "balanced", 42, "train")


def test_question_subset_is_seeded():
    qs = rl_questions(100)
    a = select_questions(qs, 10, 42, "train")
    assert a == select_questions(list(reversed(qs)), 10, 42, "train") and len(a) == 10
    assert select_questions(qs, "all", 42, "train") == qs


def test_rl_validation_only_from_gsm8k_only_train_groups():
    cs = cases()
    rows = gsm8k(400) + [{"split": "test", "row": 0, "question": cs[0]["question"]}]
    groups = split_all(cs, rows)
    train_qs = [{"question_group_id": question_group_id(r["question"])} for r in rows
                if groups[question_group_id(r["question"])].split == "train"]
    val, info = assign_validation(train_qs, groups, 0.1, 42)
    assert all(not groups[g].sft_ids and groups[g].split == "train" for g in val)
    assert abs(len(val) - 0.1 * len(train_qs)) <= len(info["per_stratum"])
    assert val == assign_validation(list(reversed(train_qs)), groups, 0.1, 42)[0]


def test_multi_label_rule_counts_labels_outside_the_pool():
    from newman.sources import exclude_multi_label_solutions

    def case(sid, label, sol="s", reason=""):
        return {"sample_id": sid, "dataset": "stepwise", "question": "Q?", "solution": sol, "source_error_label": label,
                "exclusion_reason": reason}

    cs = [case("a", "Misunderstanding of a question"), case("b", "Misunderstanding of a question", sol="other")]
    raw = [{"dataset": "stepwise", "question": "q ?", "incorrect_solution": "S", "source_error_label": "None of the above"}]
    stats = exclude_multi_label_solutions(cs, raw)
    assert cs[0]["exclusion_reason"] == "multi_label_solution" and cs[1]["exclusion_reason"] == ""
    assert stats["solutions_found_only_with_raw_labels"] == {"stepwise": 1}


def test_second_negative_is_other_dataset_other_stage_and_keeps_the_first():
    """Data v3 (user decision 2026-10-01): + one negative from another dataset at another Newman stage, unit priority."""
    cs = cases()
    split_all(cs, gsm8k(20))
    one, _ = make_pairs(cs, TAX, 42)
    two, manifest = make_pairs(cs, TAX, 42, cross_dataset_different_stage=True)
    assert [p for p in two if not p["pair_id"].endswith("::neg_cross")] == one      # first negatives unchanged
    cross = {p["anchor_sample_id"]: p for p in two if p["pair_id"].endswith("::neg_cross")}
    assert set(cross) == {c["sample_id"] for c in cs}
    for p in cross.values():
        t = TAX.types[p["target_error_id"]]
        assert p["target"] == "not_aligned" and t.dataset != p["dataset"] and t.newman_stage != p["anchor_newman_stage"]
        assert p["negative_dataset_relation"] == "other_dataset" and p["negative_kind"] == "different_stage"
        if t.unit_related:
            assert p["unit_conversion_eligible"] is True
    for m in manifest:
        own_unit = TAX.types[m["anchor_error_id"]].unit_related
        unit_available = any(TAX.types[c].unit_related for c in m["cross_candidates"])
        if m["unit_conversion_eligible"] is True and not own_unit and unit_available:
            assert m["cross_draw"] == "unit_priority" and TAX.types[m["cross_negative_error_id"]].unit_related
        else:
            assert m["cross_draw"] == "uniform"
    assert any(m["cross_draw"] == "unit_priority" for m in manifest)
