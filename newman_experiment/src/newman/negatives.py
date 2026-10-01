"""One positive and one negative per anchor case, drawn once and fixed in the manifest (plan 5.4, 5.5).

positive  (Q, S, N, E)   -> aligned       E = the case's own adopted source type, N = mapping(E)
negative  (Q, S, N', E') -> not_aligned   E' uniform over the adopted types of the candidate scope other than E
                                          (same-stage types included); N' = mapping(E')
Candidate scope (configs/data.yaml negatives.candidates):
  same_dataset       the anchor's own source dataset (plan 4.3; in use again since 2026-10-01)
  all_adopted_types  all 16 types, as llm_tutee_tutor finetuning. Tried on 2026-10-01 and dropped: the verifiers then
                     rejected every other-dataset negative (0/360 accepted) but accepted 32-44% of same-dataset ones,
                     i.e. they learned the label's source dataset instead of the error.
Unit priority (user decision 2026-10-01): on an allowlisted question whose own type is not unit-related, E' is drawn
uniformly from the two unit-related types only, because those questions are the only places the unit types can be
negatives. An anchor whose own type is unit-related keeps the uniform draw (the other unit type is a near-synonym).
Q and S are never replaced. The two unit-related types are candidates only when the question is on the
confirmed unit-conversion allowlist (eligibility True); unknown (None) and False both drop them, and nothing
else is restricted. An anchor without a candidate is dropped with its positive (1:1 pairs), never relaxed.

Second negative (configs/data.yaml negatives.cross_dataset_different_stage, user decision 2026-10-01, data v3):
one more negative per anchor, E'' uniform over the adopted types of ANOTHER source dataset whose Newman stage differs
from the anchor's (unit-related types only on allowlisted questions, with the same unit priority). It is drawn with
its own RNG (random.Random(f"{seed}|cross_dataset_different_stage"), once per region) after the same-dataset draw,
so the same-dataset negatives are identical to the one-negative version. pair_id suffix `::neg_cross`.
An anchor without a cross candidate is dropped with its other rows (never relaxed).

RNG: random.Random(seed), created once per region (half_a, half_b, test); anchors in sample_id order and
candidates in type-id order, so each region's pairs are independent of the other regions and of epochs.
No semantic review of negatives: targets are automatic (reported as a limitation, plan 4.3).
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping

from .taxonomy import Taxonomy

REGIONS = ("half_a", "half_b", "test")
ALIGNED, NOT_ALIGNED = "aligned", "not_aligned"


SCOPES = ("same_dataset", "all_adopted_types")


def candidates(anchor: Mapping[str, Any], taxonomy: Taxonomy, scope: str = "same_dataset") -> tuple[list[str], list[str]]:
    """(allowed negative types, unit-related types removed because the question is not confirmed eligible)."""
    if scope not in SCOPES:
        raise ValueError(f"negatives.candidates must be one of {SCOPES}, got {scope!r}")
    pool = taxonomy.types_for_dataset(anchor["dataset"]) if scope == "same_dataset" else taxonomy.types.values()
    allowed, removed = [], []
    for t in sorted(pool, key=lambda t: t.id):
        if t.id == anchor["error_id"]:
            continue
        if t.unit_related and anchor["unit_conversion_eligible"] is not True:
            removed.append(t.id)
            continue
        allowed.append(t.id)
    return allowed, removed


def cross_candidates(anchor: Mapping[str, Any], taxonomy: Taxonomy) -> tuple[list[str], list[str]]:
    """Second negative: types of another source dataset at another Newman stage (allowed, unit types removed)."""
    allowed, removed = [], []
    for t in sorted(taxonomy.types.values(), key=lambda t: t.id):
        if t.dataset == anchor["dataset"] or t.newman_stage == anchor["newman_stage"]:
            continue
        if t.unit_related and anchor["unit_conversion_eligible"] is not True:
            removed.append(t.id)
            continue
        allowed.append(t.id)
    return allowed, removed


def pair_record(anchor: Mapping[str, Any], target_error_id: str, target: str, taxonomy: Taxonomy,
                suffix: str | None = None) -> dict[str, Any]:
    target_stage = taxonomy.stage_of(target_error_id)
    target_dataset = taxonomy.types[target_error_id].dataset
    kind = relation = None
    if target == NOT_ALIGNED:
        kind = "same_stage" if target_stage == anchor["newman_stage"] else "different_stage"
        relation = "same_dataset" if target_dataset == anchor["dataset"] else "other_dataset"
    return {
        "pair_id": f"{anchor['sample_id']}::{suffix or ('pos' if target == ALIGNED else 'neg')}",
        "region": anchor["region"],
        "split": anchor["split"],
        "half": anchor["half"],
        "target": target,
        "anchor_sample_id": anchor["sample_id"],
        "question_group_id": anchor["question_group_id"],
        "dataset": anchor["dataset"],
        "benchmark": anchor["benchmark"],
        "anchor_error_id": anchor["error_id"],
        "anchor_newman_stage": anchor["newman_stage"],
        "target_error_id": target_error_id,
        "target_newman_stage": target_stage,
        "negative_kind": kind,
        "target_dataset": target_dataset,
        "negative_dataset_relation": relation,
        "unit_conversion_eligible": anchor["unit_conversion_eligible"],
        "question": anchor["question"],
        "solution": anchor["solution"],
    }


def unit_priority(anchor: Mapping[str, Any], allowed: list[str], taxonomy: Taxonomy) -> list[str]:
    """The unit-related candidates when the priority applies, else [] (then the draw is uniform over `allowed`)."""
    if anchor["unit_conversion_eligible"] is not True or taxonomy.types[anchor["error_id"]].unit_related:
        return []
    return [t for t in allowed if taxonomy.types[t].unit_related]


def make_pairs(anchors: Iterable[Mapping[str, Any]], taxonomy: Taxonomy, seed: int, prioritize_unit: bool = True,
               scope: str = "same_dataset", cross_dataset_different_stage: bool = False
               ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_region: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for a in anchors:
        by_region[a["region"]].append(a)
    unknown = set(by_region) - set(REGIONS)
    if unknown:
        raise ValueError(f"unknown regions {unknown}")
    pairs: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    for region in REGIONS:
        rng = random.Random(seed)
        cross_rng = random.Random(f"{seed}|cross_dataset_different_stage")
        for anchor in sorted(by_region.get(region, []), key=lambda a: a["sample_id"]):
            allowed, removed = candidates(anchor, taxonomy, scope)
            entry = {"anchor_sample_id": anchor["sample_id"], "region": region, "dataset": anchor["dataset"],
                     "question_group_id": anchor["question_group_id"], "anchor_error_id": anchor["error_id"],
                     "unit_conversion_eligible": anchor["unit_conversion_eligible"],
                     "unit_eligibility_source": anchor.get("unit_eligibility_source"),
                     "candidates": allowed, "unit_types_removed": removed,
                     "negative_error_id": None, "negative_kind": None, "status": "paired", "reason": ""}
            if not allowed:
                entry.update(status="excluded", reason="no_negative_candidate")
                manifest.append(entry)
                continue
            priority = unit_priority(anchor, allowed, taxonomy) if prioritize_unit else []
            neg = rng.choice(priority or allowed)
            entry["draw"] = "unit_priority" if priority else "uniform"
            pos_rec = pair_record(anchor, anchor["error_id"], ALIGNED, taxonomy)
            neg_rec = pair_record(anchor, neg, NOT_ALIGNED, taxonomy)
            entry.update(negative_error_id=neg, negative_kind=neg_rec["negative_kind"])
            rows = [pos_rec, neg_rec]
            if cross_dataset_different_stage:
                c_allowed, c_removed = cross_candidates(anchor, taxonomy)
                entry.update(cross_candidates=c_allowed, cross_unit_types_removed=c_removed, cross_negative_error_id=None)
                if not c_allowed:
                    entry.update(status="excluded", reason="no_cross_negative_candidate")
                    manifest.append(entry)
                    continue
                c_priority = unit_priority(anchor, c_allowed, taxonomy) if prioritize_unit else []
                cross = cross_rng.choice(c_priority or c_allowed)
                entry.update(cross_negative_error_id=cross, cross_draw="unit_priority" if c_priority else "uniform")
                rows.append(pair_record(anchor, cross, NOT_ALIGNED, taxonomy, suffix="neg_cross"))
            manifest.append(entry)
            pairs += rows
    return pairs, manifest


def audit(pairs: list[Mapping[str, Any]], manifest: list[Mapping[str, Any]], taxonomy: Taxonomy) -> dict[str, Any]:
    """Per region and type: positives, negatives carrying the type, same/different-stage negatives, unit removals.
    A type with positives but no negative in a region can be answered from its name alone there (plan 5.4)."""
    out: dict[str, Any] = {}
    for region in REGIONS:
        rp = [p for p in pairs if p["region"] == region]
        rm = [m for m in manifest if m["region"] == region]
        pos = Counter(p["target_error_id"] for p in rp if p["target"] == ALIGNED)
        neg = Counter(p["target_error_id"] for p in rp if p["target"] == NOT_ALIGNED)
        kinds = Counter(p["negative_kind"] for p in rp if p["target"] == NOT_ALIGNED)
        relations = Counter(p["negative_dataset_relation"] for p in rp if p["target"] == NOT_ALIGNED)
        removed = Counter(t for m in rm for t in m["unit_types_removed"] + m.get("cross_unit_types_removed", []))
        types = {}
        for tid in taxonomy.adopted_ids():
            types[tid] = {"positives": pos[tid], "negatives_as_target": neg[tid], "unit_candidate_removed": removed[tid]}
        out[region] = {
            "anchors": len(rm), "paired": sum(1 for m in rm if m["status"] == "paired"),
            "no_negative_candidate": sum(1 for m in rm if m["reason"] in ("no_negative_candidate", "no_cross_negative_candidate")),
            "negative_kind": dict(kinds), "negative_dataset_relation": dict(relations), "types": types,
            "types_without_negatives": sorted(t for t, v in types.items() if v["positives"] and not v["negatives_as_target"]),
        }
    return out
