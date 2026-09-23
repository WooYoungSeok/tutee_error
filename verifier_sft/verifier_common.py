"""Shared pieces of the descriptive verifier experiment.

Config and IO, the fixed prompt, tokenization with loss masking, strict output
parsing and the evaluation metrics. Nothing here imports torch, so data
preparation, tests and metric code run without a GPU stack.

Training and inference build their chat messages only through
`build_messages`, so both use one template.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "config" / "descriptive_verifier_v1.json"

ALIGNED = "aligned"
NOT_ALIGNED = "not_aligned"
LABELS = (ALIGNED, NOT_ALIGNED)
INVALID = "invalid"
IGNORE_INDEX = -100

PLACEHOLDERS = ("question", "solution", "error_description")
_PLACEHOLDER_RE = re.compile("|".join(re.escape("{" + p + "}") for p in PLACEHOLDERS))


# --- config and IO ---------------------------------------------------------


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_CONFIG
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["_config_path"] = str(config_path)
    config["_config_sha256"] = sha256_file(config_path)
    return config


def resolve(relative: str | Path) -> Path:
    """Config paths are relative to the verifier_sft directory."""
    path = Path(relative)
    return path if path.is_absolute() else (ROOT / path).resolve()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_json(path: str | Path, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


# --- normalization keys ----------------------------------------------------


def label_key(label: str) -> str:
    """Only notation differences: case, underscores, whitespace. Labels are never merged by meaning."""
    text = unicodedata.normalize("NFKC", label).lower().replace("_", " ")
    return re.sub(r"\s+", " ", text).strip()


def question_key(text: str) -> str:
    """Question identity for grouping: case, whitespace and punctuation ignored."""
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", text).lower())


def text_key(text: str) -> str:
    """Record identity for duplicate removal: case and whitespace ignored, operators kept."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text).lower())


def question_group_id(question: str) -> str:
    return "qg:" + hashlib.sha256(question_key(question).encode("utf-8")).hexdigest()[:16]


# --- prompt ----------------------------------------------------------------


class PromptError(RuntimeError):
    pass


def load_prompt(config: dict[str, Any], ablation: str = "none") -> dict[str, str]:
    prompt_cfg = config["prompt"]
    system_path = resolve(prompt_cfg["system"])
    user_path = resolve(prompt_cfg["user"] if ablation == "none" else prompt_cfg["ablations"][ablation])
    system = system_path.read_text(encoding="utf-8")
    user = user_path.read_text(encoding="utf-8")
    if ablation == "none":
        missing = [p for p in PLACEHOLDERS if "{" + p + "}" not in user]
        if missing:
            raise PromptError(f"{user_path} is missing placeholder(s): {missing}")
    return {
        "system": system,
        "user": user,
        "ablation": ablation,
        "system_sha256": sha256_file(system_path),
        "user_sha256": sha256_file(user_path),
    }


def render_user(template: str, record: dict[str, Any]) -> str:
    """Single left-to-right substitution; inserted text is never re-scanned."""
    values = {
        "question": record["question"],
        "solution": record["solution"],
        "error_description": record["error_description"],
    }
    return _PLACEHOLDER_RE.sub(lambda m: str(values[m.group(0)[1:-1]]), template)


def build_messages(prompt: dict[str, str], record: dict[str, Any], with_target: bool) -> list[dict[str, str]]:
    messages = [
        {"role": "system", "content": prompt["system"]},
        {"role": "user", "content": render_user(prompt["user"], record)},
    ]
    if with_target:
        if record["target"] not in LABELS:
            raise ValueError(f"target must be one of {LABELS}: {record['target']!r}")
        messages.append({"role": "assistant", "content": record["target"]})
    return messages


# --- tokenization ----------------------------------------------------------


class EncodingError(RuntimeError):
    pass


def encode_example(tokenizer: Any, messages: list[dict[str, str]]) -> dict[str, list[int]]:
    """input_ids for the full chat; labels only on the assistant answer (label + end tokens).

    Nothing is truncated: the caller decides what to do with long examples.
    """
    if messages[-1]["role"] != "assistant":
        raise EncodingError("the last message must be the assistant answer")
    full_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    prompt_text = tokenizer.apply_chat_template(messages[:-1], tokenize=False, add_generation_prompt=True)
    if not full_text.startswith(prompt_text):
        raise EncodingError("chat template: prompt text is not a prefix of the full text")
    full_ids = tokenizer(full_text, add_special_tokens=False)["input_ids"]
    prompt_ids = tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
    if full_ids[: len(prompt_ids)] != prompt_ids or len(full_ids) <= len(prompt_ids):
        raise EncodingError("prompt tokens are not a prefix of the full tokens")
    labels = [IGNORE_INDEX] * len(prompt_ids) + full_ids[len(prompt_ids):]
    return {"input_ids": full_ids, "labels": labels}


