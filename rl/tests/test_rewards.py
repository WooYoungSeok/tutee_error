from __future__ import annotations

import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tutee_rl.clients import SchemaViolation, parse_answer_check, parse_winner  # noqa: E402
from tutee_rl.common import render  # noqa: E402
from tutee_rl.rewards import (  # noqa: E402
    combine_group,
    diversity_scores,
    main_reward,
    make_bleu,
    normalized_win_scores,
    pair_schedule,
    truncation_info,
    truncation_reward,
)

LAM, NULL, PEN = 0.75, -0.75, 0.5
A, N, I = "aligned", "not_aligned", "invalid"


# --- main reward -------------------------------------------------------------

def test_main_reward_branches():
    assert main_reward("correct", None, LAM, NULL) == -0.75
    assert main_reward(None, None, LAM, NULL) == -0.75
    assert main_reward("incorrect", [A, A], LAM, NULL) == 1.0
    assert main_reward("incorrect", [A, N], LAM, NULL) == 0.0
    assert main_reward("incorrect", [A, I], LAM, NULL) == 0.0
    assert main_reward("incorrect", [N, N], LAM, NULL) == 0.0
    with pytest.raises(ValueError):
        main_reward("incorrect", None, LAM, NULL)


# --- truncation --------------------------------------------------------------

EOS = {151645, 151643}


def test_truncation_eos_boundary():
    at_limit_eos = truncation_info([1] * 9 + [151645], EOS, 10)
    assert not at_limit_eos.truncated and truncation_reward(at_limit_eos, PEN) == 0.0
    at_limit_no_eos = truncation_info([1] * 10, EOS, 10)
    assert at_limit_no_eos.truncated and truncation_reward(at_limit_no_eos, PEN) == -0.5
    short_eos = truncation_info([1, 2, 151643], EOS, 10)
    assert not short_eos.truncated and not short_eos.anomaly
    short_no_eos = truncation_info([1, 2, 3], EOS, 10)
    assert not short_no_eos.truncated and short_no_eos.anomaly


def test_no_tag_reward_in_total():
    trunc = [truncation_info([1, 151645], EOS, 10)] * 3
    out = combine_group(["incorrect"] * 3, [[A, A]] * 3, trunc, lambda acc: {i: 0.0 for i in acc}, LAM, NULL, PEN)
    assert set(out) == {"main", "aux", "trunc", "accepted", "K"}
    assert out["trunc"] == [0.0, 0.0, 0.0]


# --- group combination and G -------------------------------------------------

def _trunc(n):
    return [truncation_info([1, 151645], EOS, 10)] * n


def test_group_K_0_and_1_get_no_aux():
    calls = []

    def aux(acc):
        calls.append(acc)
        return {i: 1.0 for i in acc}

    zero = combine_group(["correct"] * 8, [None] * 8, _trunc(8), aux, LAM, NULL, PEN)
    assert zero["K"] == 0 and zero["aux"] == [0.0] * 8 and zero["main"] == [-0.75] * 8
    one = combine_group(["incorrect"] + ["correct"] * 7, [[A, A]] + [None] * 7, _trunc(8), aux, LAM, NULL, PEN)
    assert one["K"] == 1 and one["aux"] == [0.0] * 8 and one["main"][0] == 1.0
    assert calls == []


def test_group_only_accepted_get_aux():
    verdicts = ["incorrect", "incorrect", "incorrect", "correct", None, "incorrect", "incorrect", "incorrect"]
    labels = [[A, A], [A, N], [A, A], None, None, [I, A], [A, A], [N, N]]
    out = combine_group(verdicts, labels, _trunc(8), lambda acc: {i: 0.5 for i in acc}, LAM, NULL, PEN)
    assert out["accepted"] == [0, 2, 6] and out["K"] == 3
    assert out["aux"] == [0.5, 0.0, 0.5, 0.0, 0.0, 0.0, 0.5, 0.0]
    assert out["main"] == [1.0, 0.0, 1.0, -0.75, -0.75, 0.0, 1.0, 0.0]


# --- BLEU --------------------------------------------------------------------

def test_bleu_excludes_self_only_and_identical_scores_zero():
    bleu = make_bleu()
    texts = ["the cat sat on the mat today", "the cat sat on the mat today", "a completely different answer here", "x"]
    scores, detail = diversity_scores(texts, [0, 1, 2], bleu)
    assert scores[0] == pytest.approx(0.0) and scores[1] == pytest.approx(0.0)  # identical string at another index
    assert scores[2] > 0.5
    assert "0|0" not in detail["bleu_matrix"]


def test_bleu_signature_available_before_first_score():
    assert make_bleu().get_signature().format().startswith("nrefs:1|case:mixed|eff:yes|tok:13a|smooth:exp")


def test_bleu_ignores_non_accepted_texts():
    bleu = make_bleu()
    base = ["alpha beta gamma delta", "epsilon zeta eta theta", "alpha beta gamma delta"]
    s1, _ = diversity_scores(base, [0, 1], bleu)
    changed = list(base)
    changed[2] = "totally unrelated words appear"
    s2, _ = diversity_scores(changed, [0, 1], bleu)
    assert s1 == s2


