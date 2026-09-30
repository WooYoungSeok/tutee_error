#!/usr/bin/env python3
"""Fidelity of a served verifier through the exact RL request path (plan 6.3, 8.2).

Replays the SFT test pairs through NewmanVerifierClient (chat template, token-id prompt, stop ids, repetition
penalty 1.0) and reports, kept apart:
  1. greedy (n=1, T=0): should match eval_verifier.py for the same checkpoint;
  2. the reward setting (n=2, T=0.6, both `aligned`): false rejection on positives, false acceptance on negatives
     (overall, same-stage, different-stage), invalid rate, sample disagreement.

Usage (from newman_experiment/, the server up):
  python scripts/check_verifier_server.py --config configs/rl_common.yaml --role a     # reward verifier (:8001)
  python scripts/check_verifier_server.py --config configs/rl_common.yaml --role b     # test verifier (:8002)
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman.common import load_config, now_iso, read_jsonl, rel, resolve, sha256_file, write_json  # noqa: E402
from newman.taxonomy import Taxonomy  # noqa: E402
from newman.verifier_format import load_verifier_prompt  # noqa: E402


async def judge_all(vcfg, prompt, taxonomy, rows, greedy: bool):
    from newman.clients import make_verifier

    cfg = copy.deepcopy(vcfg)
    if greedy:
        cfg.update({"samples": 1, "temperature": 0.0})
    client = make_verifier(cfg, prompt, taxonomy)
    out = await asyncio.gather(*[client.judge(r["question"], r["solution"], r["target_error_id"]) for r in rows])
    return out, client.sampling()


def rates(rows, outs):
    accept = lambda o: all(x == "aligned" for x in o["labels"])  # noqa: E731
    pos = [o for r, o in zip(rows, outs) if r["target"] == "aligned"]
    neg = [(r, o) for r, o in zip(rows, outs) if r["target"] == "not_aligned"]
    labels = [x for o in outs for x in o["labels"]]
    res = {"false_rejection_on_positives": 1 - sum(1 for o in pos if accept(o)) / max(1, len(pos)),
           "false_acceptance_on_negatives": sum(1 for _, o in neg if accept(o)) / max(1, len(neg)),
           "invalid_sample_rate": sum(1 for x in labels if x == "invalid") / max(1, len(labels)),
           "sample_disagreement_rate": sum(1 for o in outs if len(set(o["labels"])) > 1) / max(1, len(outs))}
    for kind in ("same_stage", "different_stage"):
        sub = [o for r, o in neg if r["negative_kind"] == kind]
        res[f"false_acceptance_{kind}"] = sum(1 for o in sub if accept(o)) / len(sub) if sub else None
    return res


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--role", choices=["a", "b"], required=True)
    p.add_argument("--data", default="data/prepared/sft/test.jsonl")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--out", default=None)
    args = p.parse_args()
    cfg = load_config(args.config)
    vcfg = cfg["verifier"] if args.role == "a" else {**cfg["verifier"], **cfg["evaluation"]["verifier"]}
    taxonomy = Taxonomy.load(resolve(cfg["paths"]["taxonomy"]))
    prompt = load_verifier_prompt(cfg["prompts"]["verifier_system"], cfg["prompts"]["verifier_user"])
    data = resolve(args.data)
    rows = read_jsonl(data)[: args.limit] if args.limit else read_jsonl(data)

    greedy, g_sampling = asyncio.run(judge_all(vcfg, prompt, taxonomy, rows, greedy=True))
    g_acc = sum(1 for r, o in zip(rows, greedy) if o["labels"][0] == r["target"]) / len(rows)
    sampled, s_sampling = asyncio.run(judge_all(vcfg, prompt, taxonomy, rows, greedy=False))
    per_sample = sum(1 for r, o in zip(rows, sampled) for x in o["labels"] if x == r["target"]) / sum(len(o["labels"]) for o in sampled)
    result = {"created_at": now_iso(), "role": args.role, "checkpoint": vcfg["checkpoint"], "data": {"path": rel(data), "sha256": sha256_file(data)},
              "rows": len(rows), "greedy": {"sampling": g_sampling, "accuracy": g_acc,
                                           "invalid_rate": sum(1 for o in greedy if o["labels"][0] == "invalid") / len(rows)},
              "reward_setting": {"sampling": s_sampling, "per_sample_accuracy": per_sample, **rates(rows, sampled)}}
    out = resolve(args.out or f"outputs/verifier_server_check_{args.role}{'_limit' + str(args.limit) if args.limit else ''}.json")
    write_json(out, result)
    print(f"greedy accuracy {g_acc:.4f} on {len(rows)} rows")
    for k, v in result["reward_setting"].items():
        if k != "sampling" and v is not None:
            print(f"  {k}: {v:.4f}")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
