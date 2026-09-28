#!/usr/bin/env python3
"""Split a fixed train split into two question-group-disjoint halves (A, B) for independent verifiers.

Half A trains one verifier; half B is kept for a separate verifier (e.g. a different base model that
evaluates the RL-trained main model), so the two never share a training question or error description.

  1. anchors = the source config's train positives (one per kept case);
  2. question groups are stratified as in the original split (dataset | benchmark | normalized label of the
     group's most frequent case); inside each stratum the sorted groups are permuted with one
     numpy.random.RandomState(seed) and the first half goes to A. An odd stratum gives its extra group to
     A and B in turn;
  3. positives are the source positives unchanged; each anchor's negative is re-drawn inside its own half
     with the original rule (same dataset, different normalized label, different question group);
  4. validation.jsonl and test.jsonl are copied byte for byte from the source data directory.

Usage (from verifier_sft/):
    python split_train_halves.py --config config/descriptive_verifier_v2_halfA.json config/descriptive_verifier_v2_halfB.json
Both half configs must name the same `train_half.source_config` and seed, and halves A and B.
"""

from __future__ import annotations

import argparse
import math
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from prepare_descriptive_pairs import apply_length_limit, group_stratum, make_pairs  # noqa: E402
from verifier_common import (  # noqa: E402
    ALIGNED,
    NOT_ALIGNED,
    label_key,
    load_config,
    load_prompt,
    read_jsonl,
    resolve,
    sha256_file,
    write_json,
    write_jsonl,
)

HALVES = ("A", "B")


