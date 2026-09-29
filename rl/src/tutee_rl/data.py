"""Eedi RL data: model inputs, privileged grading annotations and the question-group split.

The Student only ever sees `problem` and `target_misconception_description`. Grading information
(CorrectAnswerText, AnswerContract, distractors) lives in a separate file keyed by PairId and is
read by the reward code, never written into the model input rows.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .common import sha256_file

OPTIONS = ("A", "B", "C", "D")
MODEL_INPUT_KEYS = ("PairId", "QuestionId", "MisconceptionId", "problem", "target_misconception_description")
PRIVILEGED_KEYS = (
    "CorrectAnswerText",
    "AnswerContract",
    "TargetDistractorsJSON",
    "OtherLabeledDistractorsJSON",
    "UnlabeledDistractorsJSON",
)


class DataError(RuntimeError):
    pass


def group_key(problem: str) -> str:
    """Question group: NFKC and collapsed whitespace (the plan's split key)."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", problem)).strip()


def split_groups(keys: list[str], test_ratio: float, seed: int) -> dict[str, str]:
    """Sort unique keys, permute with numpy.random.RandomState(seed), first ceil(n*ratio) -> test (the rest train)."""
    import numpy as np

    unique = sorted(set(keys))
    perm = np.random.RandomState(seed).permutation(len(unique))
    n_test = math.ceil(len(unique) * test_ratio)
    test = {unique[i] for i in perm[:n_test]}
    return {k: ("test" if k in test else "train") for k in unique}


def _mid(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value or value.lower() == "nan":
            return None
        return int(float(value))
    return int(value)


def load_model_inputs(path: Path) -> list[dict[str, Any]]:
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            missing = [k for k in MODEL_INPUT_KEYS if k not in row]
            if missing:
                raise DataError(f"{path}:{line_no} is missing {missing}")
            row["QuestionId"] = str(row["QuestionId"])
            row["MisconceptionId"] = _mid(row["MisconceptionId"])
            rows.append(row)
    return rows


def load_judgements(path: Path) -> dict[str, dict[str, Any]]:
    import pandas as pd

    df = pd.read_csv(path, dtype={"QuestionId": str}, keep_default_na=True)
    out: dict[str, dict[str, Any]] = {}
    for rec in df.to_dict(orient="records"):
        if str(rec.get("Split", "")).strip() != "train":
            continue
        qid = str(rec["QuestionId"]).strip()
        if qid in out:
            raise DataError(f"duplicate train QuestionId {qid} in {path}")
        out[qid] = rec
    return out


def _text(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value)


def distractors_from_judgement(rec: dict[str, Any], misconception_id: int) -> dict[str, list[dict[str, Any]]]:
    correct = str(rec["CorrectAnswer"]).strip()
    target, other, unlabeled = [], [], []
    for opt in OPTIONS:
        if opt == correct:
            continue
        item = {"option": opt, "text": _text(rec.get(f"Answer{opt}Text")), "misconception_id": _mid(rec.get(f"Misconception{opt}Id"))}
        if item["misconception_id"] is None:
            unlabeled.append(item)
        elif item["misconception_id"] == misconception_id:
            target.append(item)
        else:
            other.append(item)
    return {"TargetDistractors": target, "OtherLabeledDistractors": other, "UnlabeledDistractors": unlabeled}


def _parse_json_field(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value) if value.strip() else []
    return value if value is not None else []


def load_privileged_file(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if "PairId" not in row:
                raise DataError(f"{path}:{line_no} has no PairId")
            missing = [k for k in PRIVILEGED_KEYS if k not in row]
            if missing:
                raise DataError(f"{path}:{line_no} is missing {missing}")
            if row["PairId"] in out:
                raise DataError(f"duplicate PairId {row['PairId']} in {path}")
            out[row["PairId"]] = {
                "CorrectAnswerText": row["CorrectAnswerText"],
                "AnswerContract": row["AnswerContract"],
                "TargetDistractors": _parse_json_field(row["TargetDistractorsJSON"]),
                "OtherLabeledDistractors": _parse_json_field(row["OtherLabeledDistractorsJSON"]),
                "UnlabeledDistractors": _parse_json_field(row["UnlabeledDistractorsJSON"]),
                "source": "privileged_file",
            }
    return out


def prepare(
    model_inputs_path: Path,
    privileged_path: Path | None,
    judgements_path: Path | None,
    test_ratio: float,
    seed: int,
) -> dict[str, Any]:
    """Returns rows per split, privileged rows, the split manifest and a check report. Raises DataError on hard failures."""
    rows = load_model_inputs(model_inputs_path)
    checks: dict[str, Any] = {}
    warnings: list[str] = []

    pair_ids = [r["PairId"] for r in rows]
    dup = [p for p, c in Counter(pair_ids).items() if c > 1]
    if dup:
        raise DataError(f"duplicate PairId in model inputs: {dup[:10]}")
    pairs = Counter((r["QuestionId"], r["MisconceptionId"]) for r in rows)
    dup_pairs = [k for k, c in pairs.items() if c > 1]
    if dup_pairs:
        raise DataError(f"duplicate (QuestionId, MisconceptionId) in model inputs: {dup_pairs[:10]}")
    bad_format = [r["PairId"] for r in rows if r["PairId"] != f"{r['QuestionId']}__{r['MisconceptionId']}"]
    checks["pair_id_format_mismatch"] = len(bad_format)
    if bad_format:
        warnings.append(f"{len(bad_format)} PairIds are not QuestionId__MisconceptionId (e.g. {bad_format[:3]})")
    empty = [r["PairId"] for r in rows if not str(r["problem"]).strip() or not str(r["target_misconception_description"]).strip()]
    if empty:
        raise DataError(f"empty problem or description for {empty[:10]}")

    judgements = load_judgements(judgements_path) if judgements_path and judgements_path.exists() else None
    if judgements is not None:
        not_keep = [r["PairId"] for r in rows if judgements.get(r["QuestionId"], {}).get("Decision") != "KEEP"]
        if not_keep:
            raise DataError(f"{len(not_keep)} model input rows are not KEEP train questions: {not_keep[:10]}")
        decisions = Counter(str(v.get("Decision")) for v in judgements.values())
        checks["judgement_decisions_train"] = dict(decisions)
        mismatch = [r["PairId"] for r in rows if group_key(r["problem"]) != group_key(_text(judgements[r["QuestionId"]].get("QuestionText")))]
        checks["problem_text_differs_from_QuestionText"] = len(mismatch)
        if mismatch:
            warnings.append(f"{len(mismatch)} rows: problem differs from the audit QuestionText after whitespace "
                            f"normalisation (e.g. {mismatch[:3]}); problem is used as-is")

    if privileged_path and privileged_path.exists():
        privileged = load_privileged_file(privileged_path)
        missing = sorted(set(pair_ids) - set(privileged))
        extra = sorted(set(privileged) - set(pair_ids))
        if missing or extra:
            raise DataError(f"PairId mismatch model inputs vs privileged: {len(missing)} missing, {len(extra)} extra "
                            f"(e.g. missing {missing[:5]}, extra {extra[:5]})")
        if judgements is not None:
            diff = [p for p in pair_ids if group_key(_text(privileged[p]["CorrectAnswerText"]))
                    != group_key(_text(judgements[p.split('__')[0]].get("CorrectAnswerText")))]
            checks["correct_answer_differs_from_audit"] = len(diff)
            if diff:
                warnings.append(f"{len(diff)} PairIds: CorrectAnswerText differs from the audit CSV (e.g. {diff[:3]})")
        privileged_source = str(privileged_path)
    elif judgements is not None:
        privileged = {}
        for r in rows:
            rec = judgements[r["QuestionId"]]
            privileged[r["PairId"]] = {
                "CorrectAnswerText": _text(rec.get("CorrectAnswerText")),
                "AnswerContract": _text(rec.get("AnswerContract")),
                **distractors_from_judgement(rec, r["MisconceptionId"]),
                "source": "rebuilt_from_judgements",
            }
        privileged_source = f"rebuilt from {judgements_path}"
    else:
        raise DataError("need data/raw/train_privileged_annotations.jsonl or data/raw/all_judgements.csv")

    no_answer = [p for p in pair_ids if not _text(privileged[p]["CorrectAnswerText"]).strip()]
    if no_answer:
        raise DataError(f"{len(no_answer)} PairIds have no CorrectAnswerText: {no_answer[:10]}")
    no_contract = [p for p in pair_ids if not _text(privileged[p]["AnswerContract"]).strip()]
    checks["missing_answer_contract"] = len(no_contract)
    if no_contract:
        warnings.append(f"{len(no_contract)} PairIds have an empty AnswerContract (e.g. {no_contract[:3]})")
    no_target = [p for p in pair_ids if not privileged[p]["TargetDistractors"]]
    checks["pairs_without_target_distractor"] = len(no_target)
    if no_target:
        warnings.append(f"{len(no_target)} PairIds have no target distractor (diagnostic only)")

    assignment = split_groups([group_key(r["problem"]) for r in rows], test_ratio, seed)
    group_ids = {k: f"g{i:05d}" for i, k in enumerate(sorted(assignment))}
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    manifest_groups: dict[str, dict[str, Any]] = {}
    for r in rows:
        key = group_key(r["problem"])
        split = assignment[key]
        gid = group_ids[key]
        by_split[split].append({
            "PairId": r["PairId"],
            "QuestionId": r["QuestionId"],
            "MisconceptionId": r["MisconceptionId"],
            "problem": r["problem"],
            "target_misconception_description": r["target_misconception_description"],
            "group_id": gid,
            "split": split,
        })
        entry = manifest_groups.setdefault(gid, {"group_id": gid, "split": split, "question_ids": set(), "pair_ids": []})
        entry["question_ids"].add(r["QuestionId"])
        entry["pair_ids"].append(r["PairId"])
    manifest = [{**g, "question_ids": sorted(g["question_ids"])} for g in manifest_groups.values()]

    # the same QuestionId must never sit in two splits, and no group straddles splits by construction
    q_splits = defaultdict(set)
    for split, split_rows in by_split.items():
        for r in split_rows:
            q_splits[r["QuestionId"]].add(split)
    leaking = [q for q, s in q_splits.items() if len(s) > 1]
    if leaking:
        raise DataError(f"QuestionIds in both splits: {leaking[:10]}")

    counts = {s: {"pairs": len(v), "questions": len({r["QuestionId"] for r in v}), "groups": len({r["group_id"] for r in v})}
              for s, v in sorted(by_split.items())}
    report = {
        "inputs": {
            "model_inputs": {"path": str(model_inputs_path), "sha256": sha256_file(model_inputs_path), "rows": len(rows)},
            "privileged_source": privileged_source,
            "privileged_sha256": sha256_file(privileged_path) if privileged_path and privileged_path.exists() else None,
            "judgements_sha256": sha256_file(judgements_path) if judgements_path and judgements_path.exists() else None,
        },
        "split": {"test_ratio": test_ratio, "seed": seed, "groups": len(assignment), "splits": ["train", "test"],
                  "rule": "NFKC+whitespace problem key, sorted, RandomState(seed).permutation, first ceil(n*ratio) -> test"},
        "counts": counts,
        "checks": checks,
        "warnings": warnings,
    }
    priv_rows = [{"PairId": p, **privileged[p]} for p in pair_ids]
    return {"splits": dict(by_split), "privileged": priv_rows, "manifest": manifest, "report": report}
