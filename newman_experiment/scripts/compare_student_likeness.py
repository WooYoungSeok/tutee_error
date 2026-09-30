#!/usr/bin/env python3
"""Direct student-likeness comparison of two evaluated models on the same test conditions (plan 10.3, proposal).

Per condition, rollouts of X and Y that the test verifier B accepted (incorrect and 2/2 `aligned`) are paired by
likeness_comparison.pairing (REQUIRED until confirmed):
  rollout_index   X_k with Y_k when both are B-accepted (same per-rollout seed)
  success_rank    the i-th B-accepted rollout of X with the i-th of Y (in k order), up to the smaller count
The pairwise judge of the RL reward (gpt-5-nano, reasoning low, the approved prompt and MathEDU examples) picks the
more student-like solution; A/B positions are randomized per pair with a seeded draw. Reported next to both models'
B joint success, because only the conditions where both succeed can be compared.

Usage (from newman_experiment/):
  python scripts/compare_student_likeness.py --config configs/student_likeness.yaml \
      --x outputs/<run>/test_eval/epoch-2.0 --y outputs/<run>/test_eval/base
Output: <x>/likeness_vs_<y name>.json
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman import approvals  # noqa: E402
from newman.common import REPO_ROOT, REQUIRED, load_config, load_dotenv, now_iso, read_json, read_jsonl, read_template, resolve, sha256_text, write_json  # noqa: E402


def accepted_by_condition(eval_dir: Path) -> dict[str, dict[int, dict]]:
    out: dict[str, dict[int, dict]] = defaultdict(dict)
    for r in read_jsonl(eval_dir / "rollouts" / "step_000000.jsonl"):
        if r["in_G"]:
            out[r["condition_id"]][int(r["k"])] = r
    return out


def make_pairs(x: dict, y: dict, pairing: str) -> list[tuple[str, dict, dict]]:
    pairs = []
    for cid in sorted(set(x) & set(y)):
        if pairing == "rollout_index":
            pairs += [(cid, x[cid][k], y[cid][k]) for k in sorted(set(x[cid]) & set(y[cid]))]
        elif pairing == "success_rank":
            xs, ys = [x[cid][k] for k in sorted(x[cid])], [y[cid][k] for k in sorted(y[cid])]
            pairs += [(cid, a, b) for a, b in zip(xs, ys)]
        else:
            raise SystemExit(f"likeness_comparison.pairing must be rollout_index or success_rank, got {pairing!r}")
    return pairs


async def judge_all(cfg, pairs, questions, seed):
    from tutee_rl.clients import PairwiseJudge, openai_api_client

    sl = cfg["student_likeness"]
    examples = read_json(resolve(sl["examples"]))["examples"]
    client = openai_api_client(float(sl["request_timeout_s"]), int(sl["concurrency"]), 600.0)
    judge = PairwiseJudge(sl, read_template(cfg["prompts"]["student_likeness_system"]),
                          read_template(cfg["prompts"]["student_likeness_user"]), examples, client)

    async def one(i, cid, rx, ry):
        x_first = int(sha256_text(f"{seed}|likeness|{cid}|{i}")[:8], 16) % 2 == 0
        a, b = (rx, ry) if x_first else (ry, rx)
        res = await judge.compare(questions[cid], a["solution"], b["solution"])
        w = res["winner"]
        winner = "tie" if w == "tie" else ("x" if (w == "A") == x_first else "y")
        return {"condition_id": cid, "x_k": rx["k"], "y_k": ry["k"], "x_position": "A" if x_first else "B", "judge_winner": w,
                "winner": winner, "raw_text": res["raw_text"], "response_id": res["response_id"], "usage": res["usage"]}

    return await asyncio.gather(*[one(i, cid, rx, ry) for i, (cid, rx, ry) in enumerate(pairs)]), judge.prompt_version


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--x", required=True)
    p.add_argument("--y", required=True)
    args = p.parse_args()
    cfg = load_config(args.config)
    pairing = cfg["likeness_comparison"]["pairing"]
    if pairing == REQUIRED:
        print("refusing to start: likeness_comparison.pairing is REQUIRED (open decision)", file=sys.stderr)
        return 2
    pr = cfg["prompts"]
    problems = approvals.problems(["student_likeness_prompt"], {"student_likeness_prompt": [
        pr["student_likeness_system"], pr["student_likeness_user"], cfg["student_likeness"]["examples"]]})
    if problems:
        print("refusing to start:\n  - " + "\n  - ".join(problems), file=sys.stderr)
        return 2
    load_dotenv(REPO_ROOT / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set (tutee_error/.env)", file=sys.stderr)
        return 2
    xdir, ydir = resolve(args.x), resolve(args.y)
    x, y = accepted_by_condition(xdir), accepted_by_condition(ydir)
    questions = {r["condition_id"]: r["question"] for r in read_jsonl(resolve(cfg["paths"]["prepared_dir"]) / "test.jsonl")}
    pairs = make_pairs(x, y, pairing)
    results, prompt_version = asyncio.run(judge_all(cfg, pairs, questions, int(cfg["seed"])))
    n = len(results)
    summary = {"created_at": now_iso(), "timezone": "Asia/Seoul", "x": str(xdir), "y": str(ydir), "pairing": pairing,
               "comparable_pairs": n, "comparable_conditions": len({r["condition_id"] for r in results}),
               "x_win_rate": sum(r["winner"] == "x" for r in results) / n if n else None,
               "y_win_rate": sum(r["winner"] == "y" for r in results) / n if n else None,
               "tie_rate": sum(r["winner"] == "tie" for r in results) / n if n else None,
               "x_b_joint_success": read_json(xdir / "metrics.json")["metrics"]["b_joint_success"],
               "y_b_joint_success": read_json(ydir / "metrics.json")["metrics"]["b_joint_success"],
               "judge": {"model": cfg["student_likeness"]["model"], "reasoning_effort": cfg["student_likeness"].get("reasoning_effort"),
                         "prompt_version": prompt_version},
               "pairs": results}
    out = xdir / f"likeness_vs_{ydir.name}.json"
    write_json(out, summary)
    print(f"{n} comparable pairs: x {summary['x_win_rate']} / y {summary['y_win_rate']} / tie {summary['tie_rate']} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
