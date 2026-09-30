"""Paths, config, run naming, environment records and storage checks shared by every Newman module.

Nothing here imports torch, so data preparation and the unit tests run without a GPU stack.
Generic IO, hashing and prompt rendering come from the RL package (rl/src/tutee_rl/common.py) so both
experiments write files and render templates identically; paths here are relative to newman_experiment/.
"""

from __future__ import annotations

import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

NEWMAN_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = NEWMAN_ROOT.parent
RL_ROOT = REPO_ROOT / "rl"
VERIFIER_SFT_DIR = REPO_ROOT / "verifier_sft"

if str(RL_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(RL_ROOT / "src"))

from tutee_rl.common import (  # noqa: E402  (re-exported: one serialisation for both experiments)
    append_jsonl,
    hash_obj,
    load_dotenv,
    read_jsonl,
    render,
    sha256_bytes,
    sha256_file,
    sha256_text,
    stable_json,
    write_json,
    write_jsonl,
)

__all__ = [
    "NEWMAN_ROOT", "REPO_ROOT", "RL_ROOT", "VERIFIER_SFT_DIR", "REQUIRED", "SMOKE_PREFIX", "TIMEZONE",
    "ConfigError", "append_jsonl", "default_run_name", "disk_problem", "find_required", "free_gb", "git_state",
    "hash_obj", "import_verifier_sft", "load_config", "load_dotenv", "now_iso", "read_json", "read_jsonl",
    "read_template", "render", "resolve", "run_stamp", "sha256_bytes", "sha256_file", "sha256_text",
    "stable_json", "versions", "write_json", "write_jsonl",
]

REQUIRED = "REQUIRED"          # an open research decision: real runs refuse to start while any is left
SMOKE_PREFIX = "smoke_"        # infrastructure runs (mock rewards, unapproved drafts) must carry this prefix
TIMEZONE = "Asia/Seoul"        # run names and metadata timestamps (user rule 3)


class ConfigError(RuntimeError):
    pass


# --- paths -------------------------------------------------------------------


def resolve(path: str | Path) -> Path:
    """Config paths are relative to newman_experiment/."""
    p = Path(path)
    return p if p.is_absolute() else (NEWMAN_ROOT / p).resolve()


def rel(path: str | Path) -> str:
    """Repository-relative path for metadata (stable across servers)."""
    p = Path(path).resolve()
    try:
        return p.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(p)


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_template(path: str | Path) -> str:
    """Prompt files end with one newline on disk; the message text does not."""
    return resolve(path).read_text(encoding="utf-8").rstrip("\n")


def import_verifier_sft(module: str = "verifier_common"):
    """The descriptive-verifier modules (tokenization, strict parsing, metrics, v2 quality filters) are reused as is."""
    if str(VERIFIER_SFT_DIR) not in sys.path:
        sys.path.insert(0, str(VERIFIER_SFT_DIR))
    return importlib.import_module(module)


# --- config ------------------------------------------------------------------


def _deep_merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path: str | Path, overrides: Iterable[str] = ()) -> dict[str, Any]:
    """YAML with an optional `inherits:` parent (relative to the file). `overrides` are `a.b.c=value` strings."""
    import yaml

    path = resolve(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    parent = raw.pop("inherits", None)
    chain = [rel(path)]
    if parent:
        base = load_config(path.parent / parent)
        chain = base.pop("_config_chain") + chain
        base.pop("_config_sha256", None)
        raw = _deep_merge(base, raw)
    for item in overrides:
        key, sep, value = item.partition("=")
        if not key or not sep:
            raise ConfigError(f"override must look like a.b=value: {item!r}")
        node = raw
        parts = key.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = yaml.safe_load(value)
    raw["_config_chain"] = chain
    raw["_config_sha256"] = hash_obj({k: v for k, v in raw.items() if not k.startswith("_")})
    return raw


def public_config(cfg: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in cfg.items() if not k.startswith("_")}


def find_required(obj: Any, prefix: str = "") -> list[str]:
    """Dotted keys whose value is still the REQUIRED marker."""
    if isinstance(obj, Mapping):
        out: list[str] = []
        for key, value in obj.items():
            if str(key).startswith("_"):
                continue
            out += find_required(value, f"{prefix}.{key}" if prefix else str(key))
        return out
    if isinstance(obj, list):
        return [k for i, v in enumerate(obj) for k in find_required(v, f"{prefix}[{i}]")]
    return [prefix] if obj == REQUIRED else []


def get_path(cfg: Mapping[str, Any], dotted: str) -> Any:
    node: Any = cfg
    for part in dotted.split("."):
        node = node[part]
    return node


# --- run naming (user rule 3: output folder = W&B run name) --------------------


def _tz():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(TIMEZONE)
    except Exception:  # noqa: BLE001 - no tz database: Korea has had no DST since 1988
        return timezone(timedelta(hours=9), "KST")


def now_iso() -> str:
    return datetime.now(_tz()).isoformat(timespec="seconds")


def run_stamp() -> str:
    return datetime.now(_tz()).strftime("%Y%m%d_%H%M%S")


def default_run_name(experiment: str, seed: int) -> str:
    """<experiment>_seed<seed>_<YYYYmmdd_HHMMSS> in Asia/Seoul."""
    return f"{experiment}_seed{seed}_{run_stamp()}"


# --- environment records ------------------------------------------------------


def versions(packages: Iterable[str] = ("torch", "transformers", "trl", "vllm", "deepspeed", "accelerate", "datasets",
                                        "openai", "sacrebleu", "numpy", "pandas", "pyarrow", "openpyxl", "pyyaml")) -> dict[str, str]:
    import importlib.metadata as md

    out = {"python": platform.python_version()}
    for pkg in packages:
        try:
            out[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            out[pkg] = "missing"
    return out


def git_state() -> dict[str, Any]:
    """Commit and whether tracked files differ from it (a dirty run is still recorded, never refused)."""
    def run(*args: str) -> str | None:
        try:
            return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=20, check=True).stdout.strip()
        except Exception:  # noqa: BLE001 - not a checkout / no git
            return None

    status = run("status", "--porcelain", "--untracked-files=no")
    return {"commit": run("rev-parse", "HEAD"), "branch": run("branch", "--show-current"),
            "tracked_changes": None if status is None else bool(status)}


# --- storage (all checkpoints are kept: user rule 5) --------------------------


def free_gb(path: str | Path) -> float:
    p = Path(path)
    while not p.exists():
        p = p.parent
    return shutil.disk_usage(p).free / 1e9


def disk_problem(path: str | Path, need_gb: float, margin_gb: float) -> str | None:
    """Nothing is rotated or deleted automatically, so a run that cannot fit must not start."""
    have = free_gb(path)
    if need_gb + margin_gb > have:
        return (f"projected checkpoint storage {need_gb:.0f} GB + margin {margin_gb:.0f} GB exceeds free space "
                f"{have:.0f} GB at {path}. Checkpoints are never deleted automatically (user rule 5): free space, "
                f"move output_root, or agree a different retention policy with the user")
    return None


def dir_size_gb(path: str | Path) -> float:
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total / 1e9
