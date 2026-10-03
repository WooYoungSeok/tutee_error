#!/usr/bin/env python3
"""An API model as the verifier of already graded generations (user request 2026-10-02: gpt-5.6-sol as verifier of
the API baselines' RL-test outputs, beside the verifier-A and verifier-B scores).

Input: a scored evaluation folder of evaluate_student.py (<name>/rollouts/step_000000.jsonl), whose gpt-5-nano answer
verdicts are reused as they are. Every `incorrect` solution goes to the API verifier with the trained verifiers'
exact messages (verifier_messages: system = verifier system prompt, user = rendered user prompt, same roles, nothing
added), `samples` independent calls each (default 2, the A/B rule: success needs every call `aligned`), strict parse
(anything but `aligned` / `not_aligned` is invalid). Request settings = configs/verifier_common.yaml api_verifier (the
2026-10-01 API verifier comparison): reasoning not sent, max_output_tokens 8000. Each answer is appended as soon as it
returns, so a rerun continues.

Usage (from newman_experiment/, `source env.sh`):
  python scripts/score_generations_api_verifier.py --scored outputs/api_baselines_prelim_verifierA/test_eval/api_gpt-5.6-sol \
      --model gpt-5.6-sol --out outputs/api_baselines_verifier_gpt-5.6-sol/api_gpt-5.6-sol
Output: <out>/{verdicts_raw.jsonl, metrics.json}
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman.common import (  # noqa: E402
    REPO_ROOT,
    append_jsonl,
    git_state,
    load_config,
    load_dotenv,
    now_iso,
    read_jsonl,
    rel,
    resolve,
    sha256_file,
    sha256_text,
    write_json,
)
from newman.taxonomy import Taxonomy  # noqa: E402
from newman.verifier_format import load_verifier_prompt, parse_prediction, verifier_messages  # noqa: E402

ALIGNED = "aligned"


async def run(av, model, items, prompt, taxonomy, out_file: Path, done: set, concurrency: int) -> None:
    from tutee_rl.clients import RewardExecutionError, _backoff, classify_error, openai_api_client, responses_call

    client = openai_api_client(float(av["request_timeout_s"]), concurrency, 600.0)
    sem = asyncio.Semaphore(concurrency)

    async def one(it, rep):
        msgs = verifier_messages(prompt, taxonomy, it["question"], it["solution"], it["source_error_id"])
        payload = {"model": model,
                   "input": [{"role": m["role"], "content": [{"type": "input_text", "text": m["content"]}]} for m in msgs],
                   "max_output_tokens": int(av["max_output_tokens"])}
        if av.get("reasoning_effort"):
            payload["reasoning"] = {"effort": av["reasoning_effort"]}
        failures = []
        for attempt in range(int(av["max_attempts"])):
            async with sem:
                try:
                    api = await responses_call(client, payload, float(av["request_timeout_s"]))
                except Exception as exc:  # noqa: BLE001
                    retryable, kind = classify_error(exc)
                    failures.append(f"{kind}: {str(exc)[:300]}")
                    if not retryable:
                        if "invalid_prompt" in str(exc):  # same rule as the reward (user 2026-10-02): flagged -> not passed
                            append_jsonl(out_file, [{"condition_id": it["condition_id"], "k": it["k"], "rep": rep, "raw_output": None,
                                                     "prediction": "invalid", "flagged": True, "failures": failures}])
                            return
                        raise RewardExecutionError(f"{model} fatal error {kind}: {exc}") from exc
                    api = None
            if api is not None and (api["status"] == "completed" or api["incomplete_reason"] == "max_output_tokens"):
                append_jsonl(out_file, [{"condition_id": it["condition_id"], "k": it["k"], "rep": rep,
                                         "messages_sha256": sha256_text(json.dumps([[m["role"], m["content"]] for m in msgs], ensure_ascii=False)),
                                         "raw_output": api["output_text"], "prediction": parse_prediction(api["output_text"]),
                                         "truncated": api["incomplete_reason"] == "max_output_tokens", "usage": api["usage"],
                                         "response_id": api["response_id"], "request_id": api["request_id"], "attempts": attempt + 1}])
                return
            if api is not None:
                failures.append(f"incomplete: {api['incomplete_reason']}")
            await _backoff(attempt)
        raise RewardExecutionError(f"{model} {it['condition_id']} rep {rep} failed: {failures[-3:]}")

    await asyncio.gather(*[one(it, rep) for it in items for rep in range(it["samples"]) if (it["condition_id"], it["k"], rep) not in done])


def summarize(rows, verdicts, samples, n_boot=1000, seed=42):
    by = defaultdict(list)
    for v in verdicts:
        by[(v["condition_id"], v["k"])].append(v)
    recs = []
    for r in rows:
        wrong = r["answer_check"]["verdict"] == "incorrect"
        vs = sorted(by.get((r["condition_id"], r["k"]), []), key=lambda x: x["rep"]) if wrong else []
        if wrong and len(vs) != samples:
            raise SystemExit(f"{r['condition_id']} k={r['k']}: {len(vs)} verifier answers, expected {samples}")
        preds = [v["prediction"] for v in vs]
        recs.append({"group": r["question_group_id"], "stage": r["newman_stage"], "type": r["source_error_id"], "wrong": wrong,
                     "accept_all": wrong and all(p == ALIGNED for p in preds), "accept_first": wrong and preds[0] == ALIGNED if preds else False,
                     "invalid": sum(p not in ("aligned", "not_aligned") for p in preds), "calls": len(preds),
                     "disagree": wrong and len(set(preds)) > 1, "flagged": sum(bool(v.get("flagged")) for v in vs)})

    def rates(rs):
        n, w = len(rs), sum(x["wrong"] for x in rs)
        return {"rollouts": n, "wrong_rate": w / n, "accept_given_wrong": sum(x["accept_all"] for x in rs) / w if w else None,
                "joint_success": sum(x["accept_all"] for x in rs) / n,
                "joint_success_single_call": sum(x["accept_first"] for x in rs) / n,
                "sample_disagreement_given_wrong": sum(x["disagree"] for x in rs) / w if w else None,
                "invalid_sample_rate": sum(x["invalid"] for x in rs) / max(1, sum(x["calls"] for x in rs)),
                "flagged_samples": sum(x["flagged"] for x in rs)}

    out = rates(recs)
    out["by_stage"] = {s: rates([x for x in recs if x["stage"] == s]) for s in sorted({x["stage"] for x in recs})}
    out["by_type"] = {t: rates([x for x in recs if x["type"] == t]) for t in sorted({x["type"] for x in recs})}
    types = [v["joint_success"] for v in out["by_type"].values()]
    out["joint_success_macro_over_types"] = sum(types) / len(types)
    groups = defaultdict(list)
    for x in recs:
        groups[x["group"]].append(x)
    keys, rng, boot = sorted(groups), random.Random(seed), defaultdict(list)
    for _ in range(n_boot):
        sample = [x for g in (rng.choice(keys) for _ in keys) for x in groups[g]]
        r = rates(sample)
        for m in ("wrong_rate", "accept_given_wrong", "joint_success", "joint_success_single_call"):
            boot[m].append(r[m])
    out["ci95"] = {m: [sorted(v)[int(0.025 * n_boot)], sorted(v)[int(0.975 * n_boot) - 1]] for m, v in boot.items()}
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--scored", required=True, help="evaluate_student.py output folder of one model (has rollouts/step_000000.jsonl)")
    p.add_argument("--model", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--rl_config", default="configs/student_likeness.yaml")
    p.add_argument("--verifier_config", default="configs/verifier_common.yaml")
    p.add_argument("--samples", type=int, default=2)
    p.add_argument("--concurrency", type=int, default=64)
    args = p.parse_args()
    rl, vc = load_config(args.rl_config), load_config(args.verifier_config)
    av = vc["api_verifier"]
    if args.model not in av["models"]:
        raise SystemExit(f"{args.model} is not in api_verifier.models {av['models']}")
    load_dotenv(REPO_ROOT / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set (tutee_error/.env)")
    taxonomy = Taxonomy.load(resolve(rl["paths"]["taxonomy"]))
    prompt = load_verifier_prompt(rl["prompts"]["verifier_system"], rl["prompts"]["verifier_user"])
    scored = resolve(args.scored)
    rows = read_jsonl(scored / "rollouts" / "step_000000.jsonl")
    questions = {r["condition_id"]: r["question"] for r in read_jsonl(resolve(rl["paths"]["prepared_dir"]) / "test.jsonl")}
    items = [{**r, "question": questions[r["condition_id"]], "samples": args.samples} for r in rows if r["answer_check"]["verdict"] == "incorrect"]
    out = resolve(args.out)
    out.mkdir(parents=True, exist_ok=True)
    raw = out / "verdicts_raw.jsonl"
    done = {(v["condition_id"], v["k"], v["rep"]) for v in read_jsonl(raw)} if raw.exists() else set()
    started = now_iso()
    asyncio.run(run(av, args.model, items, prompt, taxonomy, raw, done, args.concurrency))
    verdicts = [v for v in read_jsonl(raw) if v["rep"] < args.samples]
    metrics = summarize(rows, verdicts, args.samples)
    usage = {k: sum((v.get("usage") or {}).get(k) or 0 for v in verdicts) for k in ("input_tokens", "output_tokens")}
    write_json(out / "metrics.json", {
        "created_at": now_iso(), "started_at": started, "timezone": "Asia/Seoul", "verifier_model": args.model,
        "scored_from": rel(scored), "answer_verdicts": "reused from the scored folder (gpt-5-nano, reasoning low)",
        "rule": f"{args.samples} calls per incorrect solution, success = every call exactly `aligned`",
        "request": {"max_output_tokens": av["max_output_tokens"], "reasoning_effort": av["reasoning_effort"] or "not sent (model default)",
                    "temperature": "not sent", "input": "verifier_messages(...) as role messages, nothing added"},
        "prompt_sha256": {"system": sha256_file(resolve(rl["prompts"]["verifier_system"])), "user": sha256_file(resolve(rl["prompts"]["verifier_user"]))},
        "taxonomy_sha256": taxonomy.sha256, "usage_total": usage, "git": git_state(), "metrics": metrics})
    m = metrics
    print(f"{args.model} verifier on {scored.name}: wrong {m['wrong_rate']:.4f} · accept|wrong {m['accept_given_wrong']:.4f} · "
          f"success {m['joint_success']:.4f} {m['ci95']['joint_success']} · single-call {m['joint_success_single_call']:.4f} · usage {usage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