def test_bleu_empty_solution_gets_no_credit():
    scores, _ = diversity_scores(["", "some real working here"], [0, 1], make_bleu())
    assert scores[0] == 0.0


# --- pairwise student-likeness -----------------------------------------------

@pytest.mark.parametrize("k", [2, 3, 4, 5, 6, 7, 8])
def test_pair_schedule_complete_and_balanced(k):
    accepted = [0, 2, 3, 5, 6, 7, 1, 4][:k]
    pairs = pair_schedule(accepted, seed=42, step=3, pair_id="0__1672")
    assert len(pairs) == k * (k - 1) // 2
    assert {frozenset(p) for p in pairs} == {frozenset(p) for p in combinations(accepted, 2)}
    as_a = Counter(a for a, _ in pairs)
    counts = [as_a.get(i, 0) for i in accepted]
    assert max(counts) - min(counts) <= 1
    assert pairs == pair_schedule(accepted, seed=42, step=3, pair_id="0__1672")  # deterministic


def test_win_scores_mapping_from_positions():
    # candidate 5 placed as B wins against 2 -> credit goes to 5, not to "B"
    scores = normalized_win_scores([2, 5], [(2, 5, "B")])
    assert scores == {2: 0.0, 5: 1.0}


def test_win_scores_examples_from_plan():
    s = normalized_win_scores([1, 2, 3], [(1, 2, "A"), (1, 3, "A"), (2, 3, "A")])
    assert s == {1: 1.0, 2: 0.5, 3: 0.0}
    cyc = normalized_win_scores([1, 2, 3], [(1, 2, "A"), (2, 3, "A"), (3, 1, "A")])
    assert cyc == {1: 0.5, 2: 0.5, 3: 0.5}
    order4 = normalized_win_scores([0, 1, 2, 3], [(a, b, "A") for a, b in combinations([0, 1, 2, 3], 2)])
    assert order4 == pytest.approx({0: 1.0, 1: 2 / 3, 2: 1 / 3, 3: 0.0})
    ties = normalized_win_scores([0, 1], [(0, 1, "tie")])
    assert ties == {0: 0.5, 1: 0.5}


def test_win_scores_refuse_incomplete_round_robin():
    with pytest.raises(ValueError):
        normalized_win_scores([1, 2, 3], [(1, 2, "A"), (1, 3, "A")])
    with pytest.raises(ValueError):
        normalized_win_scores([1, 2], [(1, 2, "A"), (2, 1, "B")])


# --- answer-check schema -----------------------------------------------------

def test_parse_answer_check_valid_and_null():
    ok = parse_answer_check('{"extracted_answer": "4.32", "verdict": "correct", "reason": "matches"}')
    assert ok["verdict"] == "correct"
    null = parse_answer_check('{"extracted_answer": null, "verdict": null, "reason": "No clear final answer can be extracted."}')
    assert null["extracted_answer"] is None and null["verdict"] is None
    kept = parse_answer_check('{"extracted_answer": "7", "verdict": null, "reason": "conflicting reference"}')
    assert kept["extracted_answer"] == "7" and kept["verdict"] is None
    # a student may really answer "none" (e.g. "this data set has no mode"): with a verdict it is an answer
    none_answer = parse_answer_check('{"extracted_answer": "none", "verdict": "incorrect", "reason": "modes are 1 and 7"}')
    assert none_answer["extracted_answer"] == "none" and none_answer["verdict"] == "incorrect"


@pytest.mark.parametrize("text", [
    '{"extracted_answer": null, "verdict": "incorrect", "reason": "x"}',   # null answer with a verdict
    '{"extracted_answer": "null", "verdict": null, "reason": "x"}',        # string "null"
    '{"extracted_answer": "None", "verdict": null, "reason": "x"}',
    '{"extracted_answer": "null", "verdict": "incorrect", "reason": "x"}',  # string "null" even with a verdict
    '{"extracted_answer": "", "verdict": "incorrect", "reason": "x"}',
    '{"extracted_answer": "5", "verdict": "wrong", "reason": "x"}',
    '{"extracted_answer": "5", "verdict": "incorrect"}',
    '{"extracted_answer": "5", "verdict": "incorrect", "reason": "x", "extra": 1}',
    "not json",
])
def test_parse_answer_check_violations(text):
    with pytest.raises(SchemaViolation):
        parse_answer_check(text)


def test_parse_winner():
    assert parse_winner('{"winner": "tie"}', allow_tie=True) == "tie"
    with pytest.raises(SchemaViolation):
        parse_winner('{"winner": "tie"}', allow_tie=False)
    with pytest.raises(SchemaViolation):
        parse_winner('{"winner": "C"}', allow_tie=True)


# --- prompt rendering --------------------------------------------------------

def test_render_leaves_latex_braces_and_does_not_rescan():
    template = "Problem:\n{problem}\n\nSolution:\n{solution}"
    out = render(template, {"problem": r"\frac{4}{5} {solution}", "solution": "x"})
    assert out == "Problem:\n\\frac{4}{5} {solution}\n\nSolution:\nx"
