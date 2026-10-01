"""Approval hashes, metrics, run naming, and the confirmed settings in the committed configs."""

from __future__ import annotations

import re

import pytest

from newman import approvals, preflight
from newman.common import default_run_name, find_required, load_config, now_iso
from newman.metrics import group_counts, paired_bootstrap, rank_checkpoints, ratios, verifier_metrics


# --- approvals ------------------------------------------------------------------------------


def test_approval_is_bound_to_the_content(tmp_path, monkeypatch):
    path = tmp_path / "approvals.yaml"
    assert approvals.status("student_prompt", approvals.load_approvals(path))[0] == "pending"
    approvals.approve("student_prompt", "test", path=path)
    state = approvals.load_approvals(path)
    assert approvals.status("student_prompt", state)[0] == "approved"
    real = approvals.fingerprint
    monkeypatch.setattr(approvals, "fingerprint", lambda item: {"files": {"prompts/student.txt": "0" * 64}})
    assert approvals.status("student_prompt", state)[0] == "changed"
    monkeypatch.setattr(approvals, "fingerprint", real)


def test_committed_approvals_block_real_runs_until_the_user_confirms():
    approved = {"verifier_backbones", "taxonomy_definitions", "verifier_prompt", "student_prompt"}  # user 2026-09-30 / 10-01
    assert {i for i in approvals.ITEMS if approvals.status(i)[0] == "approved"} == approved
    assert preflight.verifier_training(load_config("configs/verifier_half_a.yaml")) == []   # SFT may start
    assert preflight.verifier_training(load_config("configs/verifier_half_b.yaml")) == []
    problems = preflight.student_run(load_config("configs/student_likeness.yaml"))
    assert any("verifier.checkpoint" in p for p in problems)
    assert any("answer_judge_prompt" in p for p in problems) and any("student_likeness_prompt" in p for p in problems)
    assert not any("student_prompt:" in p for p in problems)
    assert preflight.is_smoke("smoke_x") and not preflight.is_smoke("newman_diversity_seed42_20261001_000000")


# --- metrics --------------------------------------------------------------------------------


def pair(anchor, target, pred, kind=None, tid="eic.calculation_error"):
    return {"anchor_sample_id": anchor, "question_group_id": f"g{anchor}", "target": target, "prediction": pred,
            "negative_kind": kind, "target_error_id": tid, "anchor_error_id": "eic.calculation_error",
            "target_newman_stage": "process_skills", "dataset": "eic", "benchmark": "GSM8K", "unit_conversion_eligible": None}


def test_verifier_metrics_count_invalid_as_wrong():
    rows = [pair("a", "aligned", "aligned"), pair("a", "not_aligned", "aligned", "same_stage"),
            pair("b", "aligned", "invalid"), pair("b", "not_aligned", "not_aligned", "different_stage")]
    m = verifier_metrics(rows)
    assert m["accuracy"] == 0.5 and m["negative_false_acceptance"] == 0.5 and m["positive_recall"] == 0.5
    assert m["invalid_rate_positives"] == 0.5 and m["by_negative_kind"]["same_stage"]["accuracy"] == 0.0


def test_checkpoint_ranking_rule():
    res = {"epoch-1": {"macro_f1": 0.9, "negative_false_acceptance": 0.1, "test_loss": 0.3},
           "epoch-2": {"macro_f1": 0.9, "negative_false_acceptance": 0.05, "test_loss": 0.4},
           "epoch-3": {"macro_f1": 0.8, "negative_false_acceptance": 0.0, "test_loss": 0.1}}
    assert rank_checkpoints(res, ["macro_f1:max", "negative_false_acceptance:min", "test_loss:min"])[0] == "epoch-2"
    with pytest.raises(ValueError):
        rank_checkpoints(res, ["macro_f1"])


def rollout(g, cid, verdict, b, a=None, in_g=False):
    v = lambda labels: {"labels": labels} if labels else None  # noqa: E731
    return {"question_group_id": g, "condition_id": cid, "answer_check": {"verdict": verdict}, "total": 1.0 if in_g else 0.0,
            "truncated": False, "in_G": in_g, "verifier_b": v(b), "verifier_a": v(a)}


def test_student_counts_and_paired_bootstrap():
    rs = [rollout("g1", "c1", "incorrect", ["aligned", "aligned"], ["aligned", "not_aligned"], True),
          rollout("g1", "c1", "correct", None), rollout("g2", "c2", "incorrect", ["aligned", "invalid"], ["aligned", "aligned"]),
          rollout("g2", "c2", None, None)]
    counts = group_counts(rs, "b", "a")
    r = ratios({f: sum(c[f] for c in counts.values()) for f in counts["g1"]})
    assert r["joint_success"] == 0.25 and r["accept_given_wrong"] == 0.5 and r["disagreement_given_wrong"] == 1.0
    assert r["zero_success_condition_rate"] == 0.5 and r["verifier_invalid_sample_rate"] == 0.25
    boot = paired_bootstrap({"base": counts, "rl": counts}, 200, 42, reference="base")
    assert boot["diff_vs_reference"]["rl"]["joint_success"] == [0.0, 0.0]


