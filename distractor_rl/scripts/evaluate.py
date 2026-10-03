#!/usr/bin/env python3
"""rl/scripts/evaluate.py with the distractor reward (test scoring = training reward with the half-B verifier)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _patch import run  # noqa: E402

run("evaluate.py")
