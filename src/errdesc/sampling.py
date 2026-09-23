"""Deterministic stratified sampling over the normalized records.

Rules implemented here (see the handoff document, section 4):

* one sample per question group, also across datasets;
* strata are the original error labels, filled as evenly as possible;
* a stratum that cannot be filled is exhausted and its deficit is redistributed
  deterministically to the other strata;
* no duplication is ever used to reach the target;
* dev/holdout is assigned per dataset with stratum-balanced round robin, so a
  question group can never appear on both sides of the split.
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

from .adapters import NormalizedRecord


@dataclass
class AllocationReport:
    dataset: str
    target: int
    pool_size: int
    label_counts: dict[str, int]
    planned: dict[str, int]
    selected: dict[str, int]
    shortfall: int
    exhausted_strata: list[str]
    redistributed: dict[str, int]
    skipped_duplicate_groups: int
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "target": self.target,
            "pool_size": self.pool_size,
            "label_counts": self.label_counts,
            "planned_allocation": self.planned,
            "selected_allocation": self.selected,
            "shortfall": self.shortfall,
            "exhausted_strata": self.exhausted_strata,
            "redistributed": self.redistributed,
            "skipped_duplicate_question_groups": self.skipped_duplicate_groups,
            "notes": self.notes,
        }


def plan_allocation(target: int, strata: Sequence[str], counts: dict[str, int]) -> dict[str, int]:
    """Even split of ``target`` over ``strata``; leftovers go to the largest pools."""
    if not strata:
        return {}
    base, remainder = divmod(target, len(strata))
    order = sorted(strata, key=lambda s: (-counts.get(s, 0), s))
    planned = {s: base for s in strata}
    for stratum in order[:remainder]:
        planned[stratum] += 1
    return planned


def _capacity_order(strata: Sequence[str], counts: dict[str, int]) -> list[str]:
    return sorted(strata, key=lambda s: (-counts.get(s, 0), s))


def redistribute(
    planned: dict[str, int], available: dict[str, int]
) -> tuple[dict[str, int], dict[str, int], list[str], int]:
    """Cap each stratum at its availability and hand the deficit to the others."""
    final = {s: min(n, available.get(s, 0)) for s, n in planned.items()}
    exhausted = sorted(s for s in planned if final[s] < planned[s])
    deficit = sum(planned.values()) - sum(final.values())
    added: dict[str, int] = defaultdict(int)
    order = _capacity_order(list(planned), available)
    while deficit > 0:
        progressed = False
        for stratum in order:
            if deficit == 0:
                break
            if final[stratum] < available.get(stratum, 0):
                final[stratum] += 1
                added[stratum] += 1
                deficit -= 1
                progressed = True
        if not progressed:
            break
    return final, dict(added), exhausted, deficit


def _interleave_by_key(
    records: list[NormalizedRecord],
    rng: random.Random,
    diversity_key: Callable[[NormalizedRecord], str] | None,
) -> list[NormalizedRecord]:
    """Shuffle, then round-robin over the diversity key so buckets stay mixed."""
    shuffled = sorted(records, key=lambda r: r.sample_id)
    rng.shuffle(shuffled)
    if diversity_key is None:
        return shuffled
    buckets: dict[str, list[NormalizedRecord]] = defaultdict(list)
    for record in shuffled:
        buckets[diversity_key(record)].append(record)
    keys = sorted(buckets)
    rng.shuffle(keys)
    ordered: list[NormalizedRecord] = []
    index = 0
    while any(buckets[k] for k in keys):
        for key in keys:
            if buckets[key]:
                ordered.append(buckets[key].pop(0))
        index += 1
    return ordered


def sample_dataset(
    dataset: str,
    records: Iterable[NormalizedRecord],
    target: int,
    seed: int,
    used_question_groups: set[str],
    diversity_key: Callable[[NormalizedRecord], str] | None = None,
) -> tuple[list[NormalizedRecord], AllocationReport]:
    pool = [r for r in records if r.eligible]
    label_counts = Counter(r.stratum for r in pool)
    strata = sorted(label_counts)

    by_stratum: dict[str, list[NormalizedRecord]] = defaultdict(list)
    for record in pool:
        by_stratum[record.stratum].append(record)

    rng_order = {
        stratum: _interleave_by_key(
            by_stratum[stratum],
            random.Random(f"{seed}|{dataset}|{stratum}"),
            diversity_key,
        )
        for stratum in strata
    }

    # Availability after removing question groups already taken (by an earlier
    # dataset) and collapsing duplicate groups inside the stratum itself.
    available: dict[str, int] = {}
    skipped_duplicates = 0
    for stratum in strata:
        seen_groups: set[str] = set()
        count = 0
        for record in rng_order[stratum]:
            group = record.question_group_id
            if group in used_question_groups or group in seen_groups:
                continue
            seen_groups.add(group)
            count += 1
        available[stratum] = count

    planned = plan_allocation(target, strata, dict(label_counts))
    final, added, exhausted, deficit = redistribute(planned, available)

    selected: list[NormalizedRecord] = []
    selected_counts: dict[str, int] = {}
    local_groups: set[str] = set()
    for stratum in strata:
        quota = final.get(stratum, 0)
        taken = 0
        for record in rng_order[stratum]:
            if taken >= quota:
                break
            group = record.question_group_id
            if group in used_question_groups or group in local_groups:
                skipped_duplicates += 1
                continue
            local_groups.add(group)
            selected.append(record)
            taken += 1
        selected_counts[stratum] = taken
    used_question_groups.update(local_groups)

    report = AllocationReport(
        dataset=dataset,
        target=target,
        pool_size=len(pool),
        label_counts=dict(sorted(label_counts.items())),
        planned=planned,
        selected=selected_counts,
        shortfall=target - len(selected),
        exhausted_strata=exhausted,
        redistributed=added,
        skipped_duplicate_groups=skipped_duplicates,
    )
    if deficit:
        report.notes.append(
            f"{deficit} slot(s) could not be redistributed: the eligible pool is exhausted."
        )
    return selected, report


def assign_splits(
    dataset: str,
    selected: list[NormalizedRecord],
    dev_n: int,
    seed: int,
) -> None:
    """Stratum-balanced dev/holdout assignment, in place."""
    buckets: dict[str, list[NormalizedRecord]] = defaultdict(list)
    for record in selected:
        buckets[record.stratum].append(record)
    rng = random.Random(f"{seed}|{dataset}|split")
    for stratum in buckets:
        buckets[stratum].sort(key=lambda r: r.sample_id)
        rng.shuffle(buckets[stratum])
    keys = sorted(buckets, key=lambda s: (-len(buckets[s]), s))
    dev: list[NormalizedRecord] = []
    while len(dev) < min(dev_n, len(selected)):
        progressed = False
        for key in keys:
            if len(dev) >= dev_n:
                break
            if buckets[key]:
                dev.append(buckets[key].pop(0))
                progressed = True
        if not progressed:
            break
    dev_ids = {r.sample_id for r in dev}
    for record in selected:
        record.split = "dev" if record.sample_id in dev_ids else "holdout"
