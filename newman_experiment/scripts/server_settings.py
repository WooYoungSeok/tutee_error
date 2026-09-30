#!/usr/bin/env python3
"""Print shell `export` lines for the launch scripts from an RL config (single source of truth)."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman.common import REQUIRED, load_config  # noqa: E402


def main() -> int:
    cfg = load_config(sys.argv[1] if len(sys.argv) > 1 else "configs/rl_common.yaml")
    ro, ve = cfg["servers"]["rollout"], cfg["servers"]["verifier"]
    ev, ea = cfg["evaluation"]["server"], cfg["evaluation"]["reward_verifier_server"]
    train_gpus = str(cfg["distributed"]["train_gpus"])
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
        "EVAL_WITH_REWARD_VERIFIER": int(bool(cfg["evaluation"]["with_reward_verifier"])),
        "EVAL_REWARD_GPU": ea["gpu"], "EVAL_REWARD_PORT": ea["port"], "EVAL_REWARD_UTIL": ea["gpu_memory_utilization"],
        "EVAL_REWARD_MAXLEN": ea["max_model_len"],
        "TRAIN_GPUS": train_gpus, "NUM_TRAIN": len(train_gpus.split(",")),
        "ACCEL_CONFIG": cfg["distributed"]["accelerate_config"],
        "MOCK_REWARDS": int(bool(cfg.get("smoke", {}).get("mock_reward_clients"))),
    }
    for key, value in values.items():
        print(f"export {key}={shlex.quote(str(value))}")
    if REQUIRED in (values["VERIFIER_MODEL"], values["EVAL_VERIFIER_MODEL"]):
        print("# note: a verifier checkpoint is still REQUIRED in the config", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
