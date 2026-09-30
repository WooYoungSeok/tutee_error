#!/usr/bin/env python3
"""SMOKE ONLY: a tiny RL condition set for plumbing tests before the real conditions exist.

Questions and reference answers are the first GSM8K train rows (pinned parquet); error types rotate over the
adopted types (unit-related only on allowlisted rows). Never train a real run on data/smoke/.

Usage (from newman_experiment/):  python scripts/make_smoke_data.py [--questions 24]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman.common import load_config, read_template, resolve, write_json, write_jsonl  # noqa: E402
from newman.rl_conditions import condition_row, eligible_types  # noqa: E402
from newman.sources import load_gsm8k  # noqa: E402
from newman.taxonomy import Taxonomy  # noqa: E402
from newman.unit_eligibility import Eligibility, load_allowlist  # noqa: E402
from newman.verifier_format import question_group_id, question_key  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--questions", type=int, default=24)
    args = p.parse_args()
    cfg = load_config("configs/data.yaml")
    taxonomy = Taxonomy.load(resolve(cfg["inputs"]["taxonomy"]))
    gsm8k = load_gsm8k(cfg, fetch=True)
    elig = Eligibility(gsm8k, load_allowlist(resolve(cfg["inputs"]["unit_allowlist"])), question_key)
    contract = read_template(cfg["rl_data"]["answer_contract"])
    rows, priv = [], []
    for i, r in enumerate([x for x in gsm8k if x["split"] == "train"][: args.questions]):
        q = {"gsm8k_split": r["split"], "gsm8k_row": r["row"], "question": r["question"], "question_group_id": question_group_id(r["question"]),
             "split": "train", "unit_conversion_eligible": elig.gsm8k_value(r["split"], r["row"])}
        types = eligible_types(q, taxonomy)
        c = condition_row(q, types[i % len(types)], taxonomy)
        rows.append(c)
        priv.append({"condition_id": c["condition_id"], "reference_answer": r["reference_answer"], "answer_contract": contract})
    out = resolve("data/smoke/rl")
    write_jsonl(out / "train.jsonl", rows)
    write_jsonl(out / "test.jsonl", rows[:8])
    write_jsonl(out / "privileged.jsonl", priv)
    write_json(out / "meta.json", {"SMOKE_ONLY": True, "mapping_verified": False, "conditions": len(rows),
                                   "taxonomy_sha256": taxonomy.sha256})
    print(f"wrote {len(rows)} smoke conditions to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
