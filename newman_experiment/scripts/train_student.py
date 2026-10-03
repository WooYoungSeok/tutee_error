#!/usr/bin/env python3
"""GRPO training of the Student(Q, N, E) -> incorrect solution S with the Newman reward (TRL, vLLM server mode).

Reward (plan 8): gpt-5-nano (reasoning effort low) extracts and grades the final answer of every rollout; an
incorrect one goes to the frozen reward verifier A (n=2, T=0.6, both `aligned`); plus 0.5 x the experiment's
auxiliary term inside G and the truncation penalty. Model-only snapshots and resume checkpoints every 0.5 epoch, all kept (user rule 5); the snapshot is chosen on test afterwards (scripts/evaluate_student.py).

Launch through scripts/run_train_student.sh (servers first: scripts/launch_servers.sh):
  bash scripts/run_train_student.sh configs/student_likeness.yaml              # run name <experiment>_seed42_<KST stamp>
  bash scripts/run_train_student.sh configs/diversity.yaml --run_name newman_diversity_seed42_20261001_101500 --resume latest
Another epoch after a finished run (prepared 2026-10-02, used only when the user decides; see continuation_plan()):
  bash scripts/run_train_student.sh configs/student_likeness.yaml --continue_from outputs/<run>/epoch_checkpoints/epoch-1.00
Refuses to start while a REQUIRED decision, an unapproved draft, or unverified data is involved (smoke_* runs excepted).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman import approvals, preflight  # noqa: E402
from newman.common import (  # noqa: E402
    REPO_ROOT,
    default_run_name,
    dir_size_gb,
    disk_problem,
    git_state,
    load_config,
    load_dotenv,
    now_iso,
    public_config,
    read_json,
    read_jsonl,
    rel,
    resolve,
    run_stamp,
    sha256_file,
    versions,
    write_json,
)
from newman.taxonomy import Taxonomy  # noqa: E402
from newman.verifier_format import load_student_template, student_messages  # noqa: E402

GEN_CONFIG_KEYS = ("bos_token_id", "eos_token_id", "pad_token_id", "transformers_version")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--override", action="append", default=[], help="a.b.c=value (YAML value), repeatable")
    p.add_argument("--run_name", default=None)
    p.add_argument("--max_steps", type=int, default=-1, help="smoke only")
    p.add_argument("--limit", type=int, default=None, help="smoke only: first N training conditions")
    p.add_argument("--resume", default=None, help="checkpoint dir, or 'latest' (needs --run_name)")
    p.add_argument("--report_to", default=None)
    p.add_argument("--continue_from", default=None,
                   help="model snapshot of a finished run (epoch_checkpoints/epoch-X): train one more stage from its weights "
                        "with the KL reference kept on policy.model, no warmup and a new data order (continuation_plan)")
    return p.parse_args()


def continuation_plan(cfg, path: str | None) -> dict | None:
    """Settings of a continuation stage (prepared 2026-10-02 on the user's request; not yet decided to run).
    - policy weights from the snapshot (Adam moments start fresh: snapshots hold weights only);
    - KL reference stays the original policy.model, so the objective is the same as in the first stage;
    - learning rate: cfg.continuation.warmup_ratio (0) warmup, then the same linear decay over num_train_epochs;
    - data order: the training conditions are permuted with a stage-specific seed before TRL's own seeded shuffle,
      so the stage does not replay the first epoch's order;
    - snapshot names continue the epoch count (epoch-1.25 ... after a 1-epoch first stage)."""
    if not path:
        return None
    snap = Path(path).resolve()
    if not (snap / "config.json").exists():
        raise SystemExit(f"--continue_from {path}: no model snapshot (config.json) there")
    meta = snap / "epoch_meta.json"
    if not meta.exists():
        raise SystemExit(f"--continue_from {path}: no epoch_meta.json to read the finished epoch count from")
    offset = float(read_json(meta)["epoch"])
    stage = int(round(offset / float(cfg["training"]["num_train_epochs"]))) + 1
    return {"from": rel(snap), "from_run": snap.parent.parent.name, "epoch_offset": offset, "stage": stage,
            "reference_model": cfg["policy"]["model"], "warmup_ratio": float(cfg["continuation"]["warmup_ratio"]),
            "data_permutation_seed": f"{cfg['seed']}|stage{stage}", "optimizer_state": "fresh (snapshot holds weights only)"}


def permute_for_stage(rows: list, cont: dict | None) -> list:
    if not cont:
        return rows
    rng = random.Random(int(hashlib.sha256(cont["data_permutation_seed"].encode()).hexdigest()[:16], 16))
    rows = list(rows)
    rng.shuffle(rows)
    return rows


def write_generation_config(model_dir: Path, cfg) -> None:
    """Snapshots sample like the RL run, not with the base model's defaults (Qwen2.5: T 0.7, top_p 0.8, top_k 20)."""
    path = model_dir / "generation_config.json"
    base = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    gen = cfg["generation"]
    out = {k: base[k] for k in GEN_CONFIG_KEYS if k in base}
    out.update(do_sample=True, temperature=float(gen["temperature"]), top_p=float(gen["top_p"]), top_k=int(gen["top_k"]),
               repetition_penalty=float(gen["repetition_penalty"]), max_new_tokens=int(gen["max_completion_tokens"]))
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")


def build_dataset(cfg, tokenizer, taxonomy, limit, cont=None):
    from datasets import Dataset

    rows = permute_for_stage(read_jsonl(resolve(cfg["paths"]["prepared_dir"]) / "train.jsonl"), cont)
    if limit:
        rows = rows[:limit]
    template = load_student_template(cfg["prompts"]["student"])
    records, lengths = [], []
    for r in rows:
        if taxonomy.stage_of(r["source_error_id"]) != r["newman_stage"]:
            raise SystemExit(f"{r['condition_id']}: stage {r['newman_stage']} is not mapping({r['source_error_id']})")
        messages = student_messages(template, taxonomy, r)
        records.append({"prompt": messages, "condition_id": r["condition_id"]})
        lengths.append(len(tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_dict=False)))
    too_long = [(rows[i]["condition_id"], n) for i, n in enumerate(lengths) if n > int(cfg["generation"]["max_prompt_tokens"])]
    if too_long:
        raise SystemExit(f"{len(too_long)} prompts exceed generation.max_prompt_tokens: {too_long[:5]}")
    stats = {"conditions": len(records), "prompt_tokens_max": max(lengths), "prompt_tokens_mean": sum(lengths) / len(lengths)}
    return Dataset.from_list(records), stats


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config, args.override)
    if args.resume == "latest" and not args.run_name:
        raise SystemExit("--resume latest needs --run_name of the run to continue")
    cont = continuation_plan(cfg, args.continue_from)
    if args.resume and args.resume != "latest":
        run_dir = Path(args.resume).resolve().parent
        run_name = run_dir.name
    else:
        run_name = args.run_name or default_run_name(cfg["experiment"] + (f"_stage{cont['stage']}" if cont else ""), int(cfg["seed"]))
        run_dir = resolve(cfg["paths"]["output_root"]) / run_name
    smoke = preflight.is_smoke(run_name)
    mock = bool(cfg.get("smoke", {}).get("mock_reward_clients"))
    if (mock or args.limit or args.max_steps > 0) and not smoke:
        print("refusing to start: mock rewards, --limit and --max_steps are for smoke runs (run name smoke_*)", file=sys.stderr)
        return 2
    problems = preflight.student_run(cfg)
    if problems and not smoke:
        print("refusing to start (real run):\n  - " + "\n  - ".join(problems), file=sys.stderr)
        return 2
    load_dotenv(REPO_ROOT / ".env")
    if not mock and not os.environ.get("OPENAI_API_KEY"):
        print("refusing to start: OPENAI_API_KEY is not set (tutee_error/.env)", file=sys.stderr)
        return 2

    import torch
    from accelerate import PartialState
    from transformers import AutoTokenizer, TrainerCallback
    from trl import GRPOConfig, GRPOTrainer

    from newman.orchestrator import RewardOrchestrator

    if not cfg["training"].get("log_profiling", False):
        from trl.extras import profiling

        profiling.ProfilingContext._log_metrics = lambda self, duration: None  # unstepped W&B points (see ../rl)

    state = PartialState()
    t, gen, srv = cfg["training"], cfg["generation"], cfg["servers"]["rollout"]
    per_step = int(t["per_device_train_batch_size"]) * state.num_processes * int(t["gradient_accumulation_steps"])
    if per_step != int(t["expected_completions_per_step"]):
        raise SystemExit(f"completions per step {per_step} != training.expected_completions_per_step "
                         f"{t['expected_completions_per_step']}: a different GPU count needs a batch/accumulation choice agreed "
                         "with the user (plan 9)")
    if per_step % int(gen["num_generations"]):
        raise SystemExit(f"completions per step {per_step} is not divisible by num_generations {gen['num_generations']}")

    taxonomy = Taxonomy.load(resolve(cfg["paths"]["taxonomy"]))
    tokenizer = AutoTokenizer.from_pretrained(cfg["policy"]["model"])
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    dataset, data_stats = build_dataset(cfg, tokenizer, taxonomy, args.limit, cont)

    prompts_per_step = per_step // int(gen["num_generations"])
    steps_per_epoch = math.ceil(len(dataset) / prompts_per_step)
    total_steps = args.max_steps if args.max_steps > 0 else int(steps_per_epoch * float(t["num_train_epochs"]))
    n_snap = int(round(float(t["num_train_epochs"]) / float(t["model_save_every_epochs"])))
    n_resume = int(round(float(t["num_train_epochs"]) / float(t["resume_save_every_epochs"])))
    resume_ratio = float(t["resume_save_every_epochs"]) / float(t["num_train_epochs"])  # Trainer: float < 1 = share of all steps
    need = n_snap * float(cfg["storage"]["model_snapshot_gb"]) + n_resume * float(cfg["storage"]["resume_checkpoint_gb"])
    disk = disk_problem(resolve(cfg["paths"]["output_root"]), need, float(cfg["storage"]["margin_gb"]))
    if disk and not smoke and not args.resume:
        print(f"refusing to start: {disk}", file=sys.stderr)
        return 2

    report_to = args.report_to or t["report_to"]
    if report_to == "wandb":
        os.environ["WANDB_PROJECT"] = t["wandb_project"]
        if not os.environ.get("WANDB_API_KEY"):
            report_to = "none"
        else:  # one W&B run per training run: a --resume continues <run>/wandb_run_id.txt
            id_file = run_dir / "wandb_run_id.txt"
            if not id_file.exists() and state.is_main_process:
                import secrets

                run_dir.mkdir(parents=True, exist_ok=True)
                id_file.write_text(secrets.token_hex(4) + "\n", encoding="utf-8")
            state.wait_for_everyone()
            if state.is_main_process:
                os.environ["WANDB_RUN_ID"] = id_file.read_text(encoding="utf-8").strip()
                os.environ["WANDB_RESUME"] = "allow"

    grpo_args = GRPOConfig(
        output_dir=str(run_dir), run_name=run_name, seed=int(cfg["seed"]),
        learning_rate=float(t["learning_rate"]), beta=float(t["beta"]), epsilon=float(t["epsilon"]), loss_type=t["loss_type"],
        scale_rewards=t["scale_rewards"], num_iterations=int(t["num_iterations"]), num_train_epochs=float(t["num_train_epochs"]),
        max_steps=args.max_steps, per_device_train_batch_size=int(t["per_device_train_batch_size"]),
        gradient_accumulation_steps=int(t["gradient_accumulation_steps"]), gradient_checkpointing=bool(t["gradient_checkpointing"]),
        bf16=bool(t["bf16"]), lr_scheduler_type=t["lr_scheduler_type"],
        warmup_steps=float(cont["warmup_ratio"] if cont else t["warmup_ratio"]),
        max_grad_norm=float(t["max_grad_norm"]), logging_steps=int(t["logging_steps"]),
        save_strategy="steps", save_steps=resume_ratio if resume_ratio < 1 else total_steps, save_total_limit=t["resume_save_total_limit"],
        report_to=report_to, ddp_timeout=int(t["ddp_timeout_s"]), mask_truncated_completions=bool(t["mask_truncated_completions"]),
        num_generations=int(gen["num_generations"]), max_completion_length=int(gen["max_completion_tokens"]),
        temperature=float(gen["temperature"]), top_p=float(gen["top_p"]), top_k=int(gen["top_k"]),
        repetition_penalty=float(gen["repetition_penalty"]),
        use_vllm=True, vllm_mode="server", vllm_server_host=srv["host"], vllm_server_port=int(srv["port"]),
        vllm_group_port=int(srv["group_port"]), vllm_server_timeout=600.0,
        vllm_importance_sampling_correction=bool(t["vllm_importance_sampling_correction"]),
        vllm_importance_sampling_mode=t["vllm_importance_sampling_mode"],
        vllm_importance_sampling_clip_max=t["vllm_importance_sampling_clip_max"],
        vllm_importance_sampling_clip_min=t["vllm_importance_sampling_clip_min"],
        use_bias_correction_kl=bool(t["use_bias_correction_kl"]),
        model_init_kwargs={"dtype": torch.bfloat16, "attn_implementation": cfg["policy"]["attn_implementation"]},
        shuffle_dataset=True, remove_unused_columns=False, log_completions=False, save_only_model=False,
    )
    orchestrator = RewardOrchestrator(cfg, tokenizer, run_dir, is_main=state.is_main_process, verifier_role="a")
    funcs, weights = orchestrator.reward_funcs()
    grpo_args.reward_weights = weights

    class NewmanGRPOTrainer(GRPOTrainer):
        """Adds the share of sequences whose vLLM importance weight is exactly 0 (masked by sequence_mask, or
        underflow): TRL logs the ratio's min/mean/max but not how many rollouts carry no gradient (plan 2.1)."""

        def _generate_and_score_completions(self, inputs):
            output = super()._generate_and_score_completions(inputs)
            ratio = output.get("importance_sampling_ratio")
            if ratio is not None:
                mode = "train" if self.model.training else "eval"
                if ratio.dim() == 2 and ratio.shape[1] == 1:  # sequence modes: one weight per completion
                    zero, total = (ratio == 0).sum().float(), torch.tensor(float(ratio.numel()), device=ratio.device)
                else:  # token modes: weight per completion token
                    mask = output["completion_mask"].bool()
                    zero, total = ((ratio == 0) & mask).sum().float(), mask.sum().float()
                zero, total = self.accelerator.gather(zero).sum(), self.accelerator.gather(total).sum()
                self._metrics[mode]["sampling/importance_sampling_zero_weight_fraction"].append((zero / total.clamp(min=1)).item())
            return output

    class EpochSave(TrainerCallback):
        """Model-only snapshot every `model_save_every_epochs` epochs -> epoch_checkpoints/epoch-X.X (never rotated)."""
        trainer = None
        save_at: dict[int, float] = {}

        def on_train_begin(self, args_, state_, control, **kw):
            every = float(t["model_save_every_epochs"])
            spe = state_.max_steps / float(args_.num_train_epochs)
            n = int(round(float(args_.num_train_epochs) / every))
            self.save_at = {int(round(k * every * spe)): k * every for k in range(1, n + 1)}
            self.save_at = {s: e for s, e in self.save_at.items() if 0 < s <= state_.max_steps}
            return control

        def on_step_end(self, args_, state_, control, **kw):
            if state_.global_step not in self.save_at:
                return control
            epoch = self.save_at[state_.global_step] + (cont["epoch_offset"] if cont else 0.0)
            out = run_dir / "epoch_checkpoints" / f"epoch-{epoch:.2f}"
            started = time.monotonic()
            self.trainer.save_model(str(out))  # collective under DeepSpeed: every rank calls it
            if state_.is_world_process_zero:
                tokenizer.save_pretrained(str(out))
                write_generation_config(out, cfg)
                write_json(out / "epoch_meta.json", {"epoch": epoch, "state_epoch": state_.epoch, "global_step": state_.global_step,
                                                     "saved_at": now_iso(), "save_s": round(time.monotonic() - started, 1),
                                                     "size_gb": round(dir_size_gb(out), 2)})
            return control

        def on_save(self, args_, state_, control, **kw):  # resume checkpoint written: record its measured size
            if state_.is_world_process_zero:
                ck = run_dir / f"checkpoint-{state_.global_step}"
                if ck.exists():
                    write_json(ck / "size_meta.json", {"size_gb": round(dir_size_gb(ck), 2), "measured_at": now_iso()})
            return control

    meta_name = "run_meta.json"
    if state.is_main_process:
        run_dir.mkdir(parents=True, exist_ok=True)
        prepared = resolve(cfg["paths"]["prepared_dir"])
        meta = {
            "created_at": now_iso(), "timezone": "Asia/Seoul", "run_name": run_name, "experiment": cfg["experiment"],
            "smoke": smoke, "preflight_warnings": problems, "config_chain": cfg["_config_chain"], "config_sha256": cfg["_config_sha256"],
            "config": public_config(cfg), "cli": vars(args), "git": git_state(), "versions": versions(),
            "num_processes": state.num_processes, "completions_per_step": per_step, "prompts_per_step": prompts_per_step,
            "steps_per_epoch_estimate": steps_per_epoch, "total_steps_estimate": total_steps,
            "data": {**data_stats, "train_sha256": sha256_file(prepared / "train.jsonl"), "prepared_meta": read_json(prepared / "meta.json")},
            "prompt_sha256": {k: sha256_file(resolve(v)) for k, v in cfg["prompts"].items()},
            "taxonomy": taxonomy.summary(), "approvals": approvals.snapshot(),
            "reward": {"reward_funcs": [f.__name__ for f in funcs], "reward_weights": weights, **orchestrator.describe()},
            "trl_loss": {k: getattr(grpo_args, k) for k in ("loss_type", "scale_rewards", "beta", "epsilon", "num_iterations",
                                                          "vllm_importance_sampling_correction", "vllm_importance_sampling_mode",
                                                          "vllm_importance_sampling_clip_max", "vllm_importance_sampling_clip_min",
                                                          "use_bias_correction_kl", "mask_truncated_completions")},
            "storage": {"projected_gb": need, "snapshots": n_snap, "resume_checkpoints": n_resume, "disk_warning": disk,
                        "resume_every_epochs": float(t["resume_save_every_epochs"]), "save_steps_ratio": resume_ratio},
            "deepspeed_config": os.environ.get("ACCELERATE_DEEPSPEED_CONFIG_FILE"),
            "gpus": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
            "report_to": report_to, "wandb_project": t["wandb_project"] if report_to == "wandb" else None,
            "continuation": cont,
        }
        if args.resume and (run_dir / meta_name).exists():  # keep the original run's metadata
            meta_name = f"run_meta.resume_{run_stamp()}.json"
        write_json(run_dir / meta_name, meta)
        print(json.dumps({k: meta[k] for k in ("run_name", "completions_per_step", "prompts_per_step", "total_steps_estimate")}, indent=2))

    epoch_cb = EpochSave()
    model = cfg["policy"]["model"]
    if cont:  # weights from the snapshot; TRL copies the reference from config._name_or_path, which stays the base model
        from transformers import AutoModelForCausalLM

        model = AutoModelForCausalLM.from_pretrained(str(resolve(cont["from"])), dtype=torch.bfloat16,
                                                     attn_implementation=cfg["policy"]["attn_implementation"])
        model.config._name_or_path = cfg["policy"]["model"]
    trainer = NewmanGRPOTrainer(model=model, reward_funcs=funcs, args=grpo_args, train_dataset=dataset,
                                processing_class=tokenizer, callbacks=[epoch_cb])
    if cont:
        ref = getattr(trainer.ref_model, "module", trainer.ref_model)
        if ref is None or ref.config._name_or_path != cfg["policy"]["model"]:
            raise SystemExit(f"continuation: the KL reference is {getattr(getattr(ref, 'config', None), '_name_or_path', None)}, "
                             f"not {cfg['policy']['model']}")
    epoch_cb.trainer = trainer
    trainer.train(resume_from_checkpoint=True if args.resume == "latest" else args.resume)
    trainer.save_model(str(run_dir / "final"))
    if state.is_main_process:
        tokenizer.save_pretrained(str(run_dir / "final"))
        write_generation_config(run_dir / "final", cfg)
        meta = read_json(run_dir / meta_name)
        meta.update(finished_at=now_iso(),
                    snapshots=[read_json(p / "epoch_meta.json") for p in sorted((run_dir / "epoch_checkpoints").glob("epoch-*"))],
                    resume_checkpoints=sorted(p.name for p in run_dir.glob("checkpoint-*")))
        write_json(run_dir / meta_name, meta)
        print(f"done: {rel(run_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
