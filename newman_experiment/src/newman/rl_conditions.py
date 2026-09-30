"""RL conditions (Q, reference answer, N, E, condition_id) on GSM8K questions (plan 5.6).

E is chosen first, then N = mapping(E). The two unit-related types go only to allowlisted questions; every other
question loses only those two candidates (it is never dropped). All conditions of a question are in its split.
The number of conditions per question, the rule and the scale are open decisions (REQUIRED in configs/data.yaml);
the options below are what prepare_data.py --stage audit sizes for that decision.

  balanced   questions in a seeded order; each takes the `k` eligible types with the smallest running count in its
             split (ties broken by a seeded key), so types are used about equally often within train and within test
  all_types  every eligible type for every question
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping

from .common import sha256_text
from .taxonomy import Taxonomy

ASSIGNMENTS = ("balanced", "all_types")


def _key(seed: int, *parts: Any) -> int:
    return int(sha256_text("|".join(map(str, (seed, *parts))))[:12], 16)


def select_questions(questions: list[Mapping[str, Any]], max_questions: int | str, seed: int, split: str) -> list[Mapping[str, Any]]:
    """`all`, or a seeded subset of that many questions (sorted by GSM8K split/row afterwards)."""
    ordered = sorted(questions, key=lambda q: (q["gsm8k_split"], q["gsm8k_row"]))
    if max_questions == "all" or int(max_questions) >= len(ordered):
        return ordered
    picked = sorted(ordered, key=lambda q: _key(seed, "rl_questions", split, q["gsm8k_split"], q["gsm8k_row"]))[: int(max_questions)]
    return sorted(picked, key=lambda q: (q["gsm8k_split"], q["gsm8k_row"]))


def eligible_types(question: Mapping[str, Any], taxonomy: Taxonomy) -> list[str]:
    return [t for t in taxonomy.adopted_ids() if not taxonomy.types[t].unit_related or question["unit_conversion_eligible"] is True]


def assign(questions: Iterable[Mapping[str, Any]], taxonomy: Taxonomy, k: int | str, assignment: str, seed: int,
           split: str) -> list[dict[str, Any]]:
    if assignment not in ASSIGNMENTS:
        raise ValueError(f"rl_data.type_assignment must be one of {ASSIGNMENTS}, got {assignment!r}")
    qs = list(questions)
    counts: Counter = Counter()
    rows = []
    order = sorted(qs, key=lambda q: _key(seed, "rl_order", split, q["gsm8k_split"], q["gsm8k_row"]))
    for q in order:
        pool = eligible_types(q, taxonomy)
        if assignment == "all_types":
            chosen = pool
        else:
            if int(k) > len(pool):
                raise ValueError(f"k={k} exceeds the {len(pool)} eligible types of {q['gsm8k_split']}:{q['gsm8k_row']}")
            ranked = sorted(pool, key=lambda t: (counts[t], _key(seed, "rl_tie", split, q["gsm8k_split"], q["gsm8k_row"], t)))
            chosen = sorted(ranked[: int(k)])
        for t in chosen:
            counts[t] += 1
            rows.append(condition_row(q, t, taxonomy))
    return sorted(rows, key=lambda r: r["condition_id"])


def condition_row(q: Mapping[str, Any], error_id: str, taxonomy: Taxonomy) -> dict[str, Any]:
    return {
        "condition_id": f"gsm8k-{q['gsm8k_split']}-{q['gsm8k_row']:05d}__{error_id}",
        "question_group_id": q["question_group_id"],
        "split": q["split"],
        "question": q["question"],
        "source_error_id": error_id,
        "newman_stage": taxonomy.stage_of(error_id),
        "unit_conversion_eligible": q["unit_conversion_eligible"],
        "gsm8k_split": q["gsm8k_split"],
        "gsm8k_row": q["gsm8k_row"],
    }


def scenario_sizes(questions_by_split: Mapping[str, list[Mapping[str, Any]]], taxonomy: Taxonomy, prompts_per_step: int,
                   ks: Iterable[int] = (1, 2, 4)) -> list[dict[str, Any]]:
    """Condition counts and optimizer steps per epoch for the audit table (no decision is taken here)."""
    out = []
    for label, k in [*((f"balanced k={k}", k) for k in ks), ("all_types", None)]:
        row = {"scenario": label}
        for split, qs in questions_by_split.items():
            n = sum(len(eligible_types(q, taxonomy)) for q in qs) if k is None else len(qs) * k
            row[f"{split}_questions"] = len(qs)
            row[f"{split}_conditions"] = n
        row["train_steps_per_epoch"] = row.get("train_conditions", 0) // prompts_per_step
        out.append(row)
    return out
