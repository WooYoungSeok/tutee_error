#!/usr/bin/env python3
"""GRPO training of the Student with the conditional-error reward (TRL, vLLM server mode).

Launch through scripts/run_train.sh (servers first: scripts/launch_servers.sh). Direct use:
  accelerate launch --config_file configs/accelerate_zero2.yaml --num_processes 3 scripts/train.py \
      --config configs/diversity.yaml [--override training.save_steps=10] [--max_steps N] [--limit N]

Refuses to start while any `REQUIRED` config value is unset (see tutee_rl.common.validate_for_training).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tutee_rl.common import (  # noqa: E402
    REPO_ROOT,
    load_config,
    load_dotenv,
    read_jsonl,
    read_template,
    resolve,
    sha256_file,
    student_messages,
    validate_for_training,
    write_json,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--override", action="append", default=[], help="a.b.c=value (YAML value), repeatable")
    p.add_argument("--run_name", default=None)
    p.add_argument("--max_steps", type=int, default=-1)
    p.add_argument("--limit", type=int, default=None, help="smoke: first N training prompts")
    p.add_argument("--resume", default=None, help="checkpoint dir, or 'latest'")
    p.add_argument("--report_to", default=None)
    return p.parse_args()


def build_dataset(cfg, tokenizer, limit):
    from datasets import Dataset

    rows = read_jsonl(resolve(cfg["paths"]["prepared_dir"]) / "train.jsonl")
    if limit:
        rows = rows[:limit]
    template = read_template(cfg["prompts"]["student"])
    records, lengths = [], []
    for r in rows:
        messages = student_messages(template, r)
        records.append({"prompt": messages, "PairId": r["PairId"]})
        lengths.append(len(tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_dict=False)))
    too_long = [(rows[i]["PairId"], n) for i, n in enumerate(lengths) if n > cfg["generation"]["max_prompt_tokens"]]
    if too_long:
        raise SystemExit(f"{len(too_long)} prompts exceed generation.max_prompt_tokens: {too_long[:5]}")
    stats = {"prompts": len(records), "prompt_tokens_max": max(lengths), "prompt_tokens_mean": sum(lengths) / len(lengths)}
    return Dataset.from_list(records), stats


def epoch_save_callback(run_dir: Path, tokenizer):
    """Model-only snapshot at every epoch end -> <run>/epoch_checkpoints/epoch-K (never rotated).

    All epochs are kept so the best one can be chosen on test afterwards. The Trainer's own
    checkpoint-N folders (full optimizer state, rotated) exist only to resume an aborted run.
    """
    from transformers import TrainerCallback

    class EpochSave(TrainerCallback):
        trainer = None

        def on_epoch_end(self, args, state, control, **kwargs):
            epoch = int(round(state.epoch or 0))
            out = run_dir / "epoch_checkpoints" / f"epoch-{epoch}"
            self.trainer.save_model(str(out))  # collective under DeepSpeed; every rank calls it
            if state.is_world_process_zero:
                tokenizer.save_pretrained(str(out))
                write_json(out / "epoch_meta.json", {"epoch": epoch, "state_epoch": state.epoch, "global_step": state.global_step,
                                                     "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
            return control

    return EpochSave()


def versions() -> dict[str, str]:
    import importlib.metadata as md

    out = {"python": platform.python_version()}
    for pkg in ("torch", "transformers", "trl", "vllm", "deepspeed", "accelerate", "openai", "sacrebleu", "datasets"):
        try:
            out[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            out[pkg] = "missing"
    return out


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config, args.override)
    problems = validate_for_training(cfg)
    if problems:
        print("refusing to start:\n  - " + "\n  - ".join(problems), file=sys.stderr)
        return 2
    load_dotenv(REPO_ROOT / ".env")
    mock = bool(cfg.get("smoke", {}).get("mock_reward_clients"))
    if mock and not (args.run_name or "").startswith("smoke_"):
        print("refusing to start: mock reward clients are only allowed for --run_name smoke_*", file=sys.stderr)
        return 2
    if not mock and not os.environ.get("OPENAI_API_KEY"):
        print("refusing to start: OPENAI_API_KEY is not set (put it in tutee_error/.env)", file=sys.stderr)
        return 2

    import torch
    from accelerate import PartialState
    from transformers import AutoTokenizer
    from trl import GRPOConfig, GRPOTrainer

    from tutee_rl.orchestrator import RewardOrchestrator

    if not cfg["training"].get("log_profiling", False):
        # TRL sends every profiled call (30+ per optimizer step) to W&B without a step, which floods the run;
        # step timing stays in train/step_time and train/timing/reward_scoring_s.
        from trl.extras import profiling

        profiling.ProfilingContext._log_metrics = lambda self, duration: None

    state = PartialState()
    t = cfg["training"]
    gen = cfg["generation"]
    srv = cfg["servers"]["rollout"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if args.resume == "latest" and not args.run_name:
        raise SystemExit("--resume latest needs --run_name of the run to continue")
    if args.resume and args.resume != "latest":
        run_dir = Path(args.resume).resolve().parent  # outputs/<run>/checkpoint-N
        run_name = run_dir.name
    else:
        run_name = args.run_name or f"{cfg['experiment']}_{stamp}"
        run_dir = resolve(cfg["paths"]["output_root"]) / run_name

    tokenizer = AutoTokenizer.from_pretrained(cfg["policy"]["model"])
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    dataset, data_stats = build_dataset(cfg, tokenizer, args.limit)

    report_to = args.report_to or t["report_to"]
    if report_to == "wandb":
        os.environ["WANDB_PROJECT"] = t.get("wandb_project", "tutee_error_rl")  # ../.env's WANDB_PROJECT is the verifier SFT project
        if not os.environ.get("WANDB_API_KEY"):
            report_to = "none"
        else:  # one W&B run per training run: a --resume continues the run recorded in <run>/wandb_run_id.txt
            id_file = run_dir / "wandb_run_id.txt"
            if not id_file.exists() and state.is_main_process:
                import secrets

                run_dir.mkdir(parents=True, exist_ok=True)
                id_file.write_text(secrets.token_hex(4) + "\n", encoding="utf-8")
            if state.is_main_process:
                os.environ["WANDB_RUN_ID"] = id_file.read_text(encoding="utf-8").strip()
                os.environ["WANDB_RESUME"] = "allow"

    per_step = t["per_device_train_batch_size"] * state.num_processes * t["gradient_accumulation_steps"]
    if per_step % gen["num_generations"]:
        raise SystemExit(f"completions per step {per_step} is not divisible by num_generations {gen['num_generations']}")

    grpo_args = GRPOConfig(
        output_dir=str(run_dir),
        run_name=run_name,
        seed=cfg["seed"],
        learning_rate=float(t["learning_rate"]),
        beta=float(t["beta"]),
        epsilon=float(t["epsilon"]),
        loss_type=t["loss_type"],
        scale_rewards=t["scale_rewards"],
        num_iterations=int(t["num_iterations"]),
        num_train_epochs=float(t["num_train_epochs"]),
        max_steps=args.max_steps,
        per_device_train_batch_size=int(t["per_device_train_batch_size"]),
        gradient_accumulation_steps=int(t["gradient_accumulation_steps"]),
        gradient_checkpointing=bool(t["gradient_checkpointing"]),
        bf16=bool(t["bf16"]),
        lr_scheduler_type=t["lr_scheduler_type"],
        warmup_steps=int(t["warmup_steps"]),
        max_grad_norm=float(t["max_grad_norm"]),
        logging_steps=int(t["logging_steps"]),
        save_strategy="steps",                       # resume checkpoints (rotated); epochs saved by EpochSave
        save_steps=int(t["resume_save_steps"]),
        save_total_limit=int(t["resume_save_total_limit"]),
        report_to=report_to,
        ddp_timeout=int(t["ddp_timeout_s"]),
        mask_truncated_completions=bool(t["mask_truncated_completions"]),
        num_generations=int(gen["num_generations"]),
        max_completion_length=int(gen["max_completion_tokens"]),
        temperature=float(gen["temperature"]),
        top_p=float(gen["top_p"]),
        top_k=int(gen["top_k"]),
        repetition_penalty=float(gen["repetition_penalty"]),
        use_vllm=True,
        vllm_mode="server",
        vllm_server_host=srv["host"],
        vllm_server_port=int(srv["port"]),
        vllm_group_port=int(srv["group_port"]),
        vllm_server_timeout=600.0,
        model_init_kwargs={"dtype": torch.bfloat16, "attn_implementation": cfg["policy"]["attn_implementation"]},
        reward_weights=None,  # set below from the orchestrator
        shuffle_dataset=True,
        remove_unused_columns=False,
        log_completions=False,
        save_only_model=False,
    )

    orchestrator = RewardOrchestrator(cfg, tokenizer, run_dir, is_main=state.is_main_process)
    funcs, weights = orchestrator.reward_funcs()
    grpo_args.reward_weights = weights

    if state.is_main_process:
        run_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "run_name": run_name,
            "config_chain": cfg["_config_chain"],
            "config_sha256": cfg["_config_sha256"],
            "config": {k: v for k, v in cfg.items() if not k.startswith("_")},
            "cli": vars(args),
            "versions": versions(),
            "num_processes": state.num_processes,
            "completions_per_step": per_step,
            "prompts_per_step": per_step // gen["num_generations"],
            "data": {**data_stats, "prepared_meta": json.loads((resolve(cfg["paths"]["prepared_dir"]) / "meta.json").read_text())},
            "prompt_sha256": {k: sha256_file(resolve(v)) for k, v in cfg["prompts"].items()},
            "reward": {"reward_funcs": [f.__name__ for f in funcs], "reward_weights": weights, **orchestrator.describe()},
            "trl_loss": {"loss_type": t["loss_type"], "scale_rewards": t["scale_rewards"], "beta": t["beta"],
                         "vllm_importance_sampling_correction": grpo_args.vllm_importance_sampling_correction,
                         "use_bias_correction_kl": grpo_args.use_bias_correction_kl},
            "deepspeed_config": os.environ.get("ACCELERATE_DEEPSPEED_CONFIG_FILE"),
            "gpus": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
        }
        meta_name = "run_meta.json"
        if args.resume and (run_dir / meta_name).exists():  # keep the original run's metadata
            meta_name = f"run_meta.resume_{stamp}.json"
        write_json(run_dir / meta_name, meta)
        print(json.dumps({k: meta[k] for k in ("run_name", "completions_per_step", "prompts_per_step", "reward")}, indent=2, ensure_ascii=False))

    epoch_cb = epoch_save_callback(run_dir, tokenizer)
    trainer = GRPOTrainer(
        model=cfg["policy"]["model"],
        reward_funcs=funcs,
        args=grpo_args,
        train_dataset=dataset,
        processing_class=tokenizer,
        callbacks=[epoch_cb],
    )
    epoch_cb.trainer = trainer
    resume = True if args.resume == "latest" else args.resume
    trainer.train(resume_from_checkpoint=resume)
    trainer.save_model(str(run_dir / "final"))
    if state.is_main_process:
        tokenizer.save_pretrained(str(run_dir / "final"))
        print(f"done: {run_dir / 'final'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
