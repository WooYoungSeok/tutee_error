#!/usr/bin/env python3
"""Fidelity check of the reward verifier as served for RL.

Replays the verifier's own v2 test split through the exact request path used in the reward
(VerifierClient: SFT chat template, token-id prompt, stop ids, repetition penalty) and reports
  1. greedy accuracy (n=1, T=0)  -> should match the SFT evaluation of the same checkpoint
  2. the reward setting (n=2, T=0.6): per-sample accuracy, both-aligned acceptance on positives
     (false rejection) and on negatives (false acceptance), invalid rate, sample disagreement.

Usage (from rl/, verifier server up):  python scripts/check_verifier_server.py [--config configs/common.yaml] [--limit N]
  --test_verifier checks the held-out half-B verifier used by evaluate.py (scripts/launch_eval_server.sh)
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tutee_rl.common import VERIFIER_SFT_DIR, eval_verifier_cfg, load_config, read_jsonl, resolve, write_json  # noqa: E402


async def run(cfg, rows, greedy: bool):
    from openai import AsyncOpenAI
    from transformers import AutoTokenizer, GenerationConfig

    from tutee_rl.clients import VerifierClient

    vcfg = copy.deepcopy(cfg["verifier"])
    if greedy:
        vcfg.update({"samples": 1, "temperature": 0.0})
    tok = AutoTokenizer.from_pretrained(vcfg["checkpoint"])
    gen = GenerationConfig.from_pretrained(vcfg["checkpoint"])
    eos = gen.eos_token_id
    stop = sorted({tok.eos_token_id, *([eos] if isinstance(eos, int) else eos)})
    rep = float(getattr(gen, "repetition_penalty", None) or 1.0)
    prompt = {"system": resolve(cfg["prompts"]["verifier_system"]).read_text(encoding="utf-8"),
              "user": resolve(cfg["prompts"]["verifier_user"]).read_text(encoding="utf-8"), "ablation": "none"}
    async with AsyncOpenAI(base_url=vcfg["base_url"], api_key="EMPTY", max_retries=0) as oai:
        client = VerifierClient(vcfg, prompt, tok, stop, rep, oai)
        return await asyncio.gather(*[client.judge(r["question"], r["solution"], r["error_description"]) for r in rows]), client.sampling()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="configs/common.yaml")
    parser.add_argument("--data", default=str(VERIFIER_SFT_DIR / "data" / "descriptive_v2" / "test.jsonl"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out", default=None, help="default outputs/verifier_server_check[_test_verifier].json")
    parser.add_argument("--test_verifier", action="store_true")
    args = parser.parse_args()
    cfg = load_config(args.config)
    if args.test_verifier:
        cfg["verifier"] = eval_verifier_cfg(cfg)
    args.out = args.out or f"outputs/verifier_server_check{'_test_verifier' if args.test_verifier else ''}.json"
    rows = read_jsonl(args.data)[: args.limit] if args.limit else read_jsonl(args.data)

    greedy, g_sampling = asyncio.run(run(cfg, rows, greedy=True))
    g_correct = sum(1 for r, o in zip(rows, greedy) if o["labels"][0] == r["target"])
    g_invalid = sum(1 for o in greedy if o["labels"][0] == "invalid")

    sampled, s_sampling = asyncio.run(run(cfg, rows, greedy=False))
    pos = [(r, o) for r, o in zip(rows, sampled) if r["target"] == "aligned"]
    neg = [(r, o) for r, o in zip(rows, sampled) if r["target"] == "not_aligned"]
    accept = lambda o: all(x == "aligned" for x in o["labels"])  # noqa: E731
    labels = [x for o in sampled for x in o["labels"]]
    result = {
        "checkpoint": cfg["verifier"]["checkpoint"], "data": args.data, "rows": len(rows),
        "greedy": {"sampling": g_sampling, "accuracy": g_correct / len(rows), "invalid_rate": g_invalid / len(rows)},
        "reward_setting": {
            "sampling": s_sampling,
            "per_sample_accuracy": sum(1 for (r, o) in zip(rows, sampled) for x in o["labels"] if x == r["target"]) / len(labels),
            "both_aligned_on_positives": sum(1 for _, o in pos if accept(o)) / max(1, len(pos)),
            "false_rejection_on_positives": 1 - sum(1 for _, o in pos if accept(o)) / max(1, len(pos)),
            "false_acceptance_on_negatives": sum(1 for _, o in neg if accept(o)) / max(1, len(neg)),
            "invalid_sample_rate": sum(1 for x in labels if x == "invalid") / len(labels),
            "sample_disagreement_rate": sum(1 for o in sampled if len(set(o["labels"])) > 1) / len(sampled),
        },
    }
    write_json(resolve(args.out), result)
    print(f"greedy accuracy {result['greedy']['accuracy']:.4f} (invalid {result['greedy']['invalid_rate']:.4f}) on {len(rows)} rows")
    for k, v in result["reward_setting"].items():
        if k != "sampling":
            print(f"  {k}: {v:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
