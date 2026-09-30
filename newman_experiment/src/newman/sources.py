"""Source records: the four error datasets (SFT) and GSM8K (RL questions, unit allowlist).

SFT cases come from the repository's full pool (../data/full/pool.jsonl, one record per unique Q/S/label) with
the v2 verifier filters (verifier_sft/prepare_descriptive_pairs.py: description status ok, processing ok, three
MathClean questions without their figure, exact duplicates, plan 5.2) and a stricter multi-label rule: every case of
a student solution that carries more than one error label in the pool *or* in the raw normalized records is
dropped (user instruction 2026-09-30). The Newman taxonomy is attached afterwards: excluded types leave the pool,
unknown labels stop preparation.

GSM8K is read from the HF parquet files at a pinned revision; each file's sha256 and row count are checked.
"""

from __future__ import annotations

import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from .common import import_verifier_sft, read_jsonl, rel, resolve, sha256_file
from .taxonomy import EXCLUDED, Taxonomy


class SourceError(RuntimeError):
    pass


# --- SFT cases ----------------------------------------------------------------


def load_sft_cases(data_cfg: Mapping[str, Any], taxonomy: Taxonomy) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Every pool record as a case with `exclusion_reason` ('' = eligible) and, if eligible, its Newman type/stage."""
    prep = import_verifier_sft("prepare_descriptive_pairs")
    inputs = data_cfg["inputs"]
    pool = read_jsonl(resolve(inputs["pool"]))
    descriptions = {r["sample_id"]: r for r in read_jsonl(resolve(inputs["descriptions"]))}
    filters = data_cfg["filters"]
    cases = prep.build_cases(pool, descriptions, {"filters": filters})
    multi = None
    if filters.get("exclude_multi_label_solutions"):
        extra = [r for p in filters.get("multi_label_extra_sources", []) for r in read_jsonl(resolve(p))]
        multi = exclude_multi_label_solutions(cases, extra)
    prep.remove_duplicates(cases)

    unknown = Counter()
    for c in cases:
        c.update(error_id=None, newman_stage=None, mathedu_id=None)
        if c["exclusion_reason"]:
            continue
        kind, type_id = taxonomy.resolve(c["dataset"], c["source_error_label"])
        if kind == "unknown":
            unknown[(c["dataset"], c["source_error_label"])] += 1
            c["exclusion_reason"] = "newman_unmapped_label"
        elif kind == EXCLUDED:
            c["exclusion_reason"] = f"newman_excluded_type:{type_id}"
        else:
            c["error_id"] = type_id
            c["newman_stage"] = taxonomy.stage_of(type_id)
    if unknown:
        raise SourceError(f"source labels with no taxonomy entry (add an approved alias or exclude): {dict(unknown)}")
    by_id = {r["sample_id"]: r for r in pool}
    for c in cases:
        c["mathedu_id"] = (by_id[c["sample_id"]].get("annotations") or {}).get("mathedu_id") if c["dataset"] == "mathedu" else None
    stats = {
        "pool_records": len(pool),
        "descriptions": len(descriptions),
        "multi_label_solutions_excluded": multi,
        "inputs": {k: {"path": rel(resolve(v)), "sha256": sha256_file(resolve(v))}
                   for k, v in inputs.items() if k in ("pool", "descriptions")},
    }
    return cases, stats


def exclude_multi_label_solutions(cases: list[dict[str, Any]], extra_records: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Drop every case of a student solution that carries more than one error label (user instruction 2026-09-30).

    A solution = same dataset, question and solution text after NFKC, lowercase and whitespace removal. Labels are
    collected over every pool record (also those excluded for another reason) and over the raw normalized records
    outside the pool (e.g. a Stepwise teacher's "None of the above" next to another teacher's "Misunderstanding of a
    question"), so the rule depends on the source annotations only. Labels are compared after notation
    normalization (case, underscores, whitespace). An already excluded case keeps its first reason.
    """
    vc = import_verifier_sft("verifier_common")

    def key(dataset, question, solution):
        if not (isinstance(question, str) and question.strip() and isinstance(solution, str) and solution.strip()):
            return None
        return dataset, vc.text_key(question), vc.text_key(solution)

    labels: dict[tuple, set[str]] = {}
    pool_labels: dict[tuple, set[str]] = {}
    for c in cases:
        k = key(c["dataset"], c["question"], c["solution"])
        if k is not None and isinstance(c["source_error_label"], str) and c["source_error_label"].strip():
            labels.setdefault(k, set()).add(vc.label_key(c["source_error_label"]))
            pool_labels.setdefault(k, set()).add(vc.label_key(c["source_error_label"]))
    for r in extra_records:
        k = key(r["dataset"], r.get("question"), r.get("incorrect_solution"))
        if k in labels and isinstance(r.get("source_error_label"), str) and r["source_error_label"].strip():
            labels[k].add(vc.label_key(r["source_error_label"]))
    multi = {k for k, v in labels.items() if len(v) > 1}
    only_extra = {k for k in multi if len(pool_labels[k]) == 1}
    stats: dict[str, Counter] = {"solutions": Counter(), "solutions_found_only_with_raw_labels": Counter(),
                                 "cases": Counter(), "newly_excluded": Counter()}
    for k in multi:
        stats["solutions"][k[0]] += 1
    for k in only_extra:
        stats["solutions_found_only_with_raw_labels"][k[0]] += 1
    for c in cases:
        if key(c["dataset"], c["question"], c["solution"]) in multi:
            stats["cases"][c["dataset"]] += 1
            if not c["exclusion_reason"]:
                c["exclusion_reason"] = "multi_label_solution"
                stats["newly_excluded"][c["dataset"]] += 1
    return {k: dict(sorted(v.items())) for k, v in stats.items()}


