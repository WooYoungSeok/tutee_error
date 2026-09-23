#!/usr/bin/env python3
"""List the model ids this API key can see (read-only; no generation is billed).

Pricing is not exposed by this endpoint: check the official pricing page before
choosing a model, and pass the price you confirmed to the dry run.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from errdesc.paths import PROJECT_ROOT  # noqa: E402
from errdesc.runner import load_dotenv  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--filter", default=None, help="substring filter on the model id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set.")
    from openai import OpenAI

    client = OpenAI()
    ids = sorted(model.id for model in client.models.list())
    if args.filter:
        ids = [model_id for model_id in ids if args.filter in model_id]
    for model_id in ids:
        print(model_id)
    print(f"\n{len(ids)} model(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
