#!/usr/bin/env python3
"""Test evaluation of Student snapshots, the base model and API baselines on the same (Q, N, E) conditions (plan 10).

1. --stage generate: one vLLM offline engine per checkpoint on its own GPU; G = 8 rollouts per test condition with
   the training sampling (T 1.0, top_p 1.0, top_k off, repetition 1.0, 1,024 tokens) and per-rollout seeds
   sha256(seed|condition_id|k) shared by every model. API baselines: scripts/generate_api_baseline.py.
2. --stage score: the training reward path with the verifier swapped for the held-out test verifier B (n=2, T=0.6,
   both `aligned`); gpt-5-nano (reasoning low) grades every rollout. With evaluation.with_reward_verifier, A judges the
   same wrong solutions as a diagnostic (A acceptance, A/B disagreement); it never enters a score.
3. summary: wrong rate, B acceptance given wrong, B joint success, A acceptance, A/B disagreement, by type / stage /
   unit eligibility (micro, macro over types), zero-success conditions, diversity and distinct solutions among the
   successes, truncation, verifier invalid samples; paired question-group bootstrap against `base`.
Checkpoint choice (user decision 2026-09-30): the snapshot with the highest evaluation.select_metric (mean reward
with verifier B) on --split validation; the test summary records that choice and reports every model.

Usage (from newman_experiment/; `bash scripts/launch_eval_servers.sh CONFIG` before scoring):
  python scripts/evaluate_student.py --config configs/student_likeness.yaml --run outputs/<run> --split validation
  python scripts/evaluate_student.py --config configs/student_likeness.yaml --run outputs/<run> --include_base
  python scripts/evaluate_student.py --config configs/student_likeness.yaml --out outputs/<run>/test_eval --api_dirs outputs/api_baselines/<model>
Outputs: <out>/<name>/{completions.jsonl, generation_meta.json, rollouts/, metrics.json}, <out>/summary.json
         (out = <run>/test_eval for test, <run>/eval_validation for validation)
"""

from __future__ import annotations

import argparse
import copy
import os
import shutil
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman import approvals, preflight  # noqa: E402
from newman.common import (  # noqa: E402
    NEWMAN_ROOT,
    REPO_ROOT,
    REQUIRED,
    git_state,
    load_config,
    load_dotenv,
    now_iso,
    read_json,
    read_jsonl,
    rel,
    resolve,
    sha256_text,
    write_json,
    write_jsonl,
)
from newman.metrics import group_counts, paired_bootstrap, student_metrics  # noqa: E402
from newman.taxonomy import Taxonomy  # noqa: E402
from newman.verifier_format import load_student_template, student_messages  # noqa: E402

SELECT_METRICS = ("b_joint_success", "reward_total_mean")
ROLE_NAMES = {"joint_success": "b_joint_success", "accept_given_wrong": "b_accept_given_wrong",
              "secondary_accept_given_wrong": "a_accept_given_wrong", "disagreement_given_wrong": "ab_disagreement_given_wrong",
              "verifier_invalid_sample_rate": "b_invalid_sample_rate"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True, help="the experiment config the run was trained with")
    p.add_argument("--override", action="append", default=[])
    p.add_argument("--run", default=None, help="training run dir: every epoch_checkpoints/epoch-K is evaluated")
    p.add_argument("--checkpoints", nargs="*", default=[], help="extra checkpoint dirs or hub ids (name = last path part)")
    p.add_argument("--api_dirs", nargs="*", default=[], help="outputs of generate_api_baseline.py (scored, never generated here)")
    p.add_argument("--include_base", action="store_true")
    p.add_argument("--split", default=None, choices=["validation", "test"], help="default evaluation.split (test)")
    p.add_argument("--out", default=None, help="default <run>/test_eval (test) or <run>/eval_validation")
    p.add_argument("--limit", type=int, default=None, help="smoke: first N test conditions")
    p.add_argument("--rescore", action="store_true")
    p.add_argument("--stage", choices=["all", "generate", "score"], default="all")
    p.add_argument("--generate_one", nargs=2, metavar=("CHECKPOINT", "OUT_DIR"), help=argparse.SUPPRESS)
    return p.parse_args()


