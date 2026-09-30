"""Global question groups and the one train/test split shared by the verifiers and the Student (plan 5.3).

A question group is one question key (NFKC, lowercase, whitespace and punctuation removed: verifier_sft's key)
over the union of the eligible SFT cases and every GSM8K row, so an EIC/Stepwise question and the same GSM8K
question are one group. Groups are split train:test = 80:20 (no validation, user rule 5); the SFT train groups are
then split into halves A (reward verifier) and B (test verifier), 50:50. Consequences, by construction:
  * a question and every solution / pair / condition derived from it sit in one split (and one half);
  * an RL test question is never in the A/B training data, an SFT test question never in RL training.

Every stratum draws from its own numpy RandomState seeded by (seed, purpose, stratum), so a group's assignment
depends only on its own stratum: the SFT split and halves stay fixed when the GSM8K range for RL is decided later
(GSM8K-only groups form their own strata: gsm8k_only|<original split>|unit:<eligible>).
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from .common import sha256_text

TRAIN, TEST = "train", "test"
HALF_A, HALF_B = "A", "B"


def stratum_rng(seed: int, purpose: str, stratum: str):
    import numpy as np

    return np.random.RandomState(int(sha256_text(f"{seed}|{purpose}|{stratum}")[:8], 16))


@dataclass
class Group:
    group_id: str
    sft_ids: list[str] = field(default_factory=list)
    gsm8k: list[tuple[str, int]] = field(default_factory=list)
    stratum: str = ""
    split: str = ""
    half: str | None = None
    forced: list[str] = field(default_factory=list)

    def record(self) -> dict[str, Any]:
        return {"question_group_id": self.group_id, "stratum": self.stratum, "split": self.split, "half": self.half,
                "forced": self.forced, "sft_sample_ids": sorted(self.sft_ids),
                "gsm8k_rows": [f"{s}:{i}" for s, i in sorted(self.gsm8k)]}


def build_groups(cases: Iterable[Mapping[str, Any]], gsm8k_rows: Iterable[Mapping[str, Any]],
                 group_id_of: Callable[[str], str], gsm8k_unit: Callable[[str, int], bool]) -> dict[str, Group]:
    """cases: eligible adopted SFT cases (with question_group_id and error_id). Strata are assigned here."""
    groups: dict[str, Group] = {}
    votes: dict[str, Counter] = defaultdict(Counter)
    for c in cases:
        g = groups.setdefault(c["question_group_id"], Group(c["question_group_id"]))
        g.sft_ids.append(c["sample_id"])
        votes[g.group_id][f"{c['dataset']}|{c['benchmark'] or '-'}|{c['error_id']}"] += 1
    for r in gsm8k_rows:
        gid = group_id_of(r["question"])
        groups.setdefault(gid, Group(gid)).gsm8k.append((r["split"], int(r["row"])))
    for gid, g in groups.items():
        if votes[gid]:  # the most frequent case stratum, ties -> smallest (as in the v2 split)
            top = max(votes[gid].values())
            g.stratum = min(k for k, v in votes[gid].items() if v == top)
        else:
            split, row = min(g.gsm8k)
            g.stratum = f"gsm8k_only|{split}|unit:{gsm8k_unit(split, row)}"
    return groups


def assign_split(groups: Mapping[str, Group], test_ratio: float, seed: int,
                 forced_train: Mapping[str, list[str]]) -> dict[str, Any]:
    """In place. Forced groups go to train and are left out of their stratum's draw."""
    strata: dict[str, list[str]] = defaultdict(list)
    for gid, g in groups.items():
        if gid in forced_train:
            g.split = TRAIN
            g.forced = sorted(set(g.forced) | set(forced_train[gid]))
        else:
            strata[g.stratum].append(gid)
    per_stratum = {}
    for stratum in sorted(strata):
        gids = sorted(strata[stratum])
        order = [gids[i] for i in stratum_rng(seed, "split", stratum).permutation(len(gids))]
        n_test = math.floor(len(order) * test_ratio + 0.5)
        for i, gid in enumerate(order):
            groups[gid].split = TEST if i < n_test else TRAIN
        per_stratum[stratum] = {"groups": len(order), "test": n_test, "train": len(order) - n_test}
    return {"test_ratio": test_ratio, "per_stratum": per_stratum,
            "forced_train": {gid: forced_train[gid] for gid in sorted(forced_train) if gid in groups}}


def assign_halves(groups: Mapping[str, Group], seed: int, forced_a: Mapping[str, list[str]]) -> dict[str, Any]:
    """In place, SFT train groups only. Half of each stratum to A; an odd stratum gives its extra group to A and B
    in turn (sorted stratum order), as verifier_sft/split_train_halves.py did."""
    strata: dict[str, list[str]] = defaultdict(list)
    for gid, g in groups.items():
        if g.split != TRAIN or not g.sft_ids:
            continue
        if gid in forced_a:
            g.half = HALF_A
            g.forced = sorted(set(g.forced) | set(forced_a[gid]))
        else:
            strata[g.stratum].append(gid)
    per_stratum, odd = {}, 0
    for stratum in sorted(strata):
        gids = sorted(strata[stratum])
        order = [gids[i] for i in stratum_rng(seed, "half", stratum).permutation(len(gids))]
        n_a = len(order) // 2
        if len(order) % 2:
            n_a += 1 if odd % 2 == 0 else 0
            odd += 1
        for i, gid in enumerate(order):
            groups[gid].half = HALF_A if i < n_a else HALF_B
        per_stratum[stratum] = {"groups": len(order), "A": n_a, "B": len(order) - n_a}
    return {"per_stratum": per_stratum, "forced_a": {gid: forced_a[gid] for gid in sorted(forced_a) if gid in groups}}


def assign_validation(train_questions: Iterable[Mapping[str, Any]], groups: Mapping[str, Group], ratio: float,
                      seed: int) -> tuple[set[str], dict[str, Any]]:
    """RL validation groups (user decision 2026-09-30: RL train 90:10 train/validation, test unchanged).

    Size = ratio x all RL train questions; drawn only from GSM8K-only train groups (no SFT solution in the group, so
    neither verifier trained on a validation question), in each such stratum at the same rate, with its own
    per-stratum RandomState. Returns the validation question-group ids.
    """
    qs = list(train_questions)
    pool: dict[str, set[str]] = defaultdict(set)
    for q in qs:
        g = groups[q["question_group_id"]]
        if g.split != TRAIN:
            raise ValueError(f"{q['question_group_id']} is not a train group")
        if not g.sft_ids:
            pool[g.stratum].add(g.group_id)
    n_pool = sum(len(v) for v in pool.values())
    rate = ratio * len(qs) / n_pool if n_pool else 0.0
    val: set[str] = set()
    per_stratum = {}
    for stratum in sorted(pool):
        gids = sorted(pool[stratum])
        order = [gids[i] for i in stratum_rng(seed, "rl_validation", stratum).permutation(len(gids))]
        n = math.floor(len(order) * rate + 0.5)
        val.update(order[:n])
        per_stratum[stratum] = {"groups": len(order), "validation": n}
    return val, {"ratio": ratio, "rate_within_gsm8k_only_groups": rate, "per_stratum": per_stratum}


def region(split: str, half: str | None) -> str:
    """SFT data regions: half_a / half_b (train) and test."""
    if split == TEST:
        return "test"
    if half == HALF_A:
        return "half_a"
    if half == HALF_B:
        return "half_b"
    raise ValueError(f"train group without a half (split={split!r}, half={half!r})")
