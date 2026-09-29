#!/usr/bin/env python3
"""Test-set evaluation of RL checkpoints; the best epoch is the one with the highest mean test reward.

The reward is the training reward (same terms and weights, Student prompt and sampling, group size G,
gpt-5-nano answer check, auxiliary term) with the error-alignment verifier swapped for the held-out
half-B checkpoint (`evaluation.verifier`). The epoch is chosen on test, so its test score is optimistic.

Run (from rl/, after training):
  bash scripts/stop_servers.sh                                  # frees the inference GPU
  bash scripts/launch_eval_server.sh configs/diversity.yaml     # test verifier on :8002
  python scripts/evaluate.py --config configs/diversity.yaml --run outputs/diversity_seed42 [--include_base]

1. generation: one vLLM engine per checkpoint, each on its own GPU (evaluation.generation_gpus); G rollouts
   per test prompt with the training sampling settings and per-rollout seeds shared by every checkpoint
2. scoring: RewardOrchestrator._score_global over the whole test set (the rank-0 path of training, step 0)
Outputs: <out>/<name>/{completions.jsonl, rollouts/, metrics.json}, <out>/summary.json (out = <run>/test_eval)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tutee_rl.common import (  # noqa: E402
    REPO_ROOT,
    RL_ROOT,
    eval_verifier_cfg,
    load_config,
    load_dotenv,
    read_jsonl,
    read_template,
    resolve,
    sha256_text,
    student_messages,
    write_json,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True, help="the experiment config the run was trained with")
    p.add_argument("--override", action="append", default=[], help="a.b.c=value (YAML value), repeatable")
    p.add_argument("--run", default=None, help="training run dir: every epoch_checkpoints/epoch-K is evaluated")
    p.add_argument("--checkpoints", nargs="*", default=[], help="extra checkpoint dirs or hub ids (name = last path part)")
    p.add_argument("--include_base", action="store_true", help="also evaluate the untrained policy as a reference")
    p.add_argument("--out", default=None, help="default <run>/test_eval")
    p.add_argument("--limit", type=int, default=None, help="first N test prompts (pipeline check only)")
    p.add_argument("--rescore", action="store_true", help="score again although metrics.json exists")
    p.add_argument("--generate_one", nargs=2, metavar=("CHECKPOINT", "OUT_DIR"), help=argparse.SUPPRESS)
    return p.parse_args()


def test_rows(cfg, limit):
    rows = read_jsonl(resolve(cfg["paths"]["prepared_dir"]) / f"{cfg['evaluation']['split']}.jsonl")
    return rows[:limit] if limit else rows


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def rollout_seed(base: int, pair_id: str, k: int) -> int:
    return int(sha256_text(f"{base}|{pair_id}|{k}")[:8], 16)


# --- 1. generation (one checkpoint, run in its own process on one GPU) --------

def generate_one(cfg, checkpoint: str, out_dir: Path, limit) -> None:
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    gen, ev = cfg["generation"], cfg["evaluation"]
    g, max_prompt, max_completion = int(gen["num_generations"]), int(gen["max_prompt_tokens"]), int(gen["max_completion_tokens"])
    rows = test_rows(cfg, limit)
    tok = AutoTokenizer.from_pretrained(checkpoint)
    template = read_template(cfg["prompts"]["student"])
    prompts = [tok.apply_chat_template(student_messages(template, r), tokenize=True, add_generation_prompt=True, return_dict=False)
               for r in rows]
    too_long = [(r["PairId"], len(p)) for r, p in zip(rows, prompts) if len(p) > max_prompt]
    if too_long:
        raise SystemExit(f"{len(too_long)} test prompts exceed generation.max_prompt_tokens: {too_long[:5]}")

    llm = LLM(checkpoint, dtype="bfloat16", gpu_memory_utilization=float(ev["gpu_memory_utilization"]),
              max_model_len=max_prompt + max_completion, seed=int(ev["seed"]), enable_prefix_caching=True)
    # the training sampling as sent by TRL to `trl vllm-serve`; one request per rollout
    sampling = {"temperature": float(gen["temperature"]), "top_p": float(gen["top_p"]), "top_k": int(gen["top_k"]),
                "repetition_penalty": float(gen["repetition_penalty"]), "max_tokens": max_completion}
    requests, params, keys = [], [], []
    for r, ids in zip(rows, prompts):
        for k in range(g):
            requests.append(TokensPrompt(prompt_token_ids=ids))
            params.append(SamplingParams(n=1, seed=rollout_seed(int(ev["seed"]), r["PairId"], k), **sampling))
            keys.append((r["PairId"], k))
    started = time.monotonic()
    outputs = llm.generate(requests, params, use_tqdm=False)
    elapsed = time.monotonic() - started
    records = []
    for (pid, k), o in zip(keys, outputs):
        c = o.outputs[0]
        records.append({"PairId": pid, "k": k, "token_ids": list(c.token_ids), "finish_reason": c.finish_reason})
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "completions.jsonl", records)
    write_json(out_dir / "generation_meta.json", {
        "checkpoint": checkpoint, "prompts": len(rows), "rollouts": len(records), "generation_s": elapsed,
        "sampling": {"n_per_prompt": g, **sampling, "seed_rule": "sha256(seed|PairId|k)[:8]"},
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })


def run_generation(args, cfg, jobs: list[tuple[str, str, Path]]) -> None:
    gpus = [x.strip() for x in str(cfg["evaluation"]["generation_gpus"]).split(",") if x.strip()]
    pending = [j for j in jobs if not (j[2] / "completions.jsonl").exists()]
    running: dict[str, tuple[subprocess.Popen, str]] = {}
    failed = []
    while pending or running:
        while pending and len(running) < len(gpus):
            name, ckpt, out_dir = pending.pop(0)
            gpu = next(x for x in gpus if x not in {v[1] for v in running.values()})
            out_dir.mkdir(parents=True, exist_ok=True)
            cmd = [sys.executable, __file__, "--config", args.config, "--generate_one", ckpt, str(out_dir)]
            cmd += [f"--override={o}" for o in args.override] + ([f"--limit={args.limit}"] if args.limit else [])
            log = open(out_dir / "generation.log", "w")
            proc = subprocess.Popen(cmd, env={**os.environ, "CUDA_VISIBLE_DEVICES": gpu}, stdout=log, stderr=subprocess.STDOUT, cwd=RL_ROOT,
                                    start_new_session=True)
            running[name] = (proc, gpu)
            print(f"[generate] {name} on GPU {gpu}: {ckpt}", flush=True)
        time.sleep(5)
        for name, (proc, gpu) in list(running.items()):
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


# --- 2. scoring (the training reward with the test verifier) -----------------

def score(cfg, name: str, out_dir: Path, limit) -> dict:
    from transformers import AutoTokenizer

    from tutee_rl.orchestrator import RewardOrchestrator

    g = int(cfg["generation"]["num_generations"])
    tok = AutoTokenizer.from_pretrained(cfg["policy"]["model"])
    order = {r["PairId"]: i for i, r in enumerate(test_rows(cfg, limit))}
    comps = sorted(read_jsonl(out_dir / "completions.jsonl"), key=lambda c: (order[c["PairId"]], c["k"]))
    if len(comps) != g * len(order):
        raise SystemExit(f"{name}: {len(comps)} completions for {len(order)} prompts x {g}")
    texts = tok.batch_decode([c["token_ids"] for c in comps], skip_special_tokens=True)  # as in training
    items = [{"rank": 0, "local_idx": i, "pair_id": c["PairId"], "ids": c["token_ids"], "text": t.strip()}
             for i, (c, t) in enumerate(zip(comps, texts))]

    shutil.rmtree(out_dir / "rollouts", ignore_errors=True)
    orch = RewardOrchestrator(cfg, tok, out_dir, is_main=True)
    started = time.monotonic()
    results, metrics = orch._score_global(items, step=0)
    w = float(cfg["rewards"]["auxiliary_weight"])
    n = len(results)
    metrics.update({
        "reward/main_mean": sum(r["main"] for r in results) / n,
        "reward/aux_weighted_mean": w * sum(r["aux"] for r in results) / n,
        "reward/truncation_mean": sum(r["trunc"] for r in results) / n,
        "timing/scoring_s": time.monotonic() - started,
    })
    out = {"name": name, "rollouts": n, "prompts": len(order), "metrics": metrics, "reward_settings": orch.describe(),
           "generation": read_json(out_dir / "generation_meta.json")}
    write_json(out_dir / "metrics.json", out)
    return out


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config, args.override)
    if args.generate_one:  # child process: exit hard so a stuck vLLM shutdown cannot hang the driver
        try:
            generate_one(cfg, args.generate_one[0], Path(args.generate_one[1]), args.limit)
        except BaseException:  # noqa: BLE001
            traceback.print_exc()
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(1)
        sys.stdout.flush()
        os._exit(0)

    load_dotenv(REPO_ROOT / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        print("refusing to start: OPENAI_API_KEY is not set (put it in tutee_error/.env)", file=sys.stderr)
        return 2
    if cfg.get("smoke", {}).get("mock_reward_clients"):
        print("refusing to start: evaluation never uses mock reward clients", file=sys.stderr)
        return 2
    cfg["verifier"] = eval_verifier_cfg(cfg)  # the only change from the training reward

    jobs: list[tuple[str, str, Path]] = []
    if args.include_base:
        jobs.append(("base", cfg["policy"]["model"], Path()))
    if args.run:
        for d in sorted((Path(args.run) / "epoch_checkpoints").glob("epoch-*"), key=lambda p: float(p.name.split("-")[1])):
            jobs.append((d.name, str(d.resolve()), Path()))
    for c in args.checkpoints:
        jobs.append((Path(c).name, str(Path(c).resolve()) if Path(c).exists() else c, Path()))
    if not jobs:
        raise SystemExit("nothing to evaluate: give --run and/or --checkpoints / --include_base")
    out_root = Path(args.out) if args.out else Path(args.run) / "test_eval" if args.run else None
    if out_root is None:
        raise SystemExit("--out is required without --run")
    out_root = resolve(out_root)
    jobs = [(name, ckpt, out_root / name) for name, ckpt, _ in jobs]

    import urllib.request

    health = cfg["verifier"]["base_url"].rsplit("/v1", 1)[0] + "/health"
    try:
        urllib.request.urlopen(health, timeout=5)
    except OSError as exc:
        raise SystemExit(f"test verifier is not up at {health} ({exc}); run scripts/launch_eval_server.sh first") from exc

    run_generation(args, cfg, jobs)
    summary = {}
    for name, ckpt, out_dir in jobs:
        if (out_dir / "metrics.json").exists() and not args.rescore:
            summary[name] = read_json(out_dir / "metrics.json")
        else:
            print(f"[score] {name}", flush=True)
            summary[name] = score(cfg, name, out_dir, args.limit)
        m = summary[name]["metrics"]
        print(f"  {name}: reward {m['reward/total_mean']:.4f} (main {m['reward/main_mean']:.4f}, aux {m['reward/aux_weighted_mean']:.4f}, "
              f"trunc {m['reward/truncation_mean']:.4f}) target success {m['target/success_rate']:.4f}", flush=True)

    key = cfg["evaluation"]["select_metric"]
    epochs = {k: v for k, v in summary.items() if k.startswith("epoch-")}
    best = max(epochs, key=lambda k: epochs[k]["metrics"][key]) if epochs else None
    write_json(out_root / "summary.json", {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": args.config, "run": args.run, "select_metric": key, "best_epoch": best,
        "selection_note": "chosen on the test split (optimistic by design)",
        "test_verifier": cfg["verifier"]["checkpoint"], "limit": args.limit,
        "results": {k: {"checkpoint": c, **{m: v["metrics"][m] for m in sorted(v["metrics"])}}
                    for (k, c, _), v in zip(jobs, summary.values())},
    })
    if best:
        print(f"best epoch by {key}: {best} ({epochs[best]['metrics'][key]:.4f}) -> {out_root / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
