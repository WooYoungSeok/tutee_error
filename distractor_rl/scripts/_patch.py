"""Run an rl/scripts/*.py entry point with the distractor reward orchestrator in place of the Eedi one.

rl/ stays unchanged (repo rule): its train.py / evaluate.py import tutee_rl.orchestrator.RewardOrchestrator inside
main(), so replacing that module attribute before running the script is enough.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RL = HERE.parent / "rl"
for p in (HERE / "src", RL / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def run(script: str) -> None:
    import tutee_rl.orchestrator as eedi

    from distractor_rl.orchestrator import DistractorRewardOrchestrator
    from distractor_rl.orchestrator_verifiable import VerifiableDistractorOrchestrator

    def make(cfg, *args, **kwargs):  # rewards.variant picks the reward (default: the 2026-10-02 distractor + verifier run)
        cls = VerifiableDistractorOrchestrator if cfg["rewards"].get("variant") == "verifiable" else DistractorRewardOrchestrator
        return cls(cfg, *args, **kwargs)

    eedi.RewardOrchestrator = make
    sys.argv[0] = str(RL / "scripts" / script)
    runpy.run_path(str(RL / "scripts" / script), run_name="__main__")
