#!/usr/bin/env python3
"""Download the pilot source datasets and record their provenance."""

from __future__ import annotations

import argparse
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from errdesc.paths import SOURCE_MANIFEST, ensure_dirs  # noqa: E402
from errdesc.sources import (  # noqa: E402
    SOURCES,
    fetch_dataset,
    load_source_manifest,
    save_source_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--datasets",
        nargs="*",
        default=sorted(SOURCES),
        choices=sorted(SOURCES),
        help="datasets to fetch (default: all)",
    )
    parser.add_argument("--force", action="store_true", help="re-download cached files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    manifest = load_source_manifest()
    failures = []
    for dataset in args.datasets:
        print(f"[{dataset}] fetching ...", flush=True)
        try:
            entry = fetch_dataset(dataset, force=args.force)
        except (urllib.error.URLError, RuntimeError, OSError, KeyError) as exc:
            entry = {
                "dataset": dataset,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }
            failures.append(dataset)
        manifest["datasets"][dataset] = entry
        total = sum(f.get("bytes", 0) for f in entry.get("files", []))
        print(
            f"[{dataset}] status={entry.get('status')} "
            f"revision={entry.get('revision', '-')} "
            f"files={len(entry.get('files', []))} bytes={total}",
            flush=True,
        )
        if entry.get("error"):
            print(f"[{dataset}] {entry['error']}", flush=True)
    save_source_manifest(manifest)
    print(f"source manifest -> {SOURCE_MANIFEST}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
