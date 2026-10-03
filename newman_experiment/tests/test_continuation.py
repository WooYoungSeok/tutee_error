"""train_student.py --continue_from (prepared 2026-10-02): settings and data order, without torch or GPUs."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from newman.common import load_config

SPEC = importlib.util.spec_from_file_location("train_student", Path(__file__).resolve().parents[1] / "scripts" / "train_student.py")
ts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ts)


def snapshot(tmp, epoch=1.0, run="newman_student_likeness_seed42_20261002_154536"):
    d = tmp / run / "epoch_checkpoints" / f"epoch-{epoch:.2f}"
    d.mkdir(parents=True)
    (d / "config.json").write_text("{}", encoding="utf-8")
    (d / "epoch_meta.json").write_text(json.dumps({"epoch": epoch, "global_step": 1056}), encoding="utf-8")
    return d


def test_no_continuation_keeps_the_first_stage_unchanged():
    cfg = load_config("configs/student_likeness.yaml")
    assert ts.continuation_plan(cfg, None) is None
    rows = [{"condition_id": str(i)} for i in range(50)]
    assert ts.permute_for_stage(rows, None) is rows


def test_continuation_plan_from_a_one_epoch_snapshot(tmp_path):
    cfg = load_config("configs/student_likeness.yaml")
    plan = ts.continuation_plan(cfg, str(snapshot(tmp_path)))
    assert plan["stage"] == 2 and plan["epoch_offset"] == 1.0 and plan["warmup_ratio"] == 0.0
    assert plan["reference_model"] == cfg["policy"]["model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert plan["from_run"] == "newman_student_likeness_seed42_20261002_154536"


def test_stage_data_order_is_new_deterministic_and_complete(tmp_path):
    cfg = load_config("configs/student_likeness.yaml")
    plan = ts.continuation_plan(cfg, str(snapshot(tmp_path)))
    rows = [{"condition_id": str(i)} for i in range(200)]
    once, twice = ts.permute_for_stage(rows, plan), ts.permute_for_stage(rows, plan)
    assert once == twice and once != rows and sorted(r["condition_id"] for r in once) == sorted(r["condition_id"] for r in rows)


def test_continuation_needs_a_model_snapshot(tmp_path):
    cfg = load_config("configs/student_likeness.yaml")
    with pytest.raises(SystemExit):
        ts.continuation_plan(cfg, str(tmp_path))