def exclusion_table(cases: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """dataset -> reason -> count ('' = eligible), with duplicate records collapsed into one reason."""
    out: dict[str, Counter] = {}
    for c in cases:
        reason = c["exclusion_reason"]
        reason = "duplicate_record" if reason.startswith("duplicate_record_of") else reason or "eligible"
        out.setdefault(c["dataset"], Counter())[reason] += 1
    return {ds: dict(sorted(v.items())) for ds, v in sorted(out.items())}


# --- GSM8K ----------------------------------------------------------------------


def gsm8k_paths(data_cfg: Mapping[str, Any]) -> dict[str, Path]:
    root = resolve(data_cfg["inputs"]["gsm8k_dir"])
    return {split: root / f"{split}.parquet" for split in data_cfg["gsm8k"]["files"]}


def fetch_gsm8k(data_cfg: Mapping[str, Any]) -> dict[str, Path]:
    """Download the pinned parquet files if absent; always verify sha256 (the allowlist indexes these exact rows)."""
    g = data_cfg["gsm8k"]
    out = {}
    for split, path in gsm8k_paths(data_cfg).items():
        spec = g["files"][split]
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            url = f"https://huggingface.co/datasets/{g['repo_id']}/resolve/{g['revision']}/{spec['path']}"
            tmp = path.with_suffix(".part")
            urllib.request.urlretrieve(url, tmp)  # noqa: S310 - fixed https URL at a pinned revision
            tmp.rename(path)
        digest = sha256_file(path)
        if digest != spec["sha256"]:
            raise SourceError(f"{path}: sha256 {digest} != pinned {spec['sha256']} (GSM8K {g['revision']})")
        out[split] = path
    return out


def load_gsm8k(data_cfg: Mapping[str, Any], fetch: bool = True) -> list[dict[str, Any]]:
    """All rows of the pinned GSM8K main config: split, 0-based row, question, answer, reference answer."""
    import pandas as pd

    paths = fetch_gsm8k(data_cfg) if fetch else gsm8k_paths(data_cfg)
    rows = []
    for split, path in paths.items():
        if not path.exists():
            raise SourceError(f"{path} is missing (python scripts/fetch_sources.py)")
        df = pd.read_parquet(path)
        expected = int(data_cfg["gsm8k"]["files"][split]["rows"])
        if len(df) != expected:
            raise SourceError(f"{path}: {len(df)} rows, expected {expected}")
        for i, (question, answer) in enumerate(zip(df["question"], df["answer"])):
            if "####" not in answer:
                raise SourceError(f"GSM8K {split} row {i} has no '####' answer line")
            rows.append({"split": split, "row": i, "question": question, "answer": answer,
                         "reference_answer": answer.rsplit("####", 1)[1].strip()})
    return rows
