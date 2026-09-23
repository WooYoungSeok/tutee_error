"""Pilot configuration loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .paths import CONFIG_DIR, PROJECT_ROOT
from .util import read_json

DEFAULT_CONFIG_PATH = CONFIG_DIR / "pilot.json"

DEFAULTS: dict[str, Any] = {
    "seed": 42,
    "datasets": ["mathedu", "stepwise", "mathclean", "eic"],
    "per_dataset_target": 50,
    "dev_per_dataset": 10,
    "prompt_file": "prompts/error_description_v1.txt",
    "prompt_version": "v1",
    "model": None,
    "generation": {
        "concurrency": 2,
        "max_output_tokens": 1200,
        "temperature": None,
        "reasoning_effort": None,
        "response_format_json": False,
        "request_timeout_s": 180,
        "max_retries": 4,
    },
    "mathedu": {"field_map": {}},
}


def _merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: Path | str | None = None) -> dict:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    user = read_json(config_path) if config_path.exists() else {}
    config = _merge(DEFAULTS, user)
    config["_config_path"] = str(config_path)
    return config


def prompt_path(config: dict) -> Path:
    return PROJECT_ROOT / config["prompt_file"]