def anchor_cases(train_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rebuild the train cases from the positive rows (a positive carries the anchor's own description)."""
    cases = []
    for r in train_rows:
        if r["target"] != ALIGNED:
            continue
        cases.append({
            "sample_id": r["anchor_sample_id"],
            "split": "train",
            "dataset": r["dataset"],
            "benchmark": r["benchmark"],
            "question_group_id": r["question_group_id"],
            "source_error_label": r["anchor_source_error_label"],
            "question": r["question"],
            "solution": r["solution"],
            "error_description": r["error_description"],
        })
    return sorted(cases, key=lambda c: c["sample_id"])


def assign_halves(cases: list[dict[str, Any]], seed: int) -> dict[str, str]:
    import numpy as np

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in cases:
        groups[c["question_group_id"]].append(c)
    strata: dict[str, list[str]] = defaultdict(list)
    for g, cs in groups.items():
        strata[group_stratum(cs)].append(g)
    rng = np.random.RandomState(seed)
    half_of: dict[str, str] = {}
    extra_to_a = True
    for stratum in sorted(strata):
        gids = sorted(strata[stratum])
        order = [gids[i] for i in rng.permutation(len(gids))]
        n_a = len(order) // 2
        if len(order) % 2:
            n_a += 1 if extra_to_a else 0
            extra_to_a = not extra_to_a
        for i, g in enumerate(order):
            half_of[g] = "A" if i < n_a else "B"
    return half_of


def run_checks(source_rows, half_cases, half_pairs, max_len) -> list[tuple[str, bool, str]]:
    src_pos = {r["anchor_sample_id"]: r for r in source_rows if r["target"] == ALIGNED}
    anchors = {h: {c["sample_id"] for c in half_cases[h]} for h in HALVES}
    groups = {h: {c["question_group_id"] for c in half_cases[h]} for h in HALVES}
    by_id = {c["sample_id"]: (h, c) for h in HALVES for c in half_cases[h]}
    checks = [
        ("halves together are exactly the source train anchors", anchors["A"] | anchors["B"] == set(src_pos), ""),
        ("no anchor in both halves", not anchors["A"] & anchors["B"], ""),
        ("no question group in both halves", not groups["A"] & groups["B"], f"{len(groups['A'] & groups['B'])} shared"),
    ]
    for h in HALVES:
        pairs = half_pairs[h]
        negs = [p for p in pairs if p["target"] == NOT_ALIGNED]
        poss = [p for p in pairs if p["target"] == ALIGNED]
        per = Counter((p["anchor_sample_id"], p["target"]) for p in pairs)
        checks += [
            (f"[{h}] every anchor has one positive and one negative",
             all(per[(a, ALIGNED)] == 1 and per[(a, NOT_ALIGNED)] == 1 for a in anchors[h]), ""),
            (f"[{h}] positives identical to the source positives", all(p == src_pos[p["anchor_sample_id"]] for p in poss), ""),
            (f"[{h}] negative donor from the same half", all(by_id[p["donor_sample_id"]][0] == h for p in negs), ""),
            (f"[{h}] negative donor from the same dataset", all(by_id[p["donor_sample_id"]][1]["dataset"] == p["dataset"] for p in negs), ""),
            (f"[{h}] negative donor label differs (normalized)",
             all(label_key(p["donor_source_error_label"]) != label_key(p["anchor_source_error_label"]) for p in negs), ""),
            (f"[{h}] negative donor from a different question group",
             all(p["donor_question_group_id"] != p["question_group_id"] for p in negs), ""),
            (f"[{h}] no pair over {max_len} tokens", all(p["n_tokens"] <= max_len for p in pairs), ""),
        ]
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", nargs=2, required=True, help="the half-A and half-B configs")
    args = parser.parse_args()

    configs = {}
    for path in args.config:
        cfg = load_config(path)
        configs[cfg["train_half"]["half"]] = cfg
    if set(configs) != set(HALVES):
        raise SystemExit(f"need one config for each half {HALVES}, got {sorted(configs)}")
    ha, hb = configs["A"]["train_half"], configs["B"]["train_half"]
    if ha["source_config"] != hb["source_config"] or ha["seed"] != hb["seed"]:
        raise SystemExit("the two half configs disagree on source_config or seed")
    seed = ha["seed"]
    source = load_config(resolve(ha["source_config"]))
    src_dir = resolve(source["output"]["data_dir"])
    source_rows = read_jsonl(src_dir / "train.jsonl")

    cases = anchor_cases(source_rows)
    half_of = assign_halves(cases, seed)
    half_cases = {h: [c for c in cases if half_of[c["question_group_id"]] == h] for h in HALVES}

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(source["model"]["name"], trust_remote_code=True)
    max_len = source["model"]["max_seq_length"]
    prompt = load_prompt(source)
    half_pairs, half_manifest = {}, {}
    for h in HALVES:
        pairs, manifest = make_pairs(half_cases[h], seed)
        half_pairs[h] = apply_length_limit(pairs, manifest, tokenizer, prompt, max_len)
        half_manifest[h] = manifest
    checks = run_checks(source_rows, half_cases, half_pairs, max_len)
    ok = all(c[1] for c in checks)

    created = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    source_hashes = {f"{s}.jsonl": sha256_file(src_dir / f"{s}.jsonl") for s in ("train", "validation", "test")}
    counts = {}
    for h in HALVES:
        cfg = configs[h]
        out = resolve(cfg["output"]["data_dir"])
        write_jsonl(out / "train.jsonl", half_pairs[h])
        for s in ("validation", "test"):
            out.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src_dir / f"{s}.jsonl", out / f"{s}.jsonl")
        write_jsonl(resolve(cfg["output"]["manifest_dir"]) / "pair_manifest.jsonl", half_manifest[h])
        counts[h] = {
            "anchors": len(half_cases[h]),
            "pair_records": len(half_pairs[h]),
            "question_groups": len({c["question_group_id"] for c in half_cases[h]}),
            "by_dataset": dict(sorted(Counter(c["dataset"] for c in half_cases[h]).items())),
        }
        write_json(out / "meta.json", {
            "created_at_utc": created,
            "experiment": cfg["experiment"],
            "train_half": cfg["train_half"],
            "config": {"path": cfg["_config_path"], "sha256": cfg["_config_sha256"]},
            "source": {"config": ha["source_config"], "data_dir": source["output"]["data_dir"], "sha256": source_hashes},
            "other_half": "B" if h == "A" else "A",
            "counts": counts[h],
            "validation_and_test": "byte-identical copies of the source validation.jsonl and test.jsonl",
            "tokenizer": source["model"]["name"],
            "max_seq_length": max_len,
            "checks_passed": ok,
        })

    assign_rows = [
        {"sample_id": c["sample_id"], "half": half_of[c["question_group_id"]], "question_group_id": c["question_group_id"],
         "dataset": c["dataset"], "benchmark": c["benchmark"], "source_error_label": c["source_error_label"]}
        for c in cases
    ]
    shared_dir = resolve(ha["assignment_dir"])
    write_jsonl(shared_dir / "half_assignment.jsonl", assign_rows)

    L = ["# Train halves — independent verifiers", ""]
    L += [f"Created (UTC): {created} · seed {seed} · source `{ha['source_config']}` (train sha256 "
          f"`{source_hashes['train.jsonl'][:16]}`)", ""]
    L += ["Half A trains the Qwen2.5-Math-7B-Instruct verifier; half B is reserved for a separate verifier. "
          "Question groups are disjoint, and every negative's description comes from the same half, so the halves "
          "share no training question or error description. Validation and test are the source files, unchanged.", ""]
    L += ["| half | anchors | pair records | question groups | " + " | ".join(sorted(counts["A"]["by_dataset"])) + " |",
          "|" + " --- |" * (4 + len(counts["A"]["by_dataset"]))]
    for h in HALVES:
        c = counts[h]
        L += [f"| {h} | {c['anchors']} | {c['pair_records']} | {c['question_groups']} | "
              + " | ".join(str(c["by_dataset"].get(d, 0)) for d in sorted(counts["A"]["by_dataset"])) + " |"]
    L += ["", "## Anchors per source label", "",
          "| dataset | label | A | B |", "| --- | --- | --- | --- |"]
    lab = Counter((half_of[c["question_group_id"]], c["dataset"], c["source_error_label"]) for c in cases)
    for ds, label in sorted({(c["dataset"], c["source_error_label"]) for c in cases}):
        L += [f"| {ds} | {label} | {lab[('A', ds, label)]} | {lab[('B', ds, label)]} |"]
    L += ["", "## Checks", "", "| check | result |", "| --- | --- |"]
    L += [f"| {n} | {'pass' if k else '**FAIL**'} |" for n, k, _ in checks]
    report = shared_dir / "split_report.md"
    report.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")

    for h in HALVES:
        print(f"half {h}: {counts[h]}")
    for n, k, d in checks:
        print(f"  [{'ok' if k else 'FAIL'}] {n} {d if not k else ''}")
    print(f"report -> {report}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