def test_rows(cfg, limit, split):
    rows = read_jsonl(resolve(cfg["paths"]["prepared_dir"]) / f"{split}.jsonl")
    return rows[:limit] if limit else rows


def rollout_seed(base: int, condition_id: str, k: int) -> int:
    return int(sha256_text(f"{base}|{condition_id}|{k}")[:8], 16)


# --- 1. generation (one checkpoint per process and GPU) -----------------------------------------


def generate_one(cfg, checkpoint: str, out_dir: Path, limit, split) -> None:
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    gen, ev = cfg["generation"], cfg["evaluation"]
    g, max_prompt, max_completion = int(gen["num_generations"]), int(gen["max_prompt_tokens"]), int(gen["max_completion_tokens"])
    rows = test_rows(cfg, limit, split)
    taxonomy = Taxonomy.load(resolve(cfg["paths"]["taxonomy"]))
    template = load_student_template(cfg["prompts"]["student"])
    tok = AutoTokenizer.from_pretrained(checkpoint)
    prompts = [tok.apply_chat_template(student_messages(template, taxonomy, r), tokenize=True, add_generation_prompt=True,
                                       return_dict=False) for r in rows]
    too_long = [(r["condition_id"], len(p)) for r, p in zip(rows, prompts) if len(p) > max_prompt]
    if too_long:
        raise SystemExit(f"{len(too_long)} test prompts exceed generation.max_prompt_tokens: {too_long[:5]}")
    llm = LLM(checkpoint, dtype="bfloat16", gpu_memory_utilization=float(ev["gpu_memory_utilization"]),
              max_model_len=max_prompt + max_completion, seed=int(ev["seed"]), enable_prefix_caching=True)
    sampling = {"temperature": float(gen["temperature"]), "top_p": float(gen["top_p"]), "top_k": int(gen["top_k"]),
                "repetition_penalty": float(gen["repetition_penalty"]), "max_tokens": max_completion}
    requests, params, keys = [], [], []
    for r, ids in zip(rows, prompts):
        for k in range(g):
            requests.append(TokensPrompt(prompt_token_ids=ids))
            params.append(SamplingParams(n=1, seed=rollout_seed(int(ev["seed"]), r["condition_id"], k), **sampling))
            keys.append((r["condition_id"], k))
    started = time.monotonic()
    outputs = llm.generate(requests, params, use_tqdm=False)
    elapsed = time.monotonic() - started
    records = [{"condition_id": cid, "k": k, "token_ids": list(o.outputs[0].token_ids), "finish_reason": o.outputs[0].finish_reason}
               for (cid, k), o in zip(keys, outputs)]
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "completions.jsonl", records)
    write_json(out_dir / "generation_meta.json", {
        "kind": "vllm_checkpoint", "checkpoint": checkpoint, "split": split, "conditions": len(rows), "rollouts": len(records),
        "generation_s": round(elapsed, 1), "sampling": {"n_per_condition": g, **sampling, "seed_rule": "sha256(seed|condition_id|k)[:8]"},
        "student_prompt_sha256": sha256_text(template), "taxonomy_sha256": taxonomy.sha256,
        "created_at": now_iso(), "timezone": "Asia/Seoul"})


