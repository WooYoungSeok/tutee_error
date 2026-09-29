#!/usr/bin/env python3
"""Turn the audited same-question candidates into SFT and evaluation files (strict verifier).

sft_data.half: "A" or "B" (the rows of that train+validation half, for a half verifier) or "all" (both
halves, i.e. every non-test group, for the verifier trained on the whole v2 train).

The audit verdict is the target (researcher decision 2026-09-29: no human review after the pilot);
`unclear` rows are dropped. Negatives are only audited not_aligned rows: the cross-question negatives
of the v2 data are not used (the model being trained further has already seen them).

sft_data.positives chooses the positives of train.jsonl:
  audited_only   audited aligned rows of the half (own + cross) — only same-question contrast rows
  existing_all   every positive of sft_data.existing_train (own rows audited not_aligned are flipped,
                 unclear own rows dropped) + audited aligned cross rows

Outputs (output.data_dir):
  train.jsonl           the half's audited rows (v2 train and validation groups of that half)
  contrast_test.jsonl   audited test-split rows: the same-question contrast evaluation set
  test.jsonl            copy of the v2 test file (the original evaluation)
  test_augmented.jsonl  the v2 test rows unchanged + the audited not_aligned cross rows of the test split
                        (same-question negatives); own rows are not added (they repeat v2 positives).
                        row_source tells the three kinds apart for the per-kind metrics
  meta.json, and output.report (counts, 2×2 blocks)

Row format is the v2 pair format, so train_descriptive_verifier.py and eval_descriptive_verifier.py
(--split contrast_test) run unchanged. anchor_sample_id is the candidate id (one row per "anchor"), so
v2's pair accuracy is not computed on these files; solution/description ids are kept in their own fields.

Usage (from verifier_sft/):
    python build_contrast_sft.py --config config/strict_contrast_v1_halfA_cont.json
"""

from __future__ import annotations

import argparse
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verifier_common import (  # noqa: E402
    ALIGNED,
    LABELS,
    NOT_ALIGNED,
    load_config,
    read_jsonl,
    resolve,
    sha256_file,
    text_key,
    write_json,
    write_jsonl,
)


def audited_row(a: dict[str, Any], split: str) -> dict[str, Any]:
    return {
        "pair_id": a["candidate_id"],
        "split": split,
        "target": a["verdict"],
        "anchor_sample_id": a["candidate_id"],
        "donor_sample_id": a["description_sample_id"],
        "question_group_id": a["question_group_id"],
        "donor_question_group_id": a["question_group_id"],
        "dataset": a["dataset"],
        "benchmark": a["benchmark"],
        "anchor_source_error_label": a["solution_source_label"],
        "donor_source_error_label": a["description_source_label"],
        "question": a["question"],
        "solution": a["solution"],
        "error_description": a["error_description"],
        "row_source": f"audited_{a['origin']}",
        "solution_sample_id": a["solution_sample_id"],
        "description_sample_id": a["description_sample_id"],
        "same_source_label": a["same_source_label"],
    }


def existing_positive(r: dict[str, Any]) -> dict[str, Any]:
    return {**r, "anchor_sample_id": r["pair_id"], "row_source": "existing_positive",
            "solution_sample_id": r["anchor_sample_id"], "description_sample_id": r["donor_sample_id"],
            "same_source_label": True}


def in_half(a: dict[str, Any], half: str) -> bool:
    return a["half"] != "test" if half == "all" else a["half"] == half


