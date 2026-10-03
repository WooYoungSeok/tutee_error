#!/usr/bin/env python3
"""rl/scripts/train.py with the distractor reward (see src/distractor_rl/orchestrator.py). Same arguments."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _patch import run  # noqa: E402

run("train.py")