def run_generation(args, jobs) -> None:
    cfg = load_config(args.config, args.override)
    gpus = [x.strip() for x in str(cfg["evaluation"]["generation_gpus"]).split(",") if x.strip()]
    pending = [j for j in jobs if j[3] == "vllm" and not (j[2] / "completions.jsonl").exists()]
    running: dict[str, tuple[subprocess.Popen, str]] = {}
    failed = []
    while pending or running:
        while pending and len(running) < len(gpus):
            name, ckpt, out_dir, _ = pending.pop(0)
            gpu = next(x for x in gpus if x not in {v[1] for v in running.values()})
            out_dir.mkdir(parents=True, exist_ok=True)
            cmd = [sys.executable, __file__, "--config", args.config, "--generate_one", ckpt, str(out_dir)]
            cmd += [f"--override={o}" for o in args.override] + ([f"--limit={args.limit}"] if args.limit else [])
            cmd += [f"--split={args.split}"]
            log = open(out_dir / "generation.log", "w")
            proc = subprocess.Popen(cmd, env={**os.environ, "CUDA_VISIBLE_DEVICES": gpu}, stdout=log, stderr=subprocess.STDOUT,
                                    cwd=NEWMAN_ROOT, start_new_session=True)
            running[name] = (proc, gpu)
            print(f"[generate] {name} on GPU {gpu}: {ckpt}", flush=True)
        time.sleep(5)
        for name, (proc, _) in list(running.items()):
            if proc.poll() is not None:
                try:  # vLLM engine-core children can outlive a failed parent and keep the GPU
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                del running[name]
                print(f"[generate] {name} finished (exit {proc.returncode})", flush=True)
                if proc.returncode:
                    failed.append(name)
    if failed:
        raise SystemExit(f"generation failed for {failed}; see <out>/<name>/generation.log")


# --- 2. scoring -------------------------------------------------------------------------------


def items_for(cfg, out_dir: Path, rows, tok, g: int) -> list[dict]:
    order = {r["condition_id"]: i for i, r in enumerate(rows)}
    comps = [c for c in read_jsonl(out_dir / "completions.jsonl") if c["condition_id"] in order]
    comps.sort(key=lambda c: (order[c["condition_id"]], c["k"]))
    if len(comps) != g * len(order):
        raise SystemExit(f"{out_dir.name}: {len(comps)} completions for {len(order)} conditions x {g}")
    if "token_ids" in comps[0]:
        texts = tok.batch_decode([c["token_ids"] for c in comps], skip_special_tokens=True)  # as in training
        return [{"rank": 0, "local_idx": i, "condition_id": c["condition_id"], "k": c["k"], "ids": c["token_ids"], "text": t.strip()}
                for i, (c, t) in enumerate(zip(comps, texts))]
    return [{"rank": 0, "local_idx": i, "condition_id": c["condition_id"], "k": c["k"], "ids": None, "text": (c["text"] or "").strip(),
             "truncated": bool(c["truncated"]), "length": c.get("output_tokens") or 0} for i, c in enumerate(comps)]


