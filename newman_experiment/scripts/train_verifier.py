#!/usr/bin/env python3
"""Full-parameter SFT of one binary verifier on its own training half (plan 6): A = RL reward, B = test verifier.

Input (Q, incorrect solution S, target Newman stage N, target source error type E) -> `aligned` / `not_aligned`;
loss on the assistant answer only (label + end tokens). Each verifier starts from its own public backbone. No
validation split (user rule 5): a model-only snapshot after every epoch (epoch_checkpoints/epoch-K, all kept); the
checkpoint is chosen afterwards on the SFT test (scripts/eval_verifier.py). Full optimizer-state checkpoints only if
training.resume_save_steps is set (all kept too).

Usage (from newman_experiment/, `source env.sh sft`):
  bash scripts/run_train_verifier.sh configs/verifier_half_a.yaml
  bash scripts/run_train_verifier.sh configs/verifier_half_b.yaml
  smoke: bash scripts/run_train_verifier.sh configs/smoke/verifier_small.yaml --run_name smoke_verifier --limit 64 --max_steps 4
Output dir outputs/<run_name> = W&B run name, <run_name> = <experiment>_seed42_<YYYYmmdd_HHMMSS> (Asia/Seoul).
"""

from __future__ import annotations

import argparse
import dataclasses
import inspect
import math
import os
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
from newman.verifier_format import build_messages, encode_example, load_verifier_prompt  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--override", action="append", default=[], help="a.b.c=value (YAML value), repeatable")
    p.add_argument("--run_name", default=None, help="default <experiment>_seed<seed>_<YYYYmmdd_HHMMSS> (Asia/Seoul)")
    p.add_argument("--resume", default=None, help="a checkpoint-N dir of this run (only with training.resume_save_steps)")
    p.add_argument("--report_to", default=None)
    p.add_argument("--limit", type=int, default=None, help="smoke: first N pair rows")
    p.add_argument("--max_steps", type=int, default=None, help="smoke: stop after N optimizer steps")
    return p.parse_args()


