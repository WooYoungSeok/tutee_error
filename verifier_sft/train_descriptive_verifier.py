#!/usr/bin/env python3
"""Full-parameter SFT of Qwen2.5-Math-7B-Instruct as a descriptive error verifier.

Input (Q, incorrect solution S, error description C) -> `aligned` / `not_aligned`.
Loss only on the assistant answer tokens. Reads the fixed pair files written by
prepare_descriptive_pairs.py; nothing is sampled here. The best checkpoint is
chosen by validation loss; the test split is never loaded.

Usage (from verifier_sft/, same launch as the reward_model scripts):
    CUDA_VISIBLE_DEVICES=0 accelerate launch --config_file accelerate_config_ds_single.yaml \
        train_descriptive_verifier.py
Smoke run:
    ... train_descriptive_verifier.py --limit 64 --max_steps 4 --report_to none
"""

from __future__ import annotations

import argparse
import dataclasses
import inspect
import platform
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verifier_common import (  # noqa: E402
    build_messages,
    encode_example,
    load_config,
    load_prompt,
    read_jsonl,
    resolve,
    sha256_file,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=None)
    parser.add_argument("--output_dir", default=None, help="default: <checkpoint_dir>/<experiment>_<timestamp>")
    parser.add_argument("--resume_from_checkpoint", default=None)
    parser.add_argument("--report_to", default=None, help="override training.report_to (e.g. none)")
    parser.add_argument("--limit", type=int, default=None, help="smoke test: first N pairs of each file")
    parser.add_argument("--max_steps", type=int, default=None, help="smoke test: stop after N steps")
    parser.add_argument("--model_name", default=None, help="smoke test only: a small model instead of model.name")
    return parser.parse_args()