# --- naming and confirmed settings ------------------------------------------------------------


def test_run_name_and_timestamps_are_asia_seoul():
    assert re.fullmatch(r"verifier_half_a_seed42_\d{8}_\d{6}", default_run_name("verifier_half_a", 42))
    assert now_iso().endswith("+09:00")


def test_confirmed_rl_settings():
    cfg = load_config("configs/diversity.yaml")
    t, g = cfg["training"], cfg["generation"]
    assert (t["learning_rate"], t["beta"], t["epsilon"], t["num_train_epochs"], t["loss_type"], t["scale_rewards"]) == (1e-6, 0.04, 0.2, 2, "dapo", "group")
    assert (g["num_generations"], g["temperature"], g["top_p"], g["top_k"], g["repetition_penalty"]) == (8, 1.0, 1.0, 0, 1.0)
    assert t["per_device_train_batch_size"] * 3 * t["gradient_accumulation_steps"] == t["expected_completions_per_step"] == 48
    assert (t["model_save_every_epochs"], t["resume_save_every_epochs"], t["resume_save_total_limit"]) == (0.5, 0.5, None)
    assert cfg["answer_check"]["reasoning_effort"] == cfg["student_likeness"]["reasoning_effort"] == "low"
    assert cfg["answer_check"]["model"] == cfg["student_likeness"]["model"] == "gpt-5-nano"
    v = cfg["verifier"]
    assert (v["samples"], v["temperature"], v["top_p"], v["repetition_penalty"], v["aggregation"]) == (2, 0.6, 1.0, 1.0, "all_aligned")
    r = cfg["rewards"]
    assert (r["lambda_correct_penalty"], r["null_verdict_main_reward"], r["auxiliary_weight"], r["format"]["truncation_penalty"]) == (0.75, -0.75, 0.5, 0.5)
    assert set(find_required(cfg)) == {"verifier.checkpoint", "evaluation.verifier.checkpoint"}
    ev = cfg["evaluation"]
    assert (ev["select_split"], ev["select_metric"], ev["split"]) == ("validation", "reward_total_mean", "test")
    assert cfg["api_baselines"]["models"] == ["gpt-5.6-sol"] and cfg["api_baselines"]["reasoning_effort"] is None
    assert cfg["api_baselines"]["max_output_tokens"] == 8000 and cfg["likeness_comparison"]["pairing"] == "rollout_index"


def test_confirmed_verifier_settings_and_independent_halves():
    a, b = load_config("configs/verifier_half_a.yaml"), load_config("configs/verifier_half_b.yaml")
    assert a["training"] == b["training"] and a["evaluation"] == b["evaluation"] and a["prompts"] == b["prompts"]
    assert (a["half"], a["role"], a["data_file"]) == ("A", "reward", "half_a.jsonl")
    assert (b["half"], b["role"], b["data_file"]) == ("B", "test", "half_b.jsonl")
    t = a["training"]
    assert (t["learning_rate"], t["num_train_epochs"], t["weight_decay"], t["warmup_ratio"]) == (1e-5, 5, 0.01, 0.1)
    assert t["per_device_train_batch_size"] * t["gradient_accumulation_steps"] == t["expected_effective_batch"] == 32
    assert a["max_seq_length"] == 4096
    assert a["evaluation"]["selection_rule"] == ["macro_f1:max", "negative_false_acceptance:min"]   # no test loss (user 2026-10-01)
    assert (a["model"]["name"], b["model"]["name"]) == ("Qwen/Qwen2.5-Math-7B-Instruct", "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B")


def test_data_decisions():
    cfg = load_config("configs/data.yaml")
    assert find_required(cfg) == []
    rd = cfg["rl_data"]
    assert (rd["gsm8k_source_splits"], rd["validation_ratio"], rd["type_assignment"], rd["conditions_per_question"]) == (
        ["train", "test"], 0.1, "balanced", 1)
    assert cfg["split"]["test_ratio"] == 0.2 and cfg["filters"]["description_status"] == "ok"
    assert cfg["filters"]["exclude_multi_label_solutions"] and len(cfg["filters"]["multi_label_extra_sources"]) == 4


def test_pair_accuracy_needs_every_row_of_the_anchor_with_two_negatives():
    from newman.metrics import basic_metrics

    rows = [pair("a", "aligned", "aligned"), pair("a", "not_aligned", "not_aligned", "same_stage"),
            pair("a", "not_aligned", "aligned", "different_stage"),
            pair("b", "aligned", "aligned"), pair("b", "not_aligned", "aligned", "same_stage"),
            pair("b", "not_aligned", "not_aligned", "different_stage")]
    m = basic_metrics(rows)
    assert m["pairs"] == 2 and m["pair_accuracy"] == 0.0     # each anchor has one wrong negative
