#!/usr/bin/env python3
"""Build the fixed positive/negative pairs for the descriptive verifier SFT.

Order (plan section 5): cases whose description status is ok -> duplicate
removal and question groups -> train/validation/test split by question group ->
one negative per case inside each split -> length check.

Negative for case i: the description of a case j drawn uniformly from the cases
in the same split and dataset whose normalized source label differs and whose
question group differs. numpy.random.RandomState(seed) is re-initialized once
per split; anchors and candidates are ordered by sample_id. No semantic review
of negatives is done: targets are assigned automatically.

Outputs (paths from the config, relative to verifier_sft/):
  data/descriptive_v1/{train,validation,test}.jsonl   pairs; model input is Q/S/C only
  data/descriptive_v1/meta.json                       input hashes, prompt hashes, counts
  manifests/split_manifest.jsonl                      every case: split or exclusion reason
  manifests/pair_manifest.jsonl                       every anchor: donor, candidates, kept or why not
  reports/data_audit.md
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verifier_common import (  # noqa: E402
    ALIGNED,
    NOT_ALIGNED,
    build_messages,
    encode_example,
    label_key,
    load_config,
    load_prompt,
    question_group_id,
    question_key,
    read_jsonl,
    resolve,
    sha256_file,
    text_key,
    write_json,
    write_jsonl,
)

SPLITS = ("train", "validation", "test")


# --- 1. cases --------------------------------------------------------------


def build_cases(
    pool: list[dict[str, Any]],
    descriptions: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    filters = config["filters"]
    held = filters.get("held_out_missing_information", {})
    cases = []
    for rec in sorted(pool, key=lambda r: r["sample_id"]):
        d = descriptions.get(rec["sample_id"]) or {}
        case = {
            "sample_id": rec["sample_id"],
            "dataset": rec["dataset"],
            "benchmark": (rec.get("annotations") or {}).get("source_benchmark", ""),
            "question_group_id": question_group_id(rec["question"]),
            "source_question_group_id": rec.get("question_group_id", ""),
            "question": rec["question"],
            "solution": rec["incorrect_solution"],
            "source_error_label": rec["source_error_label"],
            "error_description": d.get("description"),
            "description_status": d.get("status"),
            "processing_status": d.get("processing_status"),
            "evidence_quote": d.get("evidence_quote"),
            "description_model": d.get("model"),
            "prompt_version": d.get("prompt_version"),
            "source_ids": rec.get("source_ids") or [rec.get("source_id")],
            "exclusion_reason": "",
        }
        missing = [
            name
            for name, value in (
                ("question", case["question"]),
                ("solution", case["solution"]),
                ("source_error_label", case["source_error_label"]),
                ("error_description", case["error_description"]),
            )
            if not (isinstance(value, str) and value.strip())
        ]
        if not d:
            case["exclusion_reason"] = "no_description_result"
        elif case["processing_status"] != filters["processing_status"]:
            case["exclusion_reason"] = f"processing_status:{case['processing_status']}"
        elif case["description_status"] != filters["description_status"]:
            case["exclusion_reason"] = f"description_status:{case['description_status']}"
        elif missing:
            case["exclusion_reason"] = "missing_field:" + ",".join(missing)
        elif case["sample_id"] in held:
            case["exclusion_reason"] = "missing_essential_information"
        cases.append(case)
    return cases


def remove_duplicates(cases: list[dict[str, Any]]) -> None:
    """Same dataset, question, solution and label: keep the smallest sample_id."""
    kept: dict[tuple, str] = {}
    for case in cases:  # sorted by sample_id
        if case["exclusion_reason"]:
            continue
        key = (
            case["dataset"],
            text_key(case["question"]),
            text_key(case["solution"]),
            label_key(case["source_error_label"]),
        )
        if key in kept:
            case["exclusion_reason"] = f"duplicate_record_of:{kept[key]}"
        else:
            kept[key] = case["sample_id"]


# --- 2. split --------------------------------------------------------------


def group_stratum(group_cases: list[dict[str, Any]]) -> str:
    counts = Counter(
        f"{c['dataset']}|{c['benchmark']}|{label_key(c['source_error_label'])}" for c in group_cases
    )
    top = max(counts.values())
    return min(k for k, v in counts.items() if v == top)


def assign_splits(
    cases: list[dict[str, Any]],
    ratios: dict[str, float],
    forced_train_keys: set[str],
    seed: int,
) -> dict[str, Any]:
    """Assign every eligible case the split of its question group (in place)."""
    import numpy as np

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        groups[case["question_group_id"]].append(case)

    split_of: dict[str, str] = {}
    forced = sorted(g for g, cs in groups.items() if question_key(cs[0]["question"]) in forced_train_keys)
    for g in forced:
        split_of[g] = "train"

    strata: dict[str, list[str]] = defaultdict(list)
    for g, cs in groups.items():
        if g not in split_of:
            strata[group_stratum(cs)].append(g)

    rng = np.random.RandomState(seed)
    per_stratum = {}
    for stratum in sorted(strata):
        gids = sorted(strata[stratum])
        order = [gids[i] for i in rng.permutation(len(gids))]
        n = len(order)
        n_test = math.floor(n * ratios["test"] + 0.5)
        n_val = math.floor(n * ratios["validation"] + 0.5)
        for i, g in enumerate(order):
            split_of[g] = "test" if i < n_test else "validation" if i < n_test + n_val else "train"
        per_stratum[stratum] = {"groups": n, "test": n_test, "validation": n_val, "train": n - n_test - n_val}

    for case in cases:
        case["split"] = split_of[case["question_group_id"]]
        case["prompt_dev_group"] = case["question_group_id"] in forced
    return {"forced_train_groups": forced, "per_stratum": per_stratum, "groups": len(groups)}


# --- 3. negatives ----------------------------------------------------------


def pair_record(anchor: dict[str, Any], donor: dict[str, Any], target: str) -> dict[str, Any]:
    return {
        "pair_id": f"{anchor['sample_id']}::{'pos' if target == ALIGNED else 'neg'}",
        "split": anchor["split"],
        "target": target,
        "anchor_sample_id": anchor["sample_id"],
        "donor_sample_id": donor["sample_id"],
        "question_group_id": anchor["question_group_id"],
        "donor_question_group_id": donor["question_group_id"],
        "dataset": anchor["dataset"],
        "benchmark": anchor["benchmark"],
        "anchor_source_error_label": anchor["source_error_label"],
        "donor_source_error_label": donor["source_error_label"],
        "question": anchor["question"],
        "solution": anchor["solution"],
        "error_description": donor["error_description"],
    }


def make_pairs(cases: list[dict[str, Any]], seed: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    import numpy as np

    pairs: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    for split in SPLITS:
        rng = np.random.RandomState(seed)
        in_split = sorted((c for c in cases if c["split"] == split), key=lambda c: c["sample_id"])
        by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for c in in_split:
            by_dataset[c["dataset"]].append(c)
        for anchor in in_split:
            a_label = label_key(anchor["source_error_label"])
            candidates = [
                c
                for c in by_dataset[anchor["dataset"]]
                if label_key(c["source_error_label"]) != a_label
                and c["question_group_id"] != anchor["question_group_id"]
            ]
            entry = {
                "anchor_sample_id": anchor["sample_id"],
                "split": split,
                "dataset": anchor["dataset"],
                "question_group_id": anchor["question_group_id"],
                "anchor_source_error_label": anchor["source_error_label"],
                "n_candidates": len(candidates),
                "donor_sample_id": None,
                "donor_source_error_label": None,
                "status": "paired",
                "reason": "",
            }
            if not candidates:
                entry.update(status="excluded", reason="no_candidate")
                manifest.append(entry)
                continue
            donor = candidates[rng.randint(0, len(candidates))]
            entry["donor_sample_id"] = donor["sample_id"]
            entry["donor_source_error_label"] = donor["source_error_label"]
            manifest.append(entry)
            pairs.append(pair_record(anchor, anchor, ALIGNED))
            pairs.append(pair_record(anchor, donor, NOT_ALIGNED))
    return pairs, manifest


# --- 4. length -------------------------------------------------------------


def apply_length_limit(
    pairs: list[dict[str, Any]],
    manifest: list[dict[str, Any]],
    tokenizer: Any,
    prompt: dict[str, str],
    max_len: int,
) -> list[dict[str, Any]]:
    """Token counts include the assistant label; a pair over the limit is dropped as a whole."""
    by_anchor: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in pairs:
        p["n_tokens"] = len(encode_example(tokenizer, build_messages(prompt, p, with_target=True))["input_ids"])
        by_anchor[p["anchor_sample_id"]].append(p)
    too_long = {a for a, ps in by_anchor.items() if any(p["n_tokens"] > max_len for p in ps)}
    for entry in manifest:
        ps = by_anchor.get(entry["anchor_sample_id"], [])
        entry["n_tokens"] = {p["target"]: p["n_tokens"] for p in ps}
        if entry["anchor_sample_id"] in too_long:
            entry.update(status="excluded", reason=f"exceeds_max_seq_length:{max_len}")
    return [p for p in pairs if p["anchor_sample_id"] not in too_long]


# --- 5. checks and report --------------------------------------------------


def run_checks(
    cases: list[dict[str, Any]], pairs: list[dict[str, Any]], max_len: int | None
) -> list[tuple[str, bool, str]]:
    eligible = [c for c in cases if not c["exclusion_reason"]]
    by_id = {c["sample_id"]: c for c in eligible}
    checks = []

    group_splits: dict[str, set[str]] = defaultdict(set)
    for c in eligible:
        group_splits[c["question_group_id"]].add(c["split"])
    bad = [g for g, s in group_splits.items() if len(s) > 1]
    checks.append(("each question group lies in one split", not bad, f"{len(bad)} groups in several splits"))

    negs = [p for p in pairs if p["target"] == NOT_ALIGNED]
    poss = [p for p in pairs if p["target"] == ALIGNED]
    checks.append((
        "negative donor from the same split",
        all(by_id[p["donor_sample_id"]]["split"] == p["split"] for p in negs), "",
    ))
    checks.append((
        "negative donor from the same dataset",
        all(by_id[p["donor_sample_id"]]["dataset"] == p["dataset"] for p in negs), "",
    ))
    checks.append((
        "negative donor label differs (normalized)",
        all(label_key(p["donor_source_error_label"]) != label_key(p["anchor_source_error_label"]) for p in negs), "",
    ))
    checks.append((
        "negative donor from a different question group",
        all(p["donor_question_group_id"] != p["question_group_id"] for p in negs), "",
    ))
    checks.append((
        "positive donor is the anchor itself",
        all(p["donor_sample_id"] == p["anchor_sample_id"] for p in poss), "",
    ))
    per_anchor = Counter((p["anchor_sample_id"], p["target"]) for p in pairs)
    anchors = {p["anchor_sample_id"] for p in pairs}
    checks.append((
        "every kept anchor has one positive and one negative",
        all(per_anchor[(a, ALIGNED)] == 1 and per_anchor[(a, NOT_ALIGNED)] == 1 for a in anchors), "",
    ))
    checks.append((
        "all anchors and donors have description status ok",
        all(by_id[p["anchor_sample_id"]]["description_status"] == "ok"
            and by_id[p["donor_sample_id"]]["description_status"] == "ok" for p in pairs), "",
    ))
    checks.append((
        "no empty question / solution / description",
        all(all(isinstance(p[k], str) and p[k].strip() for k in ("question", "solution", "error_description")) for p in pairs), "",
    ))
    in_test = [c for c in eligible if c["split"] == "test" and c.get("prompt_dev_group")]
    checks.append(("no prompt-development (dev 40) question group in test", not in_test, f"{len(in_test)} cases"))
    if max_len is not None:
        over = [p for p in pairs if p.get("n_tokens", 0) > max_len]
        checks.append((f"no pair over {max_len} tokens", not over, f"{len(over)} pairs"))
    return checks


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join([" --- "] * len(headers)) + "|"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def pct(n: int, d: int) -> str:
    return f"{n} ({100 * n / d:.1f}%)" if d else str(n)


def write_report(
    path: Path,
    config: dict[str, Any],
    meta: dict[str, Any],
    cases: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
    manifest: list[dict[str, Any]],
    split_info: dict[str, Any],
    checks: list[tuple[str, bool, str]],
) -> None:
    eligible = [c for c in cases if not c["exclusion_reason"]]
    datasets = sorted({c["dataset"] for c in cases})
    L: list[str] = []
    L += [f"# Data audit — {config['experiment']}", ""]
    L += [f"Created (UTC): {meta['created_at_utc']} · seed {config['seed']} · config sha256 `{config['_config_sha256'][:16]}`", ""]
    L += ["Targets are assigned automatically (own description = aligned, description from a case with a different "
          "source label = not_aligned). No semantic review of negatives was done; metrics on these pairs measure "
          "agreement with the automatic targets, not human-verified alignment.", ""]

    L += ["## 1. Inputs", ""]
    L += [md_table(["input", "path", "sha256"], [[k, v["path"], f"`{v['sha256'][:16]}`"] for k, v in meta["inputs"].items()]), ""]
    run = meta.get("description_run", {})
    L += [f"Descriptions: model `{run.get('model')}`, prompt {run.get('prompt_version')} "
          f"(`{str(run.get('prompt_sha256'))[:16]}`), run `{run.get('run_id')}`.", ""]

    L += ["## 2. Case selection", ""]

    def reason_of(c: dict[str, Any]) -> str:
        r = c["exclusion_reason"]
        return "duplicate_record" if r.startswith("duplicate_record_of") else r

    reasons = sorted({reason_of(c) for c in cases if c["exclusion_reason"]})
    rows = []
    for ds in datasets:
        sub = [c for c in cases if c["dataset"] == ds]
        row = [ds, len(sub)] + [sum(1 for c in sub if reason_of(c) == r) for r in reasons]
        row.append(sum(1 for c in sub if not c["exclusion_reason"]))
        rows.append(row)
    rows.append(["total", len(cases)] + [sum(r[i + 2] for r in rows) for i in range(len(reasons))] + [len(eligible)])
    L += [md_table(["dataset", "cases"] + reasons + ["eligible"], rows), ""]
    held = config["filters"].get("held_out_missing_information", {})
    if held:
        L += ["Held out for missing essential information (found by keyword scan for figure/diagram/graph/table "
              "references without [asy] code, then read manually):", ""]
        L += [f"- `{k}`: {v}" for k, v in held.items()]
        L += [""]
    dups = [c for c in cases if c["exclusion_reason"].startswith("duplicate_record_of")]
    L += [f"Duplicate records removed: {len(dups)} (same dataset, question and solution after NFKC/lowercase/"
          "whitespace removal, same normalized label; the smallest sample_id is kept).", ""]

    L += ["## 3. Question groups", ""]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in eligible:
        groups[c["question_group_id"]].append(c)
    old = {c["source_question_group_id"] for c in eligible}
    def src(c: dict[str, Any]) -> str:
        return c["dataset"] + (f"-{c['benchmark']}" if c["benchmark"] else "")
    cross = Counter(" + ".join(sorted({src(c) for c in cs})) for cs in groups.values() if len({src(c) for c in cs}) > 1)
    sizes = Counter(len(cs) for cs in groups.values())
    same_solution = sum(
        1 for cs in groups.values()
        if len({text_key(c["solution"]) for c in cs}) < len(cs)
    )
    L += [f"- groups: {len(groups)} (key: {config['grouping']['question_group_key']}); "
          f"the description pipeline's key (case and whitespace only) gives {len(old)}"]
    L += [f"- cases per group: {dict(sorted(sizes.items()))}"]
    L += [f"- groups spanning sources: {dict(cross)}"]
    L += [f"- groups where one solution carries several source labels (e.g. Stepwise annotated by several teachers): {same_solution}. "
          "Each such case keeps its own positive; they share a group, so they never serve as each other's negative."]
    L += [""]

    L += ["## 4. Split", ""]
    L += [f"Question-group split {config['split']['ratios']}, stratified by {config['split']['stratify_by']}. "
          f"Groups containing a question from the {len(meta['prompt_dev_sample_ids'])} prompt-development (dev) cases "
          f"are forced into train: {len(split_info['forced_train_groups'])} groups. The earlier 160 holdout cases were "
          "not viewed or used for prompt changes, so they are treated as unused.", ""]
    rows = []
    for ds in datasets + ["total"]:
        sub = eligible if ds == "total" else [c for c in eligible if c["dataset"] == ds]
        rows.append([ds, len(sub)] + [pct(sum(1 for c in sub if c["split"] == s), len(sub)) for s in SPLITS]
                    + [len({c["question_group_id"] for c in sub})])
    L += [md_table(["dataset", "cases", *SPLITS, "groups"], rows), ""]
    L += ["Cases per source label and split:", ""]
    rows = []
    for (ds, lab), cs in sorted(Counter((c["dataset"], c["source_error_label"]) for c in eligible).items()):
        sub = [c for c in eligible if c["dataset"] == ds and c["source_error_label"] == lab]
        counts = [sum(1 for c in sub if c["split"] == s) for s in SPLITS]
        flag = "sparse" if min(counts[1:]) < 3 else ""
        rows.append([ds, lab, len(sub), *counts, flag])
    L += [md_table(["dataset", "source label", "cases", *SPLITS, "note"], rows), ""]
    L += ["`sparse` = fewer than 3 cases in validation or test; per-label results there are not reliable.", ""]

    L += ["## 5. Negatives", ""]
    rows = []
    for s in SPLITS:
        m = [e for e in manifest if e["split"] == s]
        rows.append([
            s, len(m),
            sum(1 for e in m if e["status"] == "paired"),
            sum(1 for e in m if e["reason"] == "no_candidate"),
            sum(1 for e in m if e["reason"].startswith("exceeds")),
            sum(1 for p in pairs if p["split"] == s),
        ])
    L += [md_table(["split", "anchors", "kept pairs", "no candidate", "over length", "pair records (2 per anchor)"], rows), ""]
    negs = [p for p in pairs if p["target"] == NOT_ALIGNED]
    reuse = Counter(p["donor_sample_id"] for p in negs)
    own_description = {c["sample_id"]: text_key(c["error_description"]) for c in eligible}
    same_text = sum(1 for p in negs if text_key(p["error_description"]) == own_description[p["anchor_sample_id"]])
    L += [f"- distinct donors: {len(reuse)}; most reuse of one donor: {max(reuse.values()) if reuse else 0}"]
    L += [f"- negatives whose description text equals the anchor's own description: {same_text} "
          "(kept: no similarity-based exclusion by design)"]
    L += [""]
    for ds in datasets:
        sub = [p for p in negs if p["dataset"] == ds]
        if not sub:
            continue
        labs = sorted({p["anchor_source_error_label"] for p in sub} | {p["donor_source_error_label"] for p in sub})
        short = {lab: f"L{i + 1}" for i, lab in enumerate(labs)}
        L += [f"**{ds}**: anchor label (rows) × donor label (columns), all splits", ""]
        grid = Counter((p["anchor_source_error_label"], p["donor_source_error_label"]) for p in sub)
        L += [md_table(["anchor \\ donor"] + [short[b] for b in labs],
                       [[f"{short[a]} {a}"] + [grid.get((a, b), "") for b in labs] for a in labs]), ""]

    L += ["## 6. Length", ""]
    if meta.get("tokenizer"):
        L += [f"Tokenizer `{meta['tokenizer']}`; counts include the chat template, system prompt and assistant label. "
              f"Limit {config['model']['max_seq_length']} (the model's max_position_embeddings)."]
        rows = []
        for s in SPLITS:
            lens = sorted(p["n_tokens"] for p in pairs if p["split"] == s)
            if lens:
                rows.append([s, lens[0], lens[len(lens) // 2], lens[int(0.99 * (len(lens) - 1))], lens[-1]])
        L += ["", md_table(["split", "min", "median", "p99", "max"], rows)]
        over = [e for e in manifest if e["reason"].startswith("exceeds")]
        L += ["", f"Pairs dropped for length: {len(over)}.", ""]
    else:
        L += ["Length check skipped (--skip-length-check). The training script still refuses over-length examples.", ""]

    L += ["## 7. Checks", ""]
    L += [md_table(["check", "result", "detail"], [[n, "pass" if ok else "**FAIL**", d] for n, ok, d in checks]), ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


# --- main ------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=None)
    parser.add_argument("--skip-length-check", action="store_true", help="do not load the tokenizer")
    args = parser.parse_args()

    from datetime import datetime, timezone
    import json

    config = load_config(args.config)
    seed = config["seed"]
    inputs = {k: resolve(v) for k, v in config["inputs"].items()}
    for name, path in inputs.items():
        if not path.exists():
            raise SystemExit(f"input {name} not found: {path}")

    pool = read_jsonl(inputs["pool"])
    descriptions = {r["sample_id"]: r for r in read_jsonl(inputs["descriptions"])}
    run_meta = json.loads(inputs["description_run_meta"].read_text(encoding="utf-8"))
    dev_rows = [r for r in read_jsonl(inputs["prompt_dev_manifest"]) if r.get("split") == config["split"]["prompt_dev_split"]]
    dev_keys = {question_key(r["question"]) for r in dev_rows}

    cases = build_cases(pool, descriptions, config)
    remove_duplicates(cases)
    eligible = [c for c in cases if not c["exclusion_reason"]]
    split_info = assign_splits(eligible, config["split"]["ratios"], dev_keys, seed)
    pairs, manifest = make_pairs(eligible, seed)

    prompt = load_prompt(config)
    tokenizer_name = None
    max_len = None
    if not args.skip_length_check:
        from transformers import AutoTokenizer

        tokenizer_name = config["model"]["name"]
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_name, trust_remote_code=True)
        max_len = config["model"]["max_seq_length"]
        pairs = apply_length_limit(pairs, manifest, tokenizer, prompt, max_len)

    checks = run_checks(cases, pairs, max_len)

    out_dir = resolve(config["output"]["data_dir"])
    manifest_dir = resolve(config["output"]["manifest_dir"])
    counts = {}
    for split in SPLITS:
        rows = [p for p in pairs if p["split"] == split]
        write_jsonl(out_dir / f"{split}.jsonl", rows)
        counts[split] = {"pair_records": len(rows), "anchors": len({p["anchor_sample_id"] for p in rows})}

    manifest_fields = (
        "sample_id", "dataset", "benchmark", "question_group_id", "source_question_group_id",
        "source_error_label", "description_status", "processing_status", "description_model",
        "prompt_version", "exclusion_reason", "source_ids",
    )
    split_manifest = []
    for c in cases:
        row = {k: c[k] for k in manifest_fields}
        row["split"] = c.get("split") if not c["exclusion_reason"] else None
        row["prompt_dev_group"] = c.get("prompt_dev_group", False)
        row["error_description"] = c["error_description"]
        row["evidence_quote"] = c["evidence_quote"]
        split_manifest.append(row)
    write_jsonl(manifest_dir / "split_manifest.jsonl", split_manifest)
    write_jsonl(manifest_dir / "pair_manifest.jsonl", manifest)

    meta = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "experiment": config["experiment"],
        "seed": seed,
        "config": {"path": os.path.relpath(Path(config["_config_path"]).resolve(), resolve(".")).replace("\\", "/"),
                   "sha256": config["_config_sha256"]},
        "inputs": {k: {"path": config["inputs"][k], "sha256": sha256_file(p)} for k, p in inputs.items()},
        "description_run": {k: run_meta.get(k) for k in ("run_id", "model", "prompt_version", "prompt_sha256", "generation")},
        "prompt": {"system_sha256": prompt["system_sha256"], "user_sha256": prompt["user_sha256"]},
        "tokenizer": tokenizer_name,
        "max_seq_length": max_len,
        "prompt_dev_sample_ids": sorted(r["sample_id"] for r in dev_rows),
        "cases": len(cases),
        "eligible_cases": len(eligible),
        "question_groups": split_info["groups"],
        "splits": counts,
        "checks_passed": all(ok for _, ok, _ in checks),
    }
    write_json(out_dir / "meta.json", meta)
    write_report(resolve(config["output"]["report"]), config, meta, cases, pairs, manifest, split_info, checks)

    print(f"cases {len(cases)} -> eligible {len(eligible)} in {split_info['groups']} question groups")
    for split in SPLITS:
        print(f"  {split:10s} anchors {counts[split]['anchors']:5d}  pair records {counts[split]['pair_records']:5d}")
    for name, ok, detail in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
    print(f"report -> {resolve(config['output']['report'])}")
    return 0 if meta["checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