def score(cfg, name: str, out_dir: Path, rows, kind: str = "vllm", split: str = "test") -> dict:
    from transformers import AutoTokenizer

    from newman.orchestrator import RewardOrchestrator

    tok = AutoTokenizer.from_pretrained(cfg["policy"]["model"])
    g = int(cfg["generation"]["num_generations"])
    if kind == "api":  # API baselines keep their own sample count (user 2026-10-02: 1); |G| < 2 there, so aux is 0
        g = int(read_json(out_dir / "generation_meta.json")["request"]["samples_per_condition"])
    items = items_for(cfg, out_dir, rows, tok, g)
    shutil.rmtree(out_dir / "rollouts", ignore_errors=True)
    ev = cfg["evaluation"]
    ecfg = copy.deepcopy(cfg)
    ecfg["generation"]["num_generations"] = g
    if ecfg["rewards"]["auxiliary_reward"] == "student_likeness" and split not in ev["student_likeness_judge_splits"]:
        ecfg["rewards"]["auxiliary_reward"] = "none"  # user 2026-10-02: judge on validation only; humans rate test, aux = 0
    ecfg["verifier"] = {**cfg["verifier"], **ev["verifier"]}  # the only change from the training reward
    secondary = ("a", {**cfg["verifier"], "base_url": f"http://127.0.0.1:{ev['reward_verifier_server']['port']}/v1"}) \
        if ev["with_reward_verifier"] else None
    orch = RewardOrchestrator(ecfg, tok, out_dir, is_main=True, verifier_role="b", secondary_verifier=secondary)
    started = time.monotonic()
    results, group_logs, train_style = orch.score_global(items, step=0, full=True)
    sm = student_metrics(results, group_logs, "b", "a" if secondary else None, bleu=orch.bleu)
    summary = {ROLE_NAMES.get(k, k): v for k, v in sm.items()}
    out = {"name": name, "rollouts": len(results), "conditions": len(rows), "metrics": summary,
           "training_style_metrics": train_style, "reward_settings": orch.describe(),
           "generation": read_json(out_dir / "generation_meta.json") if (out_dir / "generation_meta.json").exists() else {},
           "group_counts": group_counts(results, "b", "a" if secondary else None),
           "scoring_s": round(time.monotonic() - started, 1), "created_at": now_iso()}
    write_json(out_dir / "metrics.json", out)
    return out


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config, args.override)
    if args.generate_one:  # child process: exit hard so a stuck vLLM shutdown cannot hang the driver
        try:
            generate_one(cfg, args.generate_one[0], Path(args.generate_one[1]), args.limit, args.split or cfg["evaluation"]["split"])
        except BaseException:  # noqa: BLE001
            traceback.print_exc()
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(1)
        sys.stdout.flush()
        os._exit(0)

    smoke = bool(args.limit) or bool(cfg.get("smoke"))
    problems = preflight.student_run(cfg, evaluation=True)
    if problems and not smoke:
        print("refusing to start (real evaluation):\n  - " + "\n  - ".join(problems), file=sys.stderr)
        return 2
    if cfg.get("smoke", {}).get("mock_reward_clients") and args.stage != "generate":
        print("note: mock reward clients (smoke): scores are meaningless", flush=True)
    load_dotenv(REPO_ROOT / ".env")

    args.split = args.split or cfg["evaluation"]["split"]
    jobs = []  # (name, checkpoint, out_dir, kind)
    default_dir = "test_eval" if args.split == "test" else f"eval_{args.split}"
    out_root = resolve(args.out) if args.out else (resolve(args.run) / default_dir if args.run else None)
    if out_root is None:
        raise SystemExit("--out is required without --run")
    if args.limit:  # partial runs never mix with the full test results
        out_root = out_root.with_name(f"{out_root.name}_limit{args.limit}")
    if args.include_base:
        jobs.append(("base", cfg["policy"]["model"], out_root / "base", "vllm"))
    if args.run:
        for d in sorted((resolve(args.run) / "epoch_checkpoints").glob("epoch-*"), key=lambda p: float(p.name.split("-")[1])):
            jobs.append((d.name, str(d), out_root / d.name, "vllm"))
    for c in args.checkpoints:
        path = Path(c)
        jobs.append((path.name, str(path.resolve()) if path.exists() else c, out_root / path.name, "vllm"))
    for d in args.api_dirs:
        d = resolve(d)
        dest = out_root / f"api_{d.name}"
        dest.mkdir(parents=True, exist_ok=True)
        for f in ("completions.jsonl", "generation_meta.json"):
            shutil.copy2(d / f, dest / f)
        jobs.append((dest.name, str(d), dest, "api"))
    if not jobs:
        raise SystemExit("nothing to evaluate: --run, --checkpoints, --api_dirs or --include_base")

    if args.stage in ("all", "generate"):
        run_generation(args, jobs)
        if args.stage == "generate":
            print(f"generation done -> {out_root}; start the evaluation servers, then --stage score")
            return 0
    missing = [n for n, _, d, _ in jobs if not (d / "completions.jsonl").exists()]
    if missing:
        raise SystemExit(f"no completions for {missing}; run --stage generate first")
    mock = bool(cfg.get("smoke", {}).get("mock_reward_clients"))
    if not mock:
        import urllib.request

        ev = cfg["evaluation"]
        urls = [ev["verifier"]["base_url"]] + ([f"http://127.0.0.1:{ev['reward_verifier_server']['port']}/v1"] if ev["with_reward_verifier"] else [])
        for url in urls:
            health = url.rsplit("/v1", 1)[0] + "/health"
            try:
                urllib.request.urlopen(health, timeout=5)
            except OSError as exc:
                raise SystemExit(f"verifier server not up at {health} ({exc}): bash scripts/launch_eval_servers.sh {args.config}") from exc
        if not os.environ.get("OPENAI_API_KEY"):
            raise SystemExit("OPENAI_API_KEY is not set (tutee_error/.env)")

    rows = test_rows(cfg, args.limit, args.split)
    results = {}
    for name, ckpt, out_dir, kind in jobs:
        if (out_dir / "metrics.json").exists() and not args.rescore:
            results[name] = read_json(out_dir / "metrics.json")
        else:
            print(f"[score] {name}", flush=True)
            results[name] = score(cfg, name, out_dir, rows, kind, args.split)
        m = results[name]["metrics"]
        print(f"  {name}: B joint success {m['b_joint_success']:.4f} · wrong {m['wrong_rate']:.4f} · B accept|wrong "
              f"{(m['b_accept_given_wrong'] or 0):.4f} · reward {m['reward_total_mean']:.4f}", flush=True)

    ev = cfg["evaluation"]
    counts = {n: r["group_counts"] for n, r in results.items()}
    boot = paired_bootstrap(counts, int(ev["bootstrap_samples"]), int(cfg["seed"]), reference="base" if "base" in counts else None)
    metric, select_split = ev["select_metric"], ev["select_split"]
    snapshots = {n: r for n, r in results.items() if n.startswith("epoch-")}
    if metric == REQUIRED:
        best, note = None, "evaluation.select_metric is REQUIRED (open decision)"
    elif args.split == select_split:
        if metric not in SELECT_METRICS:
            raise SystemExit(f"evaluation.select_metric must be one of {SELECT_METRICS}")
        best = max(snapshots, key=lambda n: snapshots[n]["metrics"][metric]) if snapshots else None
        note = f"chosen on {select_split} by {metric}"
    else:
        chosen = out_root.parent / f"eval_{select_split}" / "summary.json"
        best = read_json(chosen).get("best_snapshot") if chosen.exists() else None
        note = f"chosen on {select_split} ({rel(chosen)})" if best else f"not chosen yet: run --split {select_split} first"
    keep = ("wrong_rate", "correct_rate", "null_rate", "b_joint_success", "b_accept_given_wrong", "a_accept_given_wrong",
            "ab_disagreement_given_wrong", "zero_success_condition_rate", "truncation_rate", "b_invalid_sample_rate",
            "reward_total_mean", "joint_success_macro_over_types", "diversity_mean_in_successes", "unique_successful_solutions_mean")
    write_json(out_root / "summary.json", {
        "created_at": now_iso(), "timezone": "Asia/Seoul", "config": args.config, "run": args.run, "split": args.split, "git": git_state(),
        "test_verifier": cfg["evaluation"]["verifier"]["checkpoint"], "reward_verifier_diagnostic": cfg["verifier"]["checkpoint"]
        if ev["with_reward_verifier"] else None, "limit": args.limit, "select_metric": metric, "select_split": select_split, "best_snapshot": best,
        "selection_note": note, "approvals": approvals.snapshot(), "preflight_warnings": problems,
        "results": {n: {"checkpoint": c, "kind": k, **{m: results[n]["metrics"].get(m) for m in keep},
                        "by_stage": results[n]["metrics"]["by_stage"], "by_type": results[n]["metrics"]["by_type"],
                        "by_unit_eligibility": results[n]["metrics"]["by_unit_eligibility"]} for n, c, _, k in jobs},
        "paired_bootstrap": boot})
    print(f"best snapshot by {metric}: {best} ({note}) -> {rel(out_root / 'summary.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
