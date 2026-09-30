#!/usr/bin/env python3
"""Download GSM8K (openai/gsm8k, main) at the pinned revision into data/raw/gsm8k and verify sha256 and row counts;
report whether the mapping workbook is in place with the expected sha256. Nothing else is fetched: the four error
datasets are already in the repository (../data/full/pool.jsonl).

Usage (from newman_experiment/):  python scripts/fetch_sources.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman.common import load_config, rel, resolve, sha256_file  # noqa: E402
from newman.sources import load_gsm8k  # noqa: E402
from newman.taxonomy import Taxonomy, find_file  # noqa: E402


def main() -> int:
    cfg = load_config("configs/data.yaml")
    rows = load_gsm8k(cfg, fetch=True)
    counts = {s: sum(1 for r in rows if r["split"] == s) for s in ("train", "test")}
    print(f"GSM8K {cfg['gsm8k']['revision'][:12]}: {counts} rows, sha256 verified -> {rel(resolve(cfg['inputs']['gsm8k_dir']))}")
    tax = Taxonomy.load(resolve(cfg["inputs"]["taxonomy"]))
    configured = resolve(tax.mapping_source["workbook"])
    wb = find_file(configured)
    if wb is None:
        print(f"mapping workbook MISSING: upload it to {rel(configured)} (sha256 {tax.mapping_source['sha256']})")
        return 1
    digest = sha256_file(wb)
    ok = digest == tax.mapping_source["sha256"]
    print(f"mapping workbook {rel(wb)}: sha256 {'OK' if ok else 'MISMATCH ' + digest}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
