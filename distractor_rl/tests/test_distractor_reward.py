"""Distractor reward (user decisions 2026-10-02): config, match parsing, literal guard, reward cases, OpenAI refusals,
group scoring with mock clients. No GPU/network."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE / "src"), str(HERE.parent / "rl" / "src")]

from distractor_rl.clients import format_options, parse_match  # noqa: E402
from distractor_rl.orchestrator import DistractorRewardOrchestrator, guard_correct, literal_target, main_reward  # noqa: E402
from tutee_rl.clients import RewardExecutionError, SchemaViolation  # noqa: E402
from tutee_rl.common import load_config, read_jsonl  # noqa: E402

CONFIG = HERE / "configs" / "student_likeness.yaml"
CFG = load_config(CONFIG)
RW = CFG["rewards"]
PRIV = {"CorrectAnswerText": r"\( 150 \mathrm{~m} \)", "TargetDistractors": [{"option": "C", "text": r"\( 1.5 \mathrm{~m} \)"}]}


def test_config_holds_the_decided_values():
    assert (RW["distractor_match_reward"], RW["verifier_pass_reward"], RW["lambda_correct_penalty"], RW["null_verdict_main_reward"]) == (1.0, 0.5, 0.75, -0.75)
    assert RW["auxiliary_reward"] == "student_likeness" and RW["auxiliary_weight"] == 0.5
    p = CFG["prompts"]
    assert (p["student"], p["answer_judge_system"], p["answer_judge_user"]) == (
        "prompts/student.txt", "prompts/answer_judge_system.txt", "prompts/answer_judge_user.txt")  # Eedi texts, unchanged
    assert CFG["answer_check"]["reasoning_effort"] == CFG["student_likeness"]["reasoning_effort"] == "low"
    assert CFG["openai_client"]["flagged_attempts"] == 3
    t = CFG["training"]
    assert (t["num_train_epochs"], t["per_device_train_batch_size"] * 3 * t["gradient_accumulation_steps"]) == (2, 48)


def test_match_parsing():
    assert parse_match(json.dumps({"matched_option": "a", "reason": "r"}), ["A", "D"])["matched_option"] == "A"
    assert parse_match(json.dumps({"matched_option": None, "reason": "r"}), ["A"])["matched_option"] is None
    other = parse_match(json.dumps({"matched_option": "B", "reason": "r"}), ["A", "D"])  # dropped, not retried
    assert other["matched_option"] is None and other["matched_option_dropped"]
    with pytest.raises(SchemaViolation):
        parse_match(json.dumps({"matched_option": "A"}), ["A"])


def test_literal_guard():
    smoke_case = guard_correct({"extracted_answer": "150 m", "verdict": "incorrect"}, PRIV)   # judge error seen in the smoke run
    assert (smoke_case["verdict"], smoke_case["judge_verdict"], smoke_case["guard"]) == ("correct", "incorrect", "literal correct answer")
    assert guard_correct({"extracted_answer": "150 metres", "verdict": "incorrect"}, PRIV)["guard"] is None  # judge's call
    assert literal_target("1.5 m", PRIV) == "C" and literal_target("1.50 m", PRIV) is None and literal_target(None, PRIV) is None


def test_main_reward_cases():
    aligned, rejected = ["aligned", "aligned"], ["aligned", "not_aligned"]
    assert main_reward("correct", None, None, RW) == (-0.75, "correct")
    assert main_reward(None, None, None, RW) == (-0.75, "null")
    assert main_reward("incorrect", "B", rejected, RW) == (1.0, "distractor")   # no verifier needed
    assert main_reward("incorrect", None, aligned, RW) == (0.5, "verifier_pass")
    assert main_reward("incorrect", None, rejected, RW) == (0.0, "incorrect_rejected")


def test_options_text():
    assert format_options([{"option": "D", "text": "None of these"}, {"option": "A", "text": r"\( \frac{62}{10} \)"}]) == \
        "A: \\( \\frac{62}{10} \\)\nD: None of these"


class FakeTokenizer:
    eos_token_id = 7


def orchestrator(tmp_path):
    cfg = load_config(CONFIG, ["smoke.mock_reward_clients=true", "policy.model=/nonexistent"])
    return DistractorRewardOrchestrator(cfg, FakeTokenizer(), tmp_path / "run", is_main=True), cfg


def block_for(orch, pid=None):
    pid = pid or next(iter(orch.rows))
    return pid, [{"rank": 0, "local_idx": i, "pair_id": pid, "ids": [10 + i, 7], "text": f"solution {i} {pid}"} for i in range(8)]


def test_group_scoring_with_mock_clients(tmp_path):
    orch, cfg = orchestrator(tmp_path)
    _, block = block_for(orch)
    rows, glog = orch._run(orch._score_group(block, 0))
    for r in rows:
        assert r["main"] == main_reward(r["answer_check"]["verdict"], r["matched_option"], r["verifier"]["labels"] if r["verifier"] else None, cfg["rewards"])[0]
        assert r["in_G"] == (r["main"] > 0)
        assert (r["distractor_check"] is not None) == (r["answer_check"]["verdict"] == "incorrect")  # second call only for incorrect
        assert r["total"] == pytest.approx(r["main"] + 0.5 * r["aux"] + r["trunc"])
    assert glog["K"] == sum(r["in_G"] for r in rows)
    m = orch._metrics(rows, [glog], 0.0)
    assert {"distractor/match_rate", "reward_case/distractor_rate", "openai/flagged_answer_checks", "guard/correct_override_rate"} <= set(m)


class _Flagged(Exception):
    code = "invalid_prompt"


def test_openai_refusal_does_not_stop_training(tmp_path):
    orch, _ = orchestrator(tmp_path)
    _, block = block_for(orch)
    calls = {"n": 0}

    async def refused(*a, **k):
        calls["n"] += 1
        raise RewardExecutionError("answer check fatal error BadRequestError") from _Flagged("flagged")

    orch.answer.check = refused
    rows, _ = orch._run(orch._score_group(block, 0))
    assert calls["n"] == 8 * 3 and all(r["main"] == -0.75 and r["answer_check"]["flagged"] for r in rows)
    assert len(read_jsonl(tmp_path / "run" / "rollouts" / "flagged.jsonl")) == 8

    async def other_error(*a, **k):
        raise RewardExecutionError("answer check fatal error BadRequestError") from ValueError("unknown model")

    orch.answer.check = other_error
    with pytest.raises(RewardExecutionError):  # any other 400 still stops the run
        orch._run(orch._score_group(block, 0))
