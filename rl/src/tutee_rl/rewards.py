"""Pure reward arithmetic. No network, no torch: every branch is unit-tested.

Per rollout i of a group H (|H| = num_generations):
  b_i   = -lambda                  answer judged correct, or verdict null
        = 1                        incorrect and both verifier samples `aligned`
        = 0                        incorrect otherwise (not_aligned or invalid)
  G     = {i : incorrect and both aligned},  K = |G|
  aux_i = raw auxiliary score in [0, 1] for i in G when K >= 2, else 0
  trunc_i = -penalty if the completion hit the length limit without EOS, else 0
  R_i   = b_i + w * aux_i + trunc_i      (w = auxiliary_weight, applied by the trainer's reward_weights)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Callable, Sequence

ALIGNED = "aligned"
VERDICTS = ("correct", "incorrect")


# --- main --------------------------------------------------------------------


def verifier_accepts(labels: Sequence[str] | None, aggregation: str = "all_aligned") -> bool:
    if aggregation != "all_aligned":
        raise ValueError(f"unknown verifier aggregation {aggregation!r}")
    return bool(labels) and all(label == ALIGNED for label in labels)


def main_reward(verdict: str | None, verifier_labels: Sequence[str] | None, lam: float, null_reward: float) -> float:
    if verdict is None:
        return null_reward
    if verdict == "correct":
        return -lam
    if verdict == "incorrect":
        if verifier_labels is None:
            raise ValueError("an incorrect answer needs verifier labels")
        return 1.0 if verifier_accepts(verifier_labels) else 0.0
    raise ValueError(f"unexpected verdict {verdict!r}")


# --- truncation --------------------------------------------------------------


@dataclass(frozen=True)
class TruncationInfo:
    truncated: bool          # hit max length without EOS -> penalised
    ends_with_eos: bool
    length: int
    anomaly: bool            # no EOS but shorter than the limit (should not happen with vLLM)


def truncation_info(completion_ids: Sequence[int], eos_ids: set[int], max_completion_tokens: int) -> TruncationInfo:
    """Decided on the real completion token ids (TRL strips padding), not on re-tokenised text."""
    length = len(completion_ids)
    ends_with_eos = length > 0 and completion_ids[-1] in eos_ids
    at_limit = length >= max_completion_tokens
    return TruncationInfo(
        truncated=(not ends_with_eos) and at_limit,
        ends_with_eos=ends_with_eos,
        length=length,
        anomaly=(not ends_with_eos) and not at_limit,
    )


def truncation_reward(info: TruncationInfo, penalty: float) -> float:
    return -penalty if info.truncated else 0.0


# --- diversity (BLEU inside G) -----------------------------------------------


def make_bleu(smooth_method: str = "exp", effective_order: bool = True, tokenize: str = "13a", lowercase: bool = False):
    from sacrebleu.metrics import BLEU

    return BLEU(smooth_method=smooth_method, effective_order=effective_order, tokenize=tokenize, lowercase=lowercase)


def diversity_scores(texts: Sequence[str], accepted: Sequence[int], bleu: Any) -> tuple[dict[int, float], dict[str, Any]]:
    """r_i = 1 - max_{j in G, j != i} sentence_BLEU(S_i | ref S_j) / 100 for i in G when K >= 2.

    Only the index i itself is excluded; an identical string at another index scores similarity 1.
    An empty solution never receives diversity credit.
    """
    scores: dict[int, float] = {}
    matrix: dict[str, float] = {}
    if len(accepted) < 2:
        return scores, {"bleu_matrix": matrix}
    for i in accepted:
        if not texts[i].strip():
            scores[i] = 0.0
            continue
        sims = []
        for j in accepted:
            if j == i:
                continue
            sim = bleu.sentence_score(texts[i], [texts[j]]).score / 100.0
            matrix[f"{i}|{j}"] = sim
            sims.append(sim)
        scores[i] = min(1.0, max(0.0, 1.0 - max(sims)))
    return scores, {"bleu_matrix": matrix}


# --- student-likeness (all unordered pairs inside G) -------------------------


def _rng_seed(*parts: Any) -> int:
    return int.from_bytes(hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).digest()[:4], "little")


def pair_schedule(accepted: Sequence[int], seed: int, step: int, pair_id: str) -> list[tuple[int, int]]:
    """All K(K-1)/2 unordered pairs as (A, B) rollout indices, positions balanced.

    The accepted indices are shuffled with a RandomState derived from (seed, step, pair_id); a pair at
    shuffled positions p < q puts the earlier item in position A when the forward cyclic distance is the
    shorter one. Every item is A in floor or ceil of (K-1)/2 of its comparisons.
    """
    import numpy as np

    k = len(accepted)
    if k < 2:
        return []
    order = list(accepted)
    np.random.RandomState(_rng_seed(seed, step, pair_id)).shuffle(order)
    pairs = []
    for p, q in combinations(range(k), 2):
        d = q - p
        if d < k - d:
            a, b = order[p], order[q]
        elif d > k - d:
            a, b = order[q], order[p]
        else:  # exact half-way (even K): alternate by position
            a, b = (order[p], order[q]) if p % 2 == 0 else (order[q], order[p])
        pairs.append((a, b))
    return pairs


def normalized_win_scores(accepted: Sequence[int], outcomes: Sequence[tuple[int, int, str]]) -> dict[int, float]:
    """Normalized Borda score. outcomes: (a_index, b_index, winner in {A, B, tie}); win 1, tie 0.5, loss 0.

    Requires the complete round robin: a missing or duplicated pair raises instead of scoring partially.
    """
    k = len(accepted)
    if k < 2:
        return {}
    expected = {frozenset(p) for p in combinations(accepted, 2)}
    seen = [frozenset((a, b)) for a, b, _ in outcomes]
    if len(seen) != len(set(seen)) or set(seen) != expected:
        raise ValueError("student-likeness outcomes do not form the complete set of unordered pairs")
    wins = {i: 0.0 for i in accepted}
    for a, b, winner in outcomes:
        if winner == "A":
            wins[a] += 1.0
        elif winner == "B":
            wins[b] += 1.0
        elif winner == "tie":
            wins[a] += 0.5
            wins[b] += 0.5
        else:
            raise ValueError(f"invalid winner {winner!r}")
    return {i: wins[i] / (k - 1) for i in accepted}


# --- group combination -------------------------------------------------------


def combine_group(
    verdicts: Sequence[str | None],
    verifier_labels: Sequence[Sequence[str] | None],
    trunc: Sequence[TruncationInfo],
    aux_fn: Callable[[list[int]], dict[int, float]],
    lam: float,
    null_reward: float,
    trunc_penalty: float,
) -> dict[str, Any]:
    """Rewards for one group. aux_fn(accepted) -> raw aux scores (called only when K >= 2)."""
    n = len(verdicts)
    main = [main_reward(verdicts[i], verifier_labels[i], lam, null_reward) for i in range(n)]
    accepted = [i for i in range(n) if verdicts[i] == "incorrect" and verifier_accepts(verifier_labels[i])]
    aux = [0.0] * n
    if len(accepted) >= 2:
        scores = aux_fn(accepted)
        for i in accepted:
            aux[i] = float(scores[i])
    trunc_r = [truncation_reward(t, trunc_penalty) for t in trunc]
    return {"main": main, "aux": aux, "trunc": trunc_r, "accepted": accepted, "K": len(accepted)}
