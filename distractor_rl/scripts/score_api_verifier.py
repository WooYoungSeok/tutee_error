#!/usr/bin/env python3
"""An API model as the Eedi error-description verifier on already scored test rollouts (user request 2026-10-03:
gpt-5.6-sol on the distractor run's test outputs).

Reuses the gpt-5-nano answer verdicts in <run>/test_eval/<model>/rollouts/step_000000.jsonl. Every `incorrect`
rollout goes to the API model with the exact messages of the Eedi reward/test verifiers
(verifier_sft/verifier_common.build_messages with verifier_sft/prompts/system.txt + user.txt: question, solution,
the condition's misconception description), `samples` calls each (default 2, the RL rule: every call `aligned`),
strict parse (anything but aligned / not_aligned is invalid). Request: reasoning not sent, max_output_tokens 8000.
Answers are appended as they arrive, so a rerun continues. An OpenAI invalid_prompt refusal counts as invalid.

Usage (from rl/, `source env.sh`):
  python ../distractor_rl/scripts/score_api_verifier.py --run ../distractor_rl/outputs/<run> --checkpoints base epoch-2.0
Output: <run>/test_eval_api_verifier_<model>/<checkpoint>/{verdicts_raw.jsonl, metrics.json}, summary.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parent
sys.path[:0] = [str(REPO / "rl" / "src"), str(REPO / "verifier_sft")]

from tutee_rl.common import append_jsonl, load_dotenv, read_jsonl, sha256_file, write_json  # noqa: E402

LABELS = ("aligned", "not_aligned")


def parse(text):
    t = (text or "").strip()
    return t if t in LABELS else "invalid"


async def call_all(items, model, prompt, out_file, done, samples, concurrency, max_tokens):
    import verifier_common as vc
    from tutee_rl.clients import _backoff, classify_error, openai_api_client, responses_call

    client = openai_api_client(600.0, concurrency, 600.0)
    sem = asyncio.Semaphore(concurrency)

    async def one(it, rep):
        msgs = vc.build_messages(prompt, {"question": it["question"], "solution": it["solution"],
                                          "error_description": it["description"]}, with_target=False)
        payload = {"model": model, "max_output_tokens": max_tokens,
                   "input": [{"role": m["role"], "content": [{"type": "input_text", "text": m["content"]}]} for m in msgs]}
        failures = []
        for attempt in range(6):
            async with sem:
                try:
                    api = await responses_call(client, payload, 600.0)
                except Exception as exc:  # noqa: BLE001
                    retryable, kind = classify_error(exc)
                    failures.append(f"{kind}: {str(exc)[:300]}")
                    if not retryable:
                        if "invalid_prompt" in str(exc):
                            append_jsonl(out_file, [{**it["key"], "rep": rep, "raw_output": None, "prediction": "invalid", "flagged": True}])
                            return
                        raise
                    api = None
            if api is not None and (api["status"] == "completed" or api["incomplete_reason"] == "max_output_tokens"):
                append_jsonl(out_file, [{**it["key"], "rep": rep, "raw_output": api["output_text"], "prediction": parse(api["output_text"]),
                                         "truncated": api["incomplete_reason"] == "max_output_tokens", "usage": api["usage"],
                                         "response_id": api["response_id"], "attempts": attempt + 1}])
                return
            if api is not None:
                failures.append(f"incomplete: {api['incomplete_reason']}")
            await _backoff(attempt)
        raise RuntimeError(f"{it['key']} rep {rep} failed: {failures[-3:]}")

    await asyncio.gather(*[one(it, r) for it in items for r in range(samples) if (it["key"]["PairId"], it["key"]["group_pos"], r) not in done])


def summarize(rows, verdicts, samples, n_boot=1000, seed=42):
    by = defaultdict(list)
    for v in verdicts:
        by[(v["PairId"], v["group_pos"])].append(v)
    recs = []
    for r in rows:
        wrong = r["answer_check"]["verdict"] == "incorrect"
        preds = [v["prediction"] for v in sorted(by.get((r["PairId"], r["group_pos"]), []), key=lambda x: x["rep"])] if wrong else []
        if wrong and len(preds) != samples:
            raise SystemExit(f"{r['PairId']} #{r['group_pos']}: {len(preds)} answers, expected {samples}")
        b = r.get("verifier")
        recs.append({"group": r["PairId"].split("__")[0], "wrong": wrong, "matched": bool(r.get("matched_option")),
                     "sol": wrong and all(p == "aligned" for p in preds), "sol_first": wrong and bool(preds) and preds[0] == "aligned",
                     "b": wrong and bool(b) and all(x == "aligned" for x in b["labels"]),
                     "invalid": sum(p == "invalid" for p in preds), "calls": len(preds)})

    def rates(rs):
        n, w = len(rs), sum(x["wrong"] for x in rs)
        mw = [x for x in rs if x["wrong"] and x["matched"]]
        uw = [x for x in rs if x["wrong"] and not x["matched"]]
        return {"rollouts": n, "wrong_rate": w / n,
                "sol_accept_given_wrong": sum(x["sol"] for x in rs) / w if w else None,
                "sol_success": sum(x["sol"] for x in rs) / n, "sol_success_single_call": sum(x["sol_first"] for x in rs) / n,
                "b_accept_given_wrong": sum(x["b"] for x in rs) / w if w else None, "b_success": sum(x["b"] for x in rs) / n,
                "sol_accept_given_wrong_distractor_matched": sum(x["sol"] for x in mw) / len(mw) if mw else None,
                "sol_accept_given_wrong_not_matched": sum(x["sol"] for x in uw) / len(uw) if uw else None,
                "sol_b_disagreement_given_wrong": sum(x["sol"] != x["b"] for x in rs if x["wrong"]) / w if w else None,
                "invalid_sample_rate": sum(x["invalid"] for x in rs) / max(1, sum(x["calls"] for x in rs))}

    out = rates(recs)
    groups = defaultdict(list)
    for x in recs:
        groups[x["group"]].append(x)
    keys, rng, boot = sorted(groups), random.Random(seed), defaultdict(list)
    for _ in range(n_boot):
        r = rates([x for g in (rng.choice(keys) for _ in keys) for x in groups[g]])
        for m in ("sol_success", "sol_accept_given_wrong", "b_success"):
            boot[m].append(r[m])
    out["ci95_question_group_bootstrap"] = {m: [sorted(v)[int(0.025 * n_boot)], sorted(v)[int(0.975 * n_boot) - 1]] for m, v in boot.items()}
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", required=True)
    p.add_argument("--checkpoints", nargs="+", required=True)
    p.add_argument("--model", default="gpt-5.6-sol")
    p.add_argument("--samples", type=int, default=2)
    p.add_argument("--concurrency", type=int, default=64)
    p.add_argument("--max_output_tokens", type=int, default=8000)
    args = p.parse_args()
    import verifier_common as vc

    load_dotenv(REPO / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set")
    sysp, userp = REPO / "verifier_sft/prompts/system.txt", REPO / "verifier_sft/prompts/user.txt"
    prompt = {"system": sysp.read_text(encoding="utf-8"), "user": userp.read_text(encoding="utf-8")}  # as tutee_rl's orchestrator
    rows_meta = {r["PairId"]: r for r in read_jsonl(REPO / "rl/data/prepared/test.jsonl")}
    run = Path(args.run).resolve()
    root = run / f"test_eval_api_verifier_{args.model}"
    summary = {}
    for ck in args.checkpoints:
        rows = read_jsonl(run / "test_eval" / ck / "rollouts" / "step_000000.jsonl")
        items = [{"key": {"PairId": r["PairId"], "group_pos": r["group_pos"]}, "question": rows_meta[r["PairId"]]["problem"],
                  "description": rows_meta[r["PairId"]]["target_misconception_description"], "solution": r["solution"]}
                 for r in rows if r["answer_check"]["verdict"] == "incorrect"]
        out = root / ck
        out.mkdir(parents=True, exist_ok=True)
        raw = out / "verdicts_raw.jsonl"
        done = {(v["PairId"], v["group_pos"], v["rep"]) for v in read_jsonl(raw)} if raw.exists() else set()
        print(f"{ck}: {len(rows)} rollouts, {len(items)} incorrect -> {len(items) * args.samples - len(done)} calls", flush=True)
        asyncio.run(call_all(items, args.model, prompt, raw, done, args.samples, args.concurrency, args.max_output_tokens))
        verdicts = [v for v in read_jsonl(raw) if v["rep"] < args.samples]
        m = summarize(rows, verdicts, args.samples)
        usage = {k: sum((v.get("usage") or {}).get(k) or 0 for v in verdicts) for k in ("input_tokens", "output_tokens")}
        write_json(out / "metrics.json", {"checkpoint": ck, "verifier_model": args.model, "samples": args.samples,
                                          "rule": "incorrect (gpt-5-nano) and every call exactly `aligned`",
                                          "request": {"reasoning_effort": "not sent", "max_output_tokens": args.max_output_tokens},
                                          "prompt_sha256": {"system": sha256_file(sysp), "user": sha256_file(userp)},
                                          "usage_total": usage, "metrics": m})
        summary[ck] = m
        print(f"  {ck}: wrong {m['wrong_rate']:.4f} · sol accept|wrong {m['sol_accept_given_wrong']:.4f} · sol success {m['sol_success']:.4f} "
              f"{[round(x, 4) for x in m['ci95_question_group_bootstrap']['sol_success']]} · B success {m['b_success']:.4f} · usage {usage}", flush=True)
    write_json(root / "summary.json", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
