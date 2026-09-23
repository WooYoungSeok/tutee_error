"""Canonical project paths."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROMPTS_DIR = PROJECT_ROOT / "prompts"
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
NORMALIZED_DIR = DATA_DIR / "normalized"
MANIFEST_DIR = DATA_DIR / "manifest"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
REPORTS_DIR = PROJECT_ROOT / "reports"

SOURCE_MANIFEST = RAW_DIR / "source_manifest.json"
SAMPLE_MANIFEST = MANIFEST_DIR / "sample_manifest.jsonl"
SAMPLE_MANIFEST_META = MANIFEST_DIR / "sample_manifest_meta.json"

# full labeling run (every eligible record, not the fixed 200-case sample)
FULL_DIR = DATA_DIR / "full"
FULL_POOL = FULL_DIR / "pool.jsonl"
FULL_RECORD_INDEX = FULL_DIR / "record_index.jsonl"
FULL_POOL_META = FULL_DIR / "pool_meta.json"
LABELED_DIR = DATA_DIR / "labeled"


def ensure_dirs() -> None:
    for path in (
        RAW_DIR,
        NORMALIZED_DIR,
        MANIFEST_DIR,
        OUTPUTS_DIR,
        REPORTS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
