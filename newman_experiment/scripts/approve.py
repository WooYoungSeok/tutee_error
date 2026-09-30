#!/usr/bin/env python3
"""Record the user's approval of a draft item (user rule 1), or show the state of every item.

Run only after the user has confirmed the content in the conversation. The approval stores the sha256 of the exact
files (or the exact config values); a later edit re-opens the item and real runs refuse to start until it is
approved again. Commit configs/approvals.yaml with the change it approves.

Usage (from newman_experiment/):
  python scripts/approve.py --status
  python scripts/approve.py student_prompt --note "user approved the plan 7 draft as is (2026-10-01)"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman import approvals  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("item", nargs="?", choices=sorted(approvals.ITEMS))
    p.add_argument("--note", default="")
    p.add_argument("--status", action="store_true")
    args = p.parse_args()
    if args.status or not args.item:
        state = approvals.load_approvals()
        for item, spec in approvals.ITEMS.items():
            st, detail = approvals.status(item, state)
            print(f"{st:9s} {item:24s} {detail}")
            for f in spec.get("files", []):
                print(f"{'':34s}{f}")
        return 0
    if not args.note.strip():
        print("--note is required: who confirmed what, and when", file=sys.stderr)
        return 2
    rec = approvals.approve(args.item, args.note)
    print(f"approved {args.item}: {rec}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
