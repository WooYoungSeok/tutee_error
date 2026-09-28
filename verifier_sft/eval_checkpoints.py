#!/usr/bin/env python3
"""Evaluate every checkpoint of a training run on the test split and log the results to its wandb run.

For runs trained with training.use_validation false, where every epoch is saved and the checkpoint is
chosen afterwards. Each checkpoint-<step> is evaluated by eval_descriptive_verifier.py (same exact-match
protocol, one process per checkpoint) under the name <prefix>epoch<k>; summarize_results.py then compares
the epochs in <output.report_dir>/verifier_results.md. Finally the test metrics are appended to the
training run in wandb as test/* against test/epoch (the run id is read from train.log). A checkpoint whose
metrics already exist is not evaluated again; a wandb failure does not affect the saved results.

Choosing the epoch on these numbers makes the chosen epoch's test score optimistic; report it as such.

Usage (from verifier_sft/):
    CUDA_VISIBLE_DEVICES=1 python eval_checkpoints.py --config config/<cfg>.json --run_dir checkpoints/<run>
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from errdesc.runner import load_dotenv  # noqa: E402
from verifier_common import load_config, resolve  # noqa: E402

METRICS = ("accuracy", "macro_f1", "pair_accuracy", "negative_acceptance_rate", "positive_rejection_rate", "invalid_rate")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True)
    parser.add_argument("--run_dir", required=True)
    parser.add_argument("--name_prefix", default="sft_")
    parser.add_argument("--limit", type=int, default=None, help="smoke test: first N test rows (no wandb)")
    parser.add_argument("--no_wandb", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    run_dir = resolve(args.run_dir)
    ckpts = sorted(run_dir.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[-1]))
    if not ckpts:
        raise SystemExit(f"no checkpoints in {run_dir}")

    rows = []
    for ckpt in ckpts:
        state = json.loads((ckpt / "trainer_state.json").read_text(encoding="utf-8"))
        epoch = round(state["epoch"])
        name = f"{args.name_prefix}epoch{epoch}"
        out_name = f"{name}_limit{args.limit}" if args.limit else name
        metrics_path = resolve(config["evaluation"]["output_dir"]) / out_name / "metrics.json"
        done = metrics_path.exists() and json.loads(metrics_path.read_text(encoding="utf-8"))["model_path"] == str(ckpt)
        if not done:
            cmd = [sys.executable, str(HERE / "eval_descriptive_verifier.py"), "--config", args.config,
                   "--model_path", str(ckpt), "--name", name]
            if args.limit:
                cmd += ["--limit", str(args.limit)]
            print(f"== {ckpt.name} (epoch {epoch}) -> {out_name}", flush=True)
            subprocess.run(cmd, check=True, cwd=HERE)
        m = json.loads(metrics_path.read_text(encoding="utf-8"))
        rows.append({"epoch": epoch, "step": state["global_step"], "checkpoint": ckpt.name, "name": out_name,
                     **{k: m["overall"][k] for k in METRICS},
                     "accuracy_ci": [m["bootstrap_ci_question_groups"]["accuracy"][b] for b in ("low", "high")]})

    for r in rows:
        print(f"epoch {r['epoch']} ({r['checkpoint']}): accuracy {r['accuracy']:.4f} · macro-F1 {r['macro_f1']:.4f} · "
              f"pair accuracy {r['pair_accuracy']:.4f} · invalid {r['invalid_rate']:.4f}", flush=True)
    if not args.limit:
        subprocess.run([sys.executable, str(HERE / "summarize_results.py"), "--config", args.config]
                       + [r["name"] for r in rows], check=True, cwd=HERE)
    if args.no_wandb or args.limit:
        return 0

    match = re.search(r"https://wandb\.ai/([^/\s]+)/([^/\s]+)/runs/(\w+)", (run_dir / "train.log").read_text(errors="ignore"))
    if not match:
        print("no wandb run found in train.log; results are saved but not logged", flush=True)
        return 0
    entity, project, run_id = match.groups()
    try:
        load_dotenv(HERE.parent / ".env")
        import wandb

        run = wandb.init(entity=entity, project=project, id=run_id, resume="must")
        run.define_metric("test/epoch")
        run.define_metric("test/*", step_metric="test/epoch")
        for r in rows:
            run.log({"test/epoch": r["epoch"], **{f"test/{k}": r[k] for k in METRICS}})
        table = wandb.Table(columns=["epoch", "step", "checkpoint"] + list(METRICS))
        for r in rows:
            table.add_data(r["epoch"], r["step"], r["checkpoint"], *[r[k] for k in METRICS])
        run.log({"test/by_epoch": table})
        best = max(rows, key=lambda r: (r["accuracy"], r["macro_f1"]))
        run.summary.update({"test/best_epoch_by_accuracy (chosen on test)": best["epoch"],
                            "test/best_accuracy (chosen on test)": best["accuracy"],
                            "test/data_sha256": json.loads((resolve(config["evaluation"]["output_dir"]) / best["name"] / "metrics.json").read_text())["data_sha256"]})
        run.finish()
        print(f"logged {len(rows)} epochs to wandb run {entity}/{project}/{run_id}", flush=True)
    except Exception as exc:  # noqa: BLE001 - the evaluation results are already on disk
        print(f"wandb logging failed ({type(exc).__name__}: {exc}); results are saved in outputs/ and reports/", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