def encode_file(path: Path, tokenizer, prompt: dict, max_len: int, limit: int | None) -> list[dict]:
    rows = read_jsonl(path)
    if limit:
        rows = rows[:limit]
    encoded = []
    for row in rows:
        enc = encode_example(tokenizer, build_messages(prompt, row, with_target=True))
        if len(enc["input_ids"]) > max_len:
            # prepare_descriptive_pairs.py already drops these; silent truncation would cut the label
            raise SystemExit(f"{row['pair_id']}: {len(enc['input_ids'])} tokens > max_seq_length {max_len}")
        encoded.append(enc)
    return encoded


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    tcfg = config["training"]
    seed = config["seed"]
    max_len = config["model"]["max_seq_length"]
    model_name = args.model_name or config["model"]["name"]

    import torch
    import transformers
    from datasets import Dataset
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForSeq2Seq,
        Trainer,
        TrainerCallback,
        TrainingArguments,
        set_seed,
    )

    set_seed(seed)
    output_dir = Path(args.output_dir) if args.output_dir else resolve(tcfg["checkpoint_dir"]) / (
        f"{config['experiment']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    if args.resume_from_checkpoint and not args.output_dir:
        output_dir = Path(args.resume_from_checkpoint).parent

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = tcfg["padding_side"]

    prompt = load_prompt(config)
    data_dir = resolve(config["output"]["data_dir"])
    train_path, val_path = data_dir / "train.jsonl", data_dir / "validation.jsonl"
    train_ds = Dataset.from_list(encode_file(train_path, tokenizer, prompt, max_len, args.limit))
    val_ds = Dataset.from_list(encode_file(val_path, tokenizer, prompt, max_len, args.limit))
    print(f"train examples {len(train_ds)} · validation examples {len(val_ds)} (test is not loaded)")

    dtype_kw = "dtype" if int(transformers.__version__.split(".")[0]) >= 5 else "torch_dtype"
    model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True, **{dtype_kw: torch.bfloat16})
    model.config.use_cache = False

    arg_fields = {f.name for f in dataclasses.fields(TrainingArguments)}
    strategy = tcfg["eval_and_save"]
    kwargs = dict(
        output_dir=str(output_dir),
        num_train_epochs=tcfg["num_train_epochs"],
        per_device_train_batch_size=tcfg["per_device_train_batch_size"],
        per_device_eval_batch_size=tcfg["per_device_eval_batch_size"],
        gradient_accumulation_steps=tcfg["gradient_accumulation_steps"],
        learning_rate=tcfg["learning_rate"],
        weight_decay=tcfg["weight_decay"],
        bf16=tcfg["bf16"],
        bf16_full_eval=tcfg["bf16"],
        gradient_checkpointing=tcfg["gradient_checkpointing"],
        gradient_checkpointing_kwargs={"use_reentrant": False},
        logging_steps=tcfg["logging_steps"],
        save_strategy=strategy,
        load_best_model_at_end=True,
        metric_for_best_model=tcfg["metric_for_best_model"],
        greater_is_better=False,
        save_total_limit=tcfg["save_total_limit"],
        report_to=args.report_to or tcfg["report_to"],
        run_name=output_dir.name,
        seed=seed,
        data_seed=seed,
        dataloader_num_workers=tcfg["dataloader_num_workers"],
    )
    # transformers renamed evaluation_strategy -> eval_strategy (4.41)
    kwargs["eval_strategy" if "eval_strategy" in arg_fields else "evaluation_strategy"] = strategy
    # transformers 5 dropped warmup_ratio; warmup_steps takes a float in [0, 1) as a ratio
    kwargs["warmup_ratio" if "warmup_ratio" in arg_fields else "warmup_steps"] = tcfg["warmup_ratio"]
    if args.max_steps:
        kwargs["max_steps"] = args.max_steps
        if strategy == "epoch":  # a smoke run may end before the first epoch
            kwargs["eval_strategy" if "eval_strategy" in arg_fields else "evaluation_strategy"] = "steps"
            kwargs.update(save_strategy="steps", eval_steps=args.max_steps, save_steps=args.max_steps)
    training_args = TrainingArguments(**kwargs)

    collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True, label_pad_token_id=-100)

    class ClearCacheCallback(TrainerCallback):
        def on_save(self, args, state, control, **kw):
            torch.cuda.empty_cache()

        def on_evaluate(self, args, state, control, **kw):
            torch.cuda.empty_cache()

    trainer_kw = dict(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=collator,
        callbacks=[ClearCacheCallback()],
    )
    # transformers 5 takes processing_class; 4.x takes tokenizer
    if "processing_class" in inspect.signature(Trainer.__init__).parameters:
        trainer_kw["processing_class"] = tokenizer
    else:
        trainer_kw["tokenizer"] = tokenizer
    trainer = Trainer(**trainer_kw)
    print(f"deepspeed enabled: {getattr(trainer, 'is_deepspeed_enabled', 'unknown')} · output {output_dir}")

    run_info = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "experiment": config["experiment"],
        "model": model_name,
        "config": {"path": config["_config_path"], "sha256": config["_config_sha256"]},
        "data": {p.name: sha256_file(p) for p in (train_path, val_path)},
        "prompt": {"system_sha256": prompt["system_sha256"], "user_sha256": prompt["user_sha256"]},
        "train_examples": len(train_ds),
        "validation_examples": len(val_ds),
        "limit": args.limit,
        "max_steps": args.max_steps,
        "versions": {"python": platform.python_version(), "torch": torch.__version__, "transformers": transformers.__version__},
        "deepspeed_enabled": bool(getattr(trainer, "is_deepspeed_enabled", False)),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "run_info.json", run_info)

    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)

    final_dir = output_dir / "final"
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    run_info.update(
        finished_at=datetime.now().isoformat(timespec="seconds"),
        best_model_checkpoint=trainer.state.best_model_checkpoint,
        best_metric=trainer.state.best_metric,
        log_history=trainer.state.log_history,
    )
    write_json(output_dir / "run_info.json", run_info)
    print(f"best checkpoint {trainer.state.best_model_checkpoint} (eval_loss {trainer.state.best_metric}) -> {final_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