def generation_prompt(tokenizer: Any, messages: list[dict[str, str]]) -> str:
    if messages[-1]["role"] == "assistant":
        raise ValueError("inference messages must not contain the answer")
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


# --- output parsing --------------------------------------------------------


def parse_prediction(raw: str | None) -> str:
    """Exactly `aligned` or `not_aligned` after stripping whitespace; anything else is invalid."""
    text = (raw or "").strip()
    return text if text in LABELS else INVALID


# --- metrics ---------------------------------------------------------------


def _ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def compute_metrics(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Rows need `target`, `prediction` and `anchor_sample_id`.

    An invalid output counts as a wrong prediction everywhere: it lowers accuracy,
    the recall of its true class and pair accuracy, and is never dropped.
    """
    n = len(rows)
    per_class: dict[str, dict[str, Any]] = {}
    for label in LABELS:
        tp = sum(1 for r in rows if r["prediction"] == label and r["target"] == label)
        predicted = sum(1 for r in rows if r["prediction"] == label)
        actual = sum(1 for r in rows if r["target"] == label)
        precision = tp / predicted if predicted else 0.0
        recall = tp / actual if actual else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": actual,
            "predicted": predicted,
            "invalid": sum(1 for r in rows if r["target"] == label and r["prediction"] == INVALID),
        }
    positives = [r for r in rows if r["target"] == ALIGNED]
    negatives = [r for r in rows if r["target"] == NOT_ALIGNED]

    by_anchor: dict[str, dict[str, bool]] = defaultdict(dict)
    for r in rows:
        by_anchor[r["anchor_sample_id"]][r["target"]] = r["prediction"] == r["target"]
    pairs = [v for v in by_anchor.values() if len(v) == 2]

    return {
        "n": n,
        "accuracy": _ratio(sum(1 for r in rows if r["prediction"] == r["target"]), n),
        "macro_f1": (per_class[ALIGNED]["f1"] + per_class[NOT_ALIGNED]["f1"]) / 2 if n else None,
        "per_class": per_class,
        "negative_acceptance_rate": _ratio(sum(1 for r in negatives if r["prediction"] == ALIGNED), len(negatives)),
        "positive_rejection_rate": _ratio(sum(1 for r in positives if r["prediction"] == NOT_ALIGNED), len(positives)),
        "invalid_rate": _ratio(sum(1 for r in rows if r["prediction"] == INVALID), n),
        "pairs": len(pairs),
        "pair_accuracy": _ratio(sum(1 for v in pairs if all(v.values())), len(pairs)),
    }


def breakdown(
    rows: Sequence[dict[str, Any]],
    key: Callable[[dict[str, Any]], str],
    min_support: int = 1,
) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[key(r)].append(r)
    return {k: compute_metrics(v) for k, v in sorted(groups.items()) if len(v) >= min_support}


def bootstrap_ci(
    rows: Sequence[dict[str, Any]],
    n_samples: int,
    seed: int,
    metrics: Sequence[str] = ("accuracy", "macro_f1", "pair_accuracy"),
    alpha: float = 0.05,
) -> dict[str, dict[str, float | None]]:
    """Percentile intervals resampling question groups, not single rows."""
    import numpy as np

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[r["question_group_id"]].append(r)
    keys = sorted(groups)
    rng = np.random.RandomState(seed)
    values: dict[str, list[float]] = {m: [] for m in metrics}
    for _ in range(n_samples):
        picked = rng.randint(0, len(keys), size=len(keys))
        sample: list[dict[str, Any]] = []
        for copy, index in enumerate(picked):
            # a group drawn twice must count as two pairs, so anchors get a copy suffix
            for r in groups[keys[index]]:
                sample.append({**r, "anchor_sample_id": f"{r['anchor_sample_id']}#{copy}"})
        result = compute_metrics(sample)
        for m in metrics:
            if result[m] is not None:
                values[m].append(result[m])
    out: dict[str, dict[str, float | None]] = {}
    for m in metrics:
        if values[m]:
            lo, hi = np.percentile(values[m], [100 * alpha / 2, 100 * (1 - alpha / 2)])
            out[m] = {"low": float(lo), "high": float(hi)}
        else:
            out[m] = {"low": None, "high": None}
    return out
