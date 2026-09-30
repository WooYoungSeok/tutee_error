"""Config, paths, IO and prompt rendering shared by every RL module.

Nothing here imports torch, so data preparation and the unit tests run without a GPU stack.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

RL_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = RL_ROOT.parent
VERIFIER_SFT_DIR = REPO_ROOT / "verifier_sft"

REQUIRED_MARKERS = ("REQUIRED", "REQUIRED_WHEN_ENABLED")
AUXILIARY_MODES = ("diversity", "student_likeness")


class ConfigError(RuntimeError):
    pass


# --- paths and IO ------------------------------------------------------------


def resolve(path: str | Path) -> Path:
    """Config paths are relative to rl/."""
    p = Path(path)
    return p if p.is_absolute() else (RL_ROOT / p).resolve()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def hash_obj(obj: Any) -> str:
    return sha256_text(stable_json(obj))


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def append_jsonl(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: str | Path, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def load_dotenv(path: str | Path | None = None, override: bool = True) -> list[str]:
    """Same convention as the repo's labeling runner: the project .env wins over the shell."""
    dotenv = Path(path) if path else REPO_ROOT / ".env"
    if not dotenv.exists():
        return []
    applied = []
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and (override or key not in os.environ):
            os.environ[key] = value
            applied.append(key)
    return applied


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
    chain = [str(path)]
    if parent:
        base = load_config(path.parent / parent)
        chain = base.pop("_config_chain") + chain
        base.pop("_config_sha256", None)
        raw = _deep_merge(base, raw)
    for item in overrides:
        key, _, value = item.partition("=")
        if not key or not _:
            raise ConfigError(f"override must look like a.b=value: {item!r}")
        node = raw
        parts = key.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = yaml.safe_load(value)
    raw["_config_chain"] = chain
    raw["_config_sha256"] = hash_obj({k: v for k, v in raw.items() if not k.startswith("_")})
    return raw


def is_required_marker(value: Any) -> bool:
    return isinstance(value, str) and value in REQUIRED_MARKERS


def validate_for_training(cfg: Mapping[str, Any]) -> list[str]:
    """Problems that must block a real run. Empty list = runnable."""
    problems: list[str] = []
    mode = cfg["rewards"]["auxiliary_reward"]
    if mode not in AUXILIARY_MODES:
        problems.append(f"rewards.auxiliary_reward must be one of {AUXILIARY_MODES} (a single mode), got {mode!r}")
    if is_required_marker(cfg["verifier"]["checkpoint"]) or not cfg["verifier"]["checkpoint"]:
        problems.append("verifier.checkpoint is not set")
    if cfg["rewards"]["format"].get("tag_reward"):
        problems.append("rewards.format.tag_reward must stay false (tag rewards were removed)")
    if cfg["answer_check"]["model"] != "gpt-5-nano":
        problems.append(f"answer_check.model is fixed to gpt-5-nano by the plan, got {cfg['answer_check']['model']!r}")
    if mode == "student_likeness":
        sl = cfg["student_likeness"]
        for key in ("backend", "model"):
            if is_required_marker(sl.get(key)) or not sl.get(key):
                problems.append(f"student_likeness.{key} is not set")
        if sl.get("backend") not in (None, "openai", "vllm") and not is_required_marker(sl.get("backend")):
            problems.append(f"student_likeness.backend must be openai or vllm, got {sl.get('backend')!r}")
        if sl.get("backend") == "vllm" and not sl.get("base_url"):
            problems.append("student_likeness.base_url is required for backend vllm")
        if not sl.get("examples_approved"):
            problems.append("student_likeness.examples_approved is false (MathEDU example 2 not approved yet)")
    return problems


# --- prompts -----------------------------------------------------------------


def read_template(path: str | Path) -> str:
    """Prompt files end with one newline on disk; the message text does not."""
    return resolve(path).read_text(encoding="utf-8").rstrip("\n")


def render(template: str, values: Mapping[str, Any]) -> str:
    """Single left-to-right substitution of `{name}` for the given names only.

    Inserted text is never re-scanned, and other braces (LaTeX, JSON examples) are left alone.
    """
    if not values:
        return template
    pattern = re.compile("|".join(re.escape("{" + k + "}") for k in values))
    missing = [k for k in values if "{" + k + "}" not in template]
    if missing:
        raise ConfigError(f"template is missing placeholder(s) {missing}")
    return pattern.sub(lambda m: str(values[m.group(0)[1:-1]]), template)


def student_messages(template: str, row: Mapping[str, Any]) -> list[dict[str, str]]:
    """The Student's chat input (training and evaluation): instruction + misconception as system, problem as user."""
    return [
        {"role": "system", "content": render(template, {"error_description": row["target_misconception_description"]})},
        {"role": "user", "content": row["problem"]},
    ]


def eval_verifier_cfg(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """The reward `verifier` settings with the held-out test verifier swapped in (same sampling and parsing)."""
    return {**cfg["verifier"], **cfg["evaluation"]["verifier"]}


def write_generation_config(model_dir: str | Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Put the Student sampling used in training/evaluation into a saved model's generation_config.json.

    Saved snapshots otherwise keep the base model's defaults (Qwen2.5: T 0.7, top_p 0.8, top_k 20, rep. 1.05).
    """
    path = Path(model_dir) / "generation_config.json"
    base = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    gen = cfg["generation"]
    out = {k: base[k] for k in ("bos_token_id", "eos_token_id", "pad_token_id", "transformers_version") if k in base}
    out.update({"do_sample": True, "temperature": float(gen["temperature"]), "top_p": float(gen["top_p"]),
                "top_k": int(gen["top_k"]), "repetition_penalty": float(gen["repetition_penalty"]),
                "max_new_tokens": int(gen["max_completion_tokens"])})
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out
