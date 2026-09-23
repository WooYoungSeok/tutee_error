#!/usr/bin/env python3
"""Build the full labeling pool: every eligible record, deduplicated by sample id.

Unlike build_samples.py this does not sample and never touches the fixed
200-case manifest. Datasets and EIC benchmarks come from the config
(default config/full.json).

Outputs
-------
data/full/pool.jsonl           one row per unique request (split = "full")
data/full/record_index.jsonl   every normalized record -> sample id / exclusion reason
data/full/pool_meta.json       counts, exclusions, labels, source revisions
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from errdesc.adapters import eic_root, normalize_dataset  # noqa: E402
from errdesc.config import load_config  # noqa: E402
from errdesc.fullpool import build_pool, index_row  # noqa: E402
from errdesc.paths import (  # noqa: E402
    CONFIG_DIR,
    FULL_POOL,
    FULL_POOL_META,
    FULL_RECORD_INDEX,
    SAMPLE_MANIFEST,
    ensure_dirs,
)
from errdesc.sources import load_source_manifest  # noqa: E402
from errdesc.util import read_jsonl, utc_now, write_json, write_jsonl  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(CONFIG_DIR / "full.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    ensure_dirs()
    source_manifest = load_source_manifest()

    for benchmark in config.get("eic", {}).get("benchmarks") or []:
        if not eic_root(benchmark).exists():
            raise SystemExit(
                f"EIC {benchmark} files are missing: {eic_root(benchmark)}\n"
                "Run scripts/fetch_sources.py --datasets eic"
            )

    pool: list[dict] = []
    index: list[dict] = []
    per_dataset: dict[str, dict] = {}
    for dataset in config["datasets"]:
        revision = source_manifest.get("datasets", {}).get(dataset, {}).get("revision", "")
        records = normalize_dataset(dataset, revision=revision, config=config.get(dataset, {}))
        rows, stats = build_pool(records)
        if dataset == "eic":
            stats["by_benchmark"] = dict(
                sorted(Counter(r["annotations"].get("source_benchmark") for r in rows).items())
            )
        pool.extend(rows)
        index.extend(index_row(r) for r in records)
        per_dataset[dataset] = stats
        print(
            f"[{dataset}] records={stats['records_read']} eligible={stats['eligible_records']} "
            f"unique requests={stats['unique_requests']}",
            flush=True,
        )

    write_jsonl(FULL_POOL, pool)
    write_jsonl(FULL_RECORD_INDEX, index)

    pool_ids = {r["sample_id"] for r in pool}
    manifest_ids = {r["sample_id"] for r in read_jsonl(SAMPLE_MANIFEST)} if SAMPLE_MANIFEST.exists() else set()
    meta = {
        "created_at_utc": utc_now(),
        "config_path": config["_config_path"],
        "datasets": config["datasets"],
        "eic_benchmarks": config.get("eic", {}).get("benchmarks"),
        "unique_requests": len(pool),
        "records_indexed": len(index),
        "per_dataset": per_dataset,
        "fixed_sample_cases_in_pool": len(manifest_ids & pool_ids),
        "fixed_sample_cases_missing_from_pool": sorted(manifest_ids - pool_ids),
        "source_revisions": {
            ds: source_manifest.get("datasets", {}).get(ds, {}).get("revision", "")
            for ds in config["datasets"]
        },
    }
    write_json(FULL_POOL_META, meta)

    print(f"unique requests : {len(pool)}")
    print(f"fixed sample    : {meta['fixed_sample_cases_in_pool']}/{len(manifest_ids)} cases in the pool")
    print(f"pool            -> {FULL_POOL}")
    print(f"record index    -> {FULL_RECORD_INDEX}")
    print(f"meta            -> {FULL_POOL_META}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