def encode_rows(rows, tokenizer, prompt, taxonomy, max_len):
    out = []
    for row in rows:
        enc = encode_example(tokenizer, build_messages(prompt, taxonomy, row, with_target=True))
        if len(enc["input_ids"]) > max_len:  # prepare_data.py drops these; truncation would cut the label
            raise SystemExit(f"{row['pair_id']}: {len(enc['input_ids'])} tokens > max_seq_length {max_len}")
        out.append(enc)
    return out


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config, args.override)
    t = cfg["training"]
    seed = int(cfg["seed"])
    if args.resume:
        run_dir = Path(args.resume).resolve().parent
        run_name = run_dir.name
    else:
        run_name = args.run_name or default_run_name(cfg["experiment"], seed)
        run_dir = resolve(t["output_root"]) / run_name
    smoke = preflight.is_smoke(run_name)
    if (args.limit or args.max_steps) and not smoke:
        print("refusing to start: --limit / --max_steps are for smoke runs (run name smoke_*)", file=sys.stderr)
        return 2
    problems = preflight.verifier_training(cfg)
    if problems and not smoke:
        print("refusing to start (real run):\n  - " + "\n  - ".join(problems), file=sys.stderr)
        return 2
    load_dotenv(REPO_ROOT / ".env")  # WANDB_API_KEY, HF_TOKEN

    import torch
    import transformers
    from datasets import Dataset
    from transformers import (AutoModelForCausalLM, AutoTokenizer, DataCollatorForSeq2Seq, Trainer, TrainerCallback,
                              TrainingArguments, set_seed)

    set_seed(seed)
    world = int(os.environ.get("WORLD_SIZE", "1"))
    effective = int(t["per_device_train_batch_size"]) * int(t["gradient_accumulation_steps"]) * world
    if effective != int(t["expected_effective_batch"]):
        print(f"refusing to start: effective batch {effective} != training.expected_effective_batch "
              f"{t['expected_effective_batch']} (a different GPU count needs a per-device/accumulation choice agreed "
              "with the user)", file=sys.stderr)
        return 2

    taxonomy = Taxonomy.load(resolve(cfg["taxonomy"]))
    prompt = load_verifier_prompt(cfg["prompts"]["system"], cfg["prompts"]["user"])
    model_name = cfg["model"]["name"]
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = t["padding_side"]
    data_path = resolve(cfg["data_dir"]) / cfg["data_file"]
    rows = read_jsonl(data_path)
    if args.limit:
        rows = rows[: args.limit]
    wrong_region = [r["pair_id"] for r in rows if r["region"] != f"half_{cfg['half'].lower()}"]
    if wrong_region:
        raise SystemExit(f"{data_path} holds pairs of another region: {wrong_region[:3]}")
    train_ds = Dataset.from_list(encode_rows(rows, tokenizer, prompt, taxonomy, int(cfg["max_seq_length"])))

    steps_per_epoch = math.ceil(len(train_ds) / (int(t["per_device_train_batch_size"]) * world) / int(t["gradient_accumulation_steps"]))
    epochs = int(t["num_train_epochs"])
    n_resume = (steps_per_epoch * epochs) // int(t["resume_save_steps"]) if t.get("resume_save_steps") else 0
    need = epochs * float(cfg["storage"]["model_snapshot_gb"]) + n_resume * float(cfg["storage"]["resume_checkpoint_gb"])
    disk = disk_problem(resolve(t["output_root"]), need, float(cfg["storage"]["margin_gb"]))
    if disk and not smoke:
        print(f"refusing to start: {disk}", file=sys.stderr)
        return 2

    report_to = args.report_to or t["report_to"]
    if report_to == "wandb":
        os.environ["WANDB_PROJECT"] = t["wandb_project"]
        if not os.environ.get("WANDB_API_KEY"):
            report_to = "none"
        else:  # one W&B run per training run; a resume continues the id in <run>/wandb_run_id.txt
            import secrets

            run_dir.mkdir(parents=True, exist_ok=True)
            id_file = run_dir / "wandb_run_id.txt"
            if not id_file.exists():
                id_file.write_text(secrets.token_hex(4) + "\n", encoding="utf-8")
            os.environ["WANDB_RUN_ID"] = id_file.read_text(encoding="utf-8").strip()
            os.environ["WANDB_RESUME"] = "allow"

    dtype_kw = "dtype" if int(transformers.__version__.split(".")[0]) >= 5 else "torch_dtype"
    model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True, **{dtype_kw: torch.bfloat16})
    model.config.use_cache = False

    fields = {f.name for f in dataclasses.fields(TrainingArguments)}
    resume_steps = t.get("resume_save_steps")
    kwargs = dict(
        output_dir=str(run_dir), run_name=run_name, seed=seed, data_seed=seed,
        num_train_epochs=epochs, per_device_train_batch_size=int(t["per_device_train_batch_size"]),
        gradient_accumulation_steps=int(t["gradient_accumulation_steps"]), learning_rate=float(t["learning_rate"]),
        weight_decay=float(t["weight_decay"]), lr_scheduler_type=t["lr_scheduler_type"], max_grad_norm=float(t["max_grad_norm"]),
        bf16=bool(t["bf16"]), gradient_checkpointing=bool(t["gradient_checkpointing"]),
        gradient_checkpointing_kwargs={"use_reentrant": False}, logging_steps=int(t["logging_steps"]),
        report_to=report_to, dataloader_num_workers=int(t["dataloader_num_workers"]),
        save_strategy="steps" if resume_steps else "no", save_total_limit=None, save_only_model=False,
    )
    if resume_steps:
        kwargs["save_steps"] = int(resume_steps)
    kwargs["eval_strategy" if "eval_strategy" in fields else "evaluation_strategy"] = "no"
    kwargs["warmup_ratio" if "warmup_ratio" in fields else "warmup_steps"] = float(t["warmup_ratio"])  # transformers 5: float < 1 = ratio
    if args.max_steps:
        kwargs["max_steps"] = args.max_steps
    training_args = TrainingArguments(**kwargs)

    meta_path = run_dir / "run_meta.json"

    class EpochSnapshot(TrainerCallback):
        """Model-only snapshot after every epoch (never rotated); its size is measured and logged."""
        trainer = None
        count = 0

        def _save(self, state, reason):
            self.count += 1
            out = run_dir / "epoch_checkpoints" / f"epoch-{self.count}"
            started = time.monotonic()
            self.trainer.save_model(str(out))
            if state.is_world_process_zero:
                tokenizer.save_pretrained(str(out))
                size = dir_size_gb(out)
                write_json(out / "epoch_meta.json", {"epoch": self.count, "state_epoch": state.epoch, "global_step": state.global_step,
                                                     "reason": reason, "size_gb": round(size, 2), "saved_at": now_iso(),
                                                     "save_s": round(time.monotonic() - started, 1)})
            torch.cuda.empty_cache()

        def on_epoch_end(self, args, state, control, **kw):
            if t.get("snapshot_every_epoch", True):
                self._save(state, "epoch_end")
            return control

        def on_train_end(self, args, state, control, **kw):
            if args.max_steps and args.max_steps > 0 and self.count == 0:  # smoke run shorter than one epoch
                self._save(state, "max_steps")
            return control

    class RecordOptimizer(TrainerCallback):
        """The optimizer actually built (class, betas, eps, weight decay) goes into run_meta.json (plan 6.2)."""

        def on_train_begin(self, args, state, control, optimizer=None, **kw):
            if not state.is_world_process_zero or optimizer is None:
                return control
            chain, opt, adamw_mode = [], optimizer, None
            while opt is not None and len(chain) < 4:
                chain.append(f"{type(opt).__module__}.{type(opt).__name__}")
                adamw_mode = getattr(opt, "adamw_mode", adamw_mode)  # DeepSpeedCPUAdam: decoupled weight decay if True
                opt = getattr(opt, "optimizer", None)
            groups = getattr(optimizer, "param_groups", None) or []
            hp = {k: groups[0].get(k) for k in ("lr", "betas", "eps", "weight_decay") if groups and k in groups[0]}
            meta = read_json(meta_path)
            meta["optimizer"] = {"classes": chain, "param_group_0": {k: (list(v) if isinstance(v, tuple) else v) for k, v in hp.items()},
                                 "adamw_mode": adamw_mode, "total_optimizer_steps": state.max_steps}
            write_json(meta_path, meta)
            return control

    snapshot = EpochSnapshot()
    trainer_kw = dict(model=model, args=training_args, train_dataset=train_ds,
                      data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True, label_pad_token_id=-100),
                      callbacks=[snapshot, RecordOptimizer()])
    trainer_kw["processing_class" if "processing_class" in inspect.signature(Trainer.__init__).parameters else "tokenizer"] = tokenizer
    trainer = Trainer(**trainer_kw)
    snapshot.trainer = trainer

    run_dir.mkdir(parents=True, exist_ok=True)
    data_meta = read_json(resolve(cfg["data_dir"]) / "meta.json")
    meta = {
        "created_at": now_iso(), "timezone": "Asia/Seoul", "run_name": run_name, "experiment": cfg["experiment"],
        "role": cfg["role"], "half": cfg["half"], "smoke": smoke, "preflight_warnings": problems,
        "config_chain": cfg["_config_chain"], "config_sha256": cfg["_config_sha256"], "config": public_config(cfg),
        "cli": vars(args), "git": git_state(), "versions": versions(), "model": model_name,
        "data": {"file": rel(data_path), "sha256": sha256_file(data_path), "pair_rows": len(train_ds),
                 "anchors": len({r["anchor_sample_id"] for r in rows}), "prepared_meta_mapping_verified": data_meta.get("mapping_verified"),
                 "limit": args.limit},
        "prompt": {k: prompt[k] for k in ("system_path", "user_path", "system_sha256", "user_sha256")},
        "taxonomy": taxonomy.summary(), "approvals": approvals.snapshot(["taxonomy_definitions", "verifier_prompt", "verifier_backbones"]),
        "effective_batch": effective, "world_size": world, "steps_per_epoch_estimate": steps_per_epoch,
        "storage": {"projected_gb": need, "snapshots": epochs, "resume_checkpoints": n_resume, "disk_warning": disk},
        "deepspeed_enabled": bool(getattr(trainer, "is_deepspeed_enabled", False)),
        "deepspeed_config": os.environ.get("ACCELERATE_DEEPSPEED_CONFIG_FILE"),
        "gpus": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
        "report_to": report_to, "wandb_project": t["wandb_project"] if report_to == "wandb" else None,
    }
    if args.resume and meta_path.exists():
        meta_path = run_dir / f"run_meta.resume_{run_stamp()}.json"
    write_json(meta_path, meta)
    print(f"run {run_name} · {len(train_ds)} pair rows · effective batch {effective} · deepspeed {meta['deepspeed_enabled']} · {run_dir}")

    trainer.train(resume_from_checkpoint=args.resume)

    final = read_json(meta_path)
    snaps = sorted((run_dir / "epoch_checkpoints").glob("epoch-*"), key=lambda p: int(p.name.split("-")[1]))
    final.update(finished_at=now_iso(), log_history=trainer.state.log_history,
                 snapshots=[{**read_json(s / "epoch_meta.json"), "path": rel(s)} for s in snaps],
                 resume_checkpoints=sorted(p.name for p in run_dir.glob("checkpoint-*")))
    write_json(meta_path, final)
    print(f"snapshots kept: {[s.name for s in snaps]} -> python scripts/eval_verifier.py --config {args.config} --run_dir {rel(run_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