def build_train(audits: list[dict[str, Any]], half: str, positives: str, existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mine = [a for a in audits if in_half(a, half) and a["verdict"] in LABELS]
    if positives == "audited_only":
        rows = [audited_row(a, "train") for a in mine]
    elif positives == "existing_all":
        own = {a["solution_sample_id"]: a for a in audits if in_half(a, half) and a["origin"] == "own"}
        rows = []
        for r in existing:
            if r["target"] != ALIGNED:
                continue
            a = own.get(r["anchor_sample_id"])
            if a is None:  # solution without a sibling in its question group: not audited, kept as before
                rows.append(existing_positive(r))
            elif a["verdict"] in LABELS:  # audited own row: the verdict wins
                rows.append(audited_row(a, "train"))
        rows += [audited_row(a, "train") for a in mine if a["origin"] != "own"]
    else:
        raise SystemExit(f"unknown sft_data.positives {positives!r}")
    return sorted(rows, key=lambda r: r["pair_id"])


def contrast_blocks(rows: list[dict[str, Any]]) -> int:
    """2×2 blocks: solutions s1, s2 of one question with (s1,d1) and (s2,d2) aligned, (s1,d2) and (s2,d1) not_aligned."""
    target = {(r["solution_sample_id"], r["description_sample_id"]): r["target"] for r in rows}
    by_group: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        by_group[r["question_group_id"]].add(r["solution_sample_id"])
    n = 0
    for sols in by_group.values():
        s = sorted(sols)
        for i, a in enumerate(s):
            for b in s[i + 1:]:
                if (target.get((a, a)) == target.get((b, b)) == ALIGNED
                        and target.get((a, b)) == target.get((b, a)) == NOT_ALIGNED):
                    n += 1
    return n


def describe(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "rows": len(rows),
        "targets": dict(Counter(r["target"] for r in rows)),
        "by_source": {f"{k[0]} → {k[1]}": v for k, v in sorted(Counter((r["row_source"], r["target"]) for r in rows).items())},
        "question_groups": len({r["question_group_id"] for r in rows}),
        "by_dataset": dict(Counter(r["dataset"] for r in rows)),
        "contrast_2x2_blocks": contrast_blocks(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    cfg = config["sft_data"]

    audits_path = resolve(cfg["audits"])
    audits = read_jsonl(audits_path)
    existing = read_jsonl(resolve(cfg["existing_train"]))
    train = build_train(audits, cfg["half"], cfg["positives"], existing)
    contrast = sorted((audited_row(a, "test") for a in audits if a["split"] == "test" and a["verdict"] in LABELS),
                      key=lambda r: r["pair_id"])
    v2_rows = [{**r, "row_source": "v2_positive" if r["target"] == ALIGNED else "v2_negative_other_question"}
               for r in read_jsonl(resolve(cfg["v2_test"]))]
    added = [r for r in contrast if r["row_source"] == "audited_cross_same_question" and r["target"] == NOT_ALIGNED]
    augmented = v2_rows + added

    train_groups = {r["question_group_id"] for r in train}
    contrast_groups = {r["question_group_id"] for r in contrast}
    v2_test = resolve(cfg["v2_test"])
    v2_test_groups = {r["question_group_id"] for r in v2_rows}
    v2_keys = {(text_key(r["question"]), text_key(r["solution"]), text_key(r["error_description"])) for r in v2_rows}
    other_half = {a["question_group_id"] for a in audits if a["half"] != "test" and not in_half(a, cfg["half"])}
    checks = [
        ("no train question group in the contrast test", not train_groups & contrast_groups),
        ("no train question group in the v2 test", not train_groups & v2_test_groups),
        ("no train question group from the other half", not train_groups & other_half),
        ("train negatives are audited rows only",
         all(r["row_source"].startswith("audited") for r in train if r["target"] == NOT_ALIGNED)),
        ("pair ids unique", len({r["pair_id"] for r in train}) == len(train)),
        ("augmented test: added rows repeat no v2 test row",
         not any((text_key(r["question"]), text_key(r["solution"]), text_key(r["error_description"])) in v2_keys for r in added)),
        ("augmented test: added rows are negatives on v2 test solutions",
         {r["solution_sample_id"] for r in added} <= {r["anchor_sample_id"] for r in v2_rows if r["target"] == ALIGNED}),
        ("augmented test: pair ids unique", len({r["pair_id"] for r in augmented}) == len(augmented)),
    ]
    ok = all(c[1] for c in checks)

    out = resolve(config["output"]["data_dir"])
    write_jsonl(out / "train.jsonl", train)
    write_jsonl(out / "contrast_test.jsonl", contrast)
    shutil.copyfile(v2_test, out / "test.jsonl")
    write_jsonl(out / "test_augmented.jsonl", augmented)
    dropped = Counter((a["split"] if a["split"] == "test" else a["half"], a["origin"]) for a in audits if a["verdict"] == "unclear")
    meta = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "config": {"path": config["_config_path"], "sha256": config["_config_sha256"]},
        "sft_data": cfg,
        "inputs": {"audits": sha256_file(audits_path), "existing_train": sha256_file(resolve(cfg["existing_train"])),
                   "v2_test": sha256_file(v2_test)},
        "train": describe(train),
        "contrast_test": describe(contrast),
        "test_augmented": {"rows": len(augmented), "by_source": dict(Counter(f"{r['row_source']} → {r['target']}" for r in augmented))},
        "unclear_dropped": {f"{k[0]}|{k[1]}": v for k, v in dropped.items()},
        "checks": {name: passed for name, passed in checks},
        "checks_passed": ok,
    }
    write_json(out / "meta.json", meta)

    L = [f"# SFT data — {config['experiment']}", "", f"Created (UTC): {meta['created_at_utc']} · positives `{cfg['positives']}` · "
         f"half {cfg['half']} · audits sha256 `{meta['inputs']['audits'][:16]}`", "",
         "Targets are the gpt-5.6-sol audit verdicts (no human review); unclear rows dropped.", ""]
    for name in ("train", "contrast_test"):
        d = meta[name]
        L += [f"## {name}", "", f"rows {d['rows']} · targets {d['targets']} · question groups {d['question_groups']} · "
              f"datasets {d['by_dataset']} · 2×2 contrast blocks {d['contrast_2x2_blocks']}", "",
              "| row source → target | rows |", "| --- | --- |"]
        L += [f"| {k} | {v} |" for k, v in d["by_source"].items()] + [""]
    L += ["## test_augmented", "", f"rows {len(augmented)}: the v2 test unchanged + the audited same-question negatives "
          "of the test split", "", "| row source → target | rows |", "| --- | --- |"]
    L += [f"| {k} | {v} |" for k, v in meta["test_augmented"]["by_source"].items()] + [""]
    L += [f"Unclear rows dropped: {meta['unclear_dropped'] or 0}", "", "## Checks", "", "| check | result |", "| --- | --- |"]
    L += [f"| {n} | {'pass' if p else '**FAIL**'} |" for n, p in checks]
    report = resolve(config["output"]["report"])
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")

    for name in ("train", "contrast_test", "test_augmented"):
        print(f"{name}: {meta[name]}")
    for n, p in checks:
        print(f"  [{'ok' if p else 'FAIL'}] {n}")
    print(f"-> {out} · report {report}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
