#!/usr/bin/env python3
"""Write the Student sampling used in training/evaluation into saved models' generation_config.json.

Saved snapshots otherwise keep the base model's defaults (Qwen2.5: T 0.7, top_p 0.8, top_k 20, repetition
penalty 1.05), so plain `generate()` / vLLM defaults would not sample like the RL runs.

Usage (from rl/):  python scripts/set_generation_config.py [--config configs/common.yaml] MODEL_DIR [MODEL_DIR ...]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tutee_rl.common import load_config, write_generation_config  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="configs/common.yaml")
    parser.add_argument("model_dirs", nargs="+")
    args = parser.parse_args()
    cfg = load_config(args.config)
    for d in args.model_dirs:
        print(d, write_generation_config(Path(d), cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
