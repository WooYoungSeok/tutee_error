"""Evaluation metrics: the verifiers on the fixed SFT test pairs (plan 6.3) and the Student on RL test (plan 10.3).

Verifier: accuracy, macro-F1, negative recall / false acceptance, positive recall, invalid rate (counted as wrong
everywhere, reported separately), same-stage vs different-stage negatives, per type / stage / dataset / unit
eligibility. The binary verifier outputs one alignment decision for the (N, E) pair: there is no separate stage
accuracy or 16-way type accuracy (plan 10.3).

Student: every rate is a ratio of per-question-group counts, so the paired bootstrap resamples question groups
(all conditions and rollouts of a question together) with one index draw shared by every model.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping, Sequence

from .taxonomy import STAGE_IDS
from .verifier_format import ALIGNED, INVALID, NOT_ALIGNED, _vc

# --- verifier (SFT test pairs) -----------------------------------------------------


def verifier_metrics(rows: Sequence[Mapping[str, Any]], min_support: int = 1) -> dict[str, Any]:
    """rows: pair records with `prediction` (aligned / not_aligned / invalid)."""
    base = _vc.compute_metrics(rows)
    negatives = [r for r in rows if r["target"] == NOT_ALIGNED]
    positives = [r for r in rows if r["target"] == ALIGNED]
    out = {
        **base,
        "negative_recall": base["per_class"][NOT_ALIGNED]["recall"],
        "negative_false_acceptance": base["negative_acceptance_rate"],
        "positive_recall": base["per_class"][ALIGNED]["recall"],
        "invalid_rate_positives": (sum(1 for r in positives if r["prediction"] == INVALID) / len(positives)) if positives else None,
        "invalid_rate_negatives": (sum(1 for r in negatives if r["prediction"] == INVALID) / len(negatives)) if negatives else None,
    }
    out["by_negative_kind"] = _vc.breakdown(negatives, lambda r: r["negative_kind"], min_support)
    out["by_target_type"] = _vc.breakdown(rows, lambda r: r["target_error_id"], min_support)
    out["by_anchor_type"] = _vc.breakdown(rows, lambda r: r["anchor_error_id"], min_support)
    out["by_target_stage"] = _vc.breakdown(rows, lambda r: r["target_newman_stage"], min_support)
    out["by_dataset"] = _vc.breakdown(rows, lambda r: f"{r['dataset']}|{r['benchmark'] or '-'}", min_support)
    out["by_unit_eligibility"] = _vc.breakdown(rows, lambda r: str(r["unit_conversion_eligible"]), min_support)
    return out


def rank_checkpoints(results: Mapping[str, Mapping[str, Any]], rule: Sequence[str]) -> list[str]:
    """Order checkpoint names by a rule like ["macro_f1:max", "negative_false_acceptance:min", "test_loss:min"]."""
    def key(name):
        parts = []
        for item in rule:
            metric, _, direction = item.partition(":")
            value = results[name][metric]
            if value is None:
                value = float("inf") if direction == "min" else float("-inf")
            parts.append(-value if direction == "max" else value)
        return tuple(parts)

    for item in rule:
        if item.partition(":")[2] not in ("max", "min"):
            raise ValueError(f"selection rule item must be metric:max or metric:min, got {item!r}")
    return sorted(results, key=key)


# --- Student (RL test) ---------------------------------------------------------------

COUNT_FIELDS = ("rollouts", "incorrect", "correct", "null", "success", "primary_pass", "both_judged", "secondary_pass",
                "disagree", "conditions", "zero_success_conditions", "truncated", "verifier_samples", "verifier_invalid",
                "total_reward")

RATIOS = {  # metric -> (numerator, denominator)
    "wrong_rate": ("incorrect", "rollouts"),
    "correct_rate": ("correct", "rollouts"),
    "null_rate": ("null", "rollouts"),
    "joint_success": ("success", "rollouts"),
    "accept_given_wrong": ("primary_pass", "incorrect"),
    "secondary_accept_given_wrong": ("secondary_pass", "both_judged"),
    "disagreement_given_wrong": ("disagree", "both_judged"),
    "zero_success_condition_rate": ("zero_success_conditions", "conditions"),
    "truncation_rate": ("truncated", "rollouts"),
    "verifier_invalid_sample_rate": ("verifier_invalid", "verifier_samples"),
    "reward_total_mean": ("total_reward", "rollouts"),
}


def _passes(v: Mapping[str, Any] | None) -> bool:
    return bool(v) and bool(v["labels"]) and all(x == ALIGNED for x in v["labels"])


def group_counts(results: Iterable[Mapping[str, Any]], primary: str, secondary: str | None) -> dict[str, dict[str, float]]:
    """question_group_id -> summed counts (COUNT_FIELDS)."""
    out: dict[str, Counter] = defaultdict(Counter)
    per_condition: dict[str, list[bool]] = defaultdict(list)
    for r in results:
        c = out[r["question_group_id"]]
        verdict = r["answer_check"]["verdict"]
        c["rollouts"] += 1
        c["total_reward"] += r["total"]
        c["truncated"] += int(r["truncated"])
        c["correct" if verdict == "correct" else "incorrect" if verdict == "incorrect" else "null"] += 1
        c["success"] += int(r["in_G"])
        pv = r.get(f"verifier_{primary}")
        if pv:
            c["primary_pass"] += int(_passes(pv))
            c["verifier_samples"] += len(pv["labels"])
            c["verifier_invalid"] += sum(1 for x in pv["labels"] if x == INVALID)
        sv = r.get(f"verifier_{secondary}") if secondary else None
        if pv and sv:
            c["both_judged"] += 1
            c["secondary_pass"] += int(_passes(sv))
            c["disagree"] += int(_passes(pv) != _passes(sv))
        per_condition[(r["question_group_id"], r["condition_id"])].append(bool(r["in_G"]))
    for (gid, _), flags in per_condition.items():
        out[gid]["conditions"] += 1
        out[gid]["zero_success_conditions"] += int(not any(flags))
    return {gid: {f: float(c[f]) for f in COUNT_FIELDS} for gid, c in out.items()}


def ratios(total: Mapping[str, float]) -> dict[str, float | None]:
    return {m: (total[a] / total[b] if total[b] else None) for m, (a, b) in RATIOS.items()}


def _norm_solution(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def student_metrics(results: Sequence[Mapping[str, Any]], group_logs: Sequence[Mapping[str, Any]], primary: str,
                    secondary: str | None, bleu: Any | None = None) -> dict[str, Any]:
    from tutee_rl.rewards import diversity_scores

    counts = group_counts(results, primary, secondary)
    total = {f: sum(c[f] for c in counts.values()) for f in COUNT_FIELDS}
    out: dict[str, Any] = {"counts": total, **ratios(total)}

    def success_by(key):
        groups: dict[str, list[bool]] = defaultdict(list)
        for r in results:
            groups[str(key(r))].append(bool(r["in_G"]))
        return {k: {"n": len(v), "joint_success": sum(v) / len(v)} for k, v in sorted(groups.items())}

    out["by_type"] = success_by(lambda r: r["source_error_id"])
    out["by_stage"] = {k: v for k, v in success_by(lambda r: r["newman_stage"]).items() if k in STAGE_IDS}
    out["by_unit_eligibility"] = success_by(lambda r: r["unit_conversion_eligible"])
    type_rates = [v["joint_success"] for v in out["by_type"].values()]
    out["joint_success_macro_over_types"] = sum(type_rates) / len(type_rates) if type_rates else None

    texts_by_condition: dict[str, dict[int, str]] = defaultdict(dict)
    for r in results:
        texts_by_condition[r["condition_id"]][r["group_pos"]] = r["solution"]
    div, uniq = [], []
    for gl in group_logs:
        acc = gl["accepted"]
        if acc:
            uniq.append(len({_norm_solution(texts_by_condition[gl["condition_id"]][i]) for i in acc}))
        if bleu is not None and len(acc) >= 2:
            texts = [texts_by_condition[gl["condition_id"]][i] for i in range(len(texts_by_condition[gl["condition_id"]]))]
            scores, _ = diversity_scores(texts, acc, bleu)
            div.append(sum(scores.values()) / len(scores))
    out["diversity_mean_in_successes"] = sum(div) / len(div) if div else None
    out["diversity_conditions"] = len(div)
    out["unique_successful_solutions_mean"] = sum(uniq) / len(uniq) if uniq else None
    return out


def paired_bootstrap(counts_by_model: Mapping[str, Mapping[str, Mapping[str, float]]], n_samples: int, seed: int,
                     reference: str | None = None, alpha: float = 0.05) -> dict[str, Any]:
    """Percentile CIs of every RATIOS metric per model and (model - reference), resampling question groups with one
    shared draw per replicate. Covers sampling of test questions only: not the optimism of choosing a checkpoint on
    test, and not seed-to-seed training variance (plan 10.3)."""
    import numpy as np

    models = list(counts_by_model)
    gids = sorted(set.intersection(*(set(c) for c in counts_by_model.values()))) if models else []
    if not gids:
        return {}
    mats = {m: np.array([[counts_by_model[m][g][f] for f in COUNT_FIELDS] for g in gids]) for m in models}
    rng = np.random.RandomState(seed)
    idx = {f: i for i, f in enumerate(COUNT_FIELDS)}
    samples: dict[str, dict[str, list[float]]] = {m: defaultdict(list) for m in models}
    diffs: dict[str, dict[str, list[float]]] = {m: defaultdict(list) for m in models if m != reference}
    for _ in range(n_samples):
        pick = rng.randint(0, len(gids), size=len(gids))
        vals = {}
        for m in models:
            s = mats[m][pick].sum(axis=0)
            vals[m] = {k: (s[idx[a]] / s[idx[b]] if s[idx[b]] else np.nan) for k, (a, b) in RATIOS.items()}
            for k, v in vals[m].items():
                samples[m][k].append(v)
        if reference in vals:
            for m in diffs:
                for k in RATIOS:
                    diffs[m][k].append(vals[m][k] - vals[reference][k])

    def ci(values):
        arr = np.array(values, dtype=float)
        arr = arr[~np.isnan(arr)]
        if not len(arr):
            return None
        lo, hi = np.percentile(arr, [100 * alpha / 2, 100 * (1 - alpha / 2)])
        return [float(lo), float(hi)]

    return {"question_groups": len(gids), "n_samples": n_samples, "seed": seed, "reference": reference,
            "ci": {m: {k: ci(v) for k, v in samples[m].items()} for m in models},
            "diff_vs_reference": {m: {k: ci(v) for k, v in diffs[m].items()} for m in diffs}}
