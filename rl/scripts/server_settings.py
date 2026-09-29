#!/usr/bin/env python3
"""Print shell `export` lines for the launch scripts, read from an RL config (single source of truth)."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tutee_rl.common import load_config  # noqa: E402


def main() -> int:
    cfg = load_config(sys.argv[1] if len(sys.argv) > 1 else "configs/common.yaml")
    ro, ve, ev = cfg["servers"]["rollout"], cfg["servers"]["verifier"], cfg["evaluation"]["server"]
    train_gpus = str(cfg["distributed"]["train_gpus"])
    ds = cfg["distributed"]["deepspeed"]
    values = {
        "POLICY_MODEL": cfg["policy"]["model"],
        "ROLLOUT_GPU": ro["gpu"], "ROLLOUT_PORT": ro["port"], "ROLLOUT_UTIL": ro["gpu_memory_utilization"],
        "ROLLOUT_MAXLEN": ro["max_model_len"],
        "VERIFIER_MODEL": cfg["verifier"]["checkpoint"], "VERIFIER_NAME": cfg["verifier"]["served_name"],
        "VERIFIER_GPU": ve["gpu"], "VERIFIER_PORT": ve["port"], "VERIFIER_UTIL": ve["gpu_memory_utilization"],
        "VERIFIER_MAXLEN": ve["max_model_len"],
        "EVAL_VERIFIER_MODEL": cfg["evaluation"]["verifier"]["checkpoint"],
        "EVAL_VERIFIER_NAME": cfg["evaluation"]["verifier"]["served_name"],
        "EVAL_VERIFIER_GPU": ev["gpu"], "EVAL_VERIFIER_PORT": ev["port"], "EVAL_VERIFIER_UTIL": ev["gpu_memory_utilization"],
        "EVAL_VERIFIER_MAXLEN": ev["max_model_len"],
        "TRAIN_GPUS": train_gpus, "NUM_TRAIN": len(train_gpus.split(",")),
        "DS_CONFIG": ds,
        "ACCEL_CONFIG": "configs/accelerate_zero3.yaml" if "zero3" in ds else "configs/accelerate_zero2_offload.yaml",
    }
    for key, value in values.items():
        print(f"export {key}={shlex.quote(str(value))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
