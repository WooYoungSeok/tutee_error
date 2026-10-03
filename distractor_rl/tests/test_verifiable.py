"""Verifiable distractor reward without a verifier (user decisions 2026-10-03). No GPU/network."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE / "src"), str(HERE.parent / "rl" / "src")]

from distractor_rl.clients import parse_extraction  # noqa: E402
from distractor_rl.orchestrator_verifiable import VerifiableDistractorOrchestrator  # noqa: E402
from tutee_rl.clients import RewardExecutionError, SchemaViolation  # noqa: E402
from tutee_rl.common import load_config, validate_for_training  # noqa: E402

CONFIG = HERE / "configs" / "verifiable.yaml"


def test_config_holds_the_decided_values():
    cfg = load_config(CONFIG)
    rw = cfg["rewards"]
    assert rw["variant"] == "verifiable" and (rw["distractor_match_reward"], rw["non_target_reward"]) == (1.0, -0.75)
    assert rw["auxiliary_terms"] == {"student_likeness": 0.5, "diversity": 0.25}
    assert cfg["generation"]["num_generations"] == 8 and cfg["openai_client"]["hedge_after_s"] == 10  # user 2026-10-03
    assert cfg["answer_check"]["reasoning_effort"] == cfg["student_likeness"]["reasoning_effort"] == "low"
    assert validate_for_training(cfg) == []


def test_extraction_parsing():
    assert parse_extraction(json.dumps({"extracted_answer": "3/4", "reason": "r"}))["extracted_answer"] == "3/4"
    assert parse_extraction(json.dumps({"extracted_answer": None, "reason": "r"}))["extracted_answer"] is None
    for bad in ({"extracted_answer": "null", "reason": "r"}, {"extracted_answer": "3", "verdict": "correct", "reason": "r"}):
        with pytest.raises(SchemaViolation):
            parse_extraction(json.dumps(bad))


class FakeTokenizer:
    eos_token_id = 7


def make(tmp_path):
    cfg = load_config(CONFIG, ["smoke.mock_reward_clients=true", "policy.model=/nonexistent"])
    return VerifiableDistractorOrchestrator(cfg, FakeTokenizer(), tmp_path / "run", is_main=True), cfg


def block(orch, pid):
    return [{"rank": 0, "local_idx": i, "pair_id": pid, "ids": [10 + i, 7], "text": f"solution {i} {pid}"} for i in range(8)]


def test_rewards_guard_and_aux(tmp_path):
    orch, cfg = make(tmp_path)
    pid = next(iter(orch.rows))
    priv = orch.privileged[pid]
    texts = {}

    async def extract(problem, contract, solution):  # answers: correct, the first target, something else, null
        i = int(solution.split()[1])
        ans = [priv["CorrectAnswerText"], priv["TargetDistractors"][0]["text"], "zzz-other", None][i % 4]
        texts[i] = ans
        return {"extracted_answer": ans, "reason": "t", "attempts": 1, "latency_s": 0.0, "cached": False}

    called = []

    async def match(problem, contract, ans, targets):
        called.append(ans)
        return {"matched_option": None, "reason": "t", "attempts": 1, "cached": False}

    orch.extractor.extract, orch.matcher.match = extract, match
    rows, glog = orch._run(orch._score_group(block(orch, pid), 0))
    cases = [r["reward_case"] for r in rows]
    assert cases[:4] == ["literal_correct", "distractor", "no_match", "null"]
    assert [r["main"] for r in rows[:4]] == [-0.75, 1.0, -0.75, -0.75]
    assert called == ["zzz-other"] * 2                       # the matcher only sees answers the literal guard cannot settle
    g = [i for i, r in enumerate(rows) if r["in_G"]]
    assert g == [1, 5] and glog["K"] == 2
    for r in rows:
        assert r["total"] == pytest.approx(r["main"] + 0.5 * r["aux_l"] + 0.25 * r["aux_d"] + r["trunc"])
        assert (r["aux_l"] == 0 and r["aux_d"] == 0) or r["in_G"]
    funcs, weights = orch.reward_funcs()
    assert weights == [1.0, 0.5, 0.25, 1.0] and [f.__name__ for f in funcs][1:3] == ["aux_student_likeness", "aux_diversity"]
    m = orch._metrics(rows, [glog], 0.0)
    assert m["distractor/match_rate"] == pytest.approx(2 / 8) and m["answer/literal_correct_rate"] == pytest.approx(2 / 8)


class _Flagged(Exception):
    code = "invalid_prompt"


def test_refused_extraction_is_no_answer(tmp_path):
    orch, _ = make(tmp_path)
    pid = next(iter(orch.rows))

    async def refused(*a, **k):
        raise RewardExecutionError("answer extraction fatal error BadRequestError") from _Flagged("flagged")

    orch.extractor.extract = refused
    rows, _ = orch._run(orch._score_group(block(orch, pid), 0))
    assert all(r["main"] == -0.75 and r["reward_case"] == "null" and r["answer_extraction"]["flagged"] for r in rows)


def test_hedged_request_takes_the_first_answer(tmp_path):
    import asyncio
    import time

    orch, _ = make(tmp_path)
    orch.cfg["openai_client"]["hedge_after_s"] = 0.2
    calls = []

    async def slow_then_fast():
        calls.append(time.monotonic())
        await asyncio.sleep(3.0 if len(calls) == 1 else 0.05)
        return {"n": len(calls)}

    started = time.monotonic()
    out = orch._run(orch._hedged(slow_then_fast))
    assert out == {"n": 2} and len(calls) == 2 and time.monotonic() - started < 1.0 and orch.hedged_calls == 1

    async def fast():
        return {"ok": True}

    assert orch._run(orch._hedged(fast)) == {"ok": True} and orch.hedged_calls == 1   # no second request when it answers in time

    async def fails():
        await asyncio.sleep(0.3)
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        orch._run(orch._hedged(fails))
