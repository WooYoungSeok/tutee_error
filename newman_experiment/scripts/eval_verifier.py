#!/usr/bin/env python3
"""Evaluate every epoch snapshot of a verifier run on the fixed SFT test pairs and choose the checkpoint (plan 6.3).

Greedy decoding with the training chat template (max_new_tokens 10, repetition penalty 1.0), exact match: anything
but `aligned` / `not_aligned` is invalid and counts as wrong. Teacher-forced test loss on the answer tokens (label
+ eos), token-weighted. Breakdowns: same-/different-stage negatives, type, stage, dataset, unit eligibility; 95% CIs
from a question-group bootstrap. The checkpoint is chosen on test by evaluation.selection_rule (user rule 5: chosen
on test, so optimistic by design); while the rule is REQUIRED everything is computed and no checkpoint is named.

Usage (from newman_experiment/, `source env.sh sft`):
  CUDA_VISIBLE_DEVICES=1 python scripts/eval_verifier.py --config configs/verifier_half_a.yaml --run_dir outputs/<run> [--include_base]
Outputs: <run>/test_eval/<epoch-K|base>/{predictions.jsonl, generation_meta.json, metrics.json}, <run>/test_eval/summary.json,
         W&B test/* in the training run.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman.common import (  # noqa: E402
    REPO_ROOT,
    REQUIRED,
    load_config,
    load_dotenv,
    now_iso,
    read_json,
    read_jsonl,
    rel,
    resolve,
    sha256_file,
    write_json,
    write_jsonl,
)
from newman.metrics import bootstrap_ci, rank_checkpoints, verifier_metrics  # noqa: E402
from newman.taxonomy import Taxonomy  # noqa: E402
from newman.verifier_format import (  # noqa: E402
    _vc,
    build_messages,
    encode_example,
    generation_prompt,
    load_verifier_prompt,
    parse_prediction,
)

SUMMARY_KEYS = ("accuracy", "macro_f1", "negative_recall", "negative_false_acceptance", "positive_recall", "invalid_rate",
                "pair_accuracy", "test_loss")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--override", action="append", default=[], help="a.b.c=value (YAML value), repeatable")
    p.add_argument("--run_dir", required=True)
    p.add_argument("--include_base", action="store_true", help="also the untrained backbone (reference)")
    p.add_argument("--limit", type=int, default=None, help="smoke: first N test rows (written as <name>_limitN)")
    p.add_argument("--rescore", action="store_true")
    p.add_argument("--only", action="append", default=None, help="evaluate only these snapshots (e.g. epoch-5), repeatable")
    p.add_argument("--eval_dir", default="test_eval", help="output folder inside the run (another name keeps test_eval/ untouched)")
    p.add_argument("--no_wandb", action="store_true")
    return p.parse_args()


def evaluate_one(cfg, model_path: str, rows, prompt, taxonomy, out_dir: Path) -> dict:
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer, DataCollatorForSeq2Seq

    ev = cfg["evaluation"]
    tok = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    dtype_kw = "dtype" if int(transformers.__version__.split(".")[0]) >= 5 else "torch_dtype"
    model = AutoModelForCausalLM.from_pretrained(model_path, trust_remote_code=True, device_map="auto", **{dtype_kw: torch.bfloat16})
    model.eval()
    device = next(model.parameters()).device

    started = time.monotonic()
    prompts = [generation_prompt(tok, build_messages(prompt, taxonomy, r, with_target=False)) for r in rows]
    raw: list[str] = []
    bs = int(ev["batch_size"])
    for i in range(0, len(prompts), bs):
        batch = tok(prompts[i:i + bs], return_tensors="pt", padding=True, add_special_tokens=False).to(device)
        with torch.no_grad():
            out = model.generate(**batch, max_new_tokens=int(ev["max_new_tokens"]), do_sample=False, temperature=None,
                                 top_p=None, top_k=None, repetition_penalty=float(ev["repetition_penalty"]),
                                 pad_token_id=tok.pad_token_id)
        raw += tok.batch_decode(out[:, batch["input_ids"].shape[1]:], skip_special_tokens=True)
    gen_s = time.monotonic() - started

    # teacher-forced loss on the answer tokens, same collator (left padding) as training
    collator = DataCollatorForSeq2Seq(tokenizer=tok, padding=True, label_pad_token_id=-100)
    encoded = [encode_example(tok, build_messages(prompt, taxonomy, r, with_target=True)) for r in rows]
    total, count, lbs = 0.0, 0, int(ev["loss_batch_size"])
    for i in range(0, len(encoded), lbs):
        batch = collator(encoded[i:i + lbs])
        batch = {k: v.to(device) for k, v in batch.items()}
        with torch.no_grad():
            logits = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).logits
        labels = batch["labels"][:, 1:]
        mask = labels != -100
        sel = logits[:, :-1][mask].float()
        total += float(torch.nn.functional.cross_entropy(sel, labels[mask], reduction="sum"))
        count += int(mask.sum())
    test_loss = total / count if count else None
    del model
    torch.cuda.empty_cache()

    preds = []
    for r, text in zip(rows, raw):
        pred = parse_prediction(text)
        preds.append({**r, "raw_output": text, "prediction": pred, "correct": pred == r["target"]})
    metrics = verifier_metrics(preds, int(ev["min_support"]))
    metrics["test_loss"] = test_loss
    metrics["bootstrap_ci_question_groups"] = bootstrap_ci(preds, int(ev["bootstrap_samples"]), int(cfg["seed"]),
                                                               metrics=("accuracy", "macro_f1", "pair_accuracy"))
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "predictions.jsonl", preds)
    gen_meta = {"checkpoint": model_path, "created_at": now_iso(), "timezone": "Asia/Seoul", "rows": len(rows),
                "decoding": {"greedy": True, "max_new_tokens": int(ev["max_new_tokens"]), "repetition_penalty": float(ev["repetition_penalty"]),
                             "batch_size": bs, "padding_side": "left"},
                "loss": {"tokens": count, "reduction": "token-weighted mean over label + eos tokens", "batch_size": lbs},
                "prompt": {k: prompt[k] for k in ("system_sha256", "user_sha256")}, "taxonomy_sha256": taxonomy.sha256,
                "generation_s": round(gen_s, 1)}
    write_json(out_dir / "generation_meta.json", gen_meta)
    result = {"name": out_dir.name, "checkpoint": model_path, "metrics": metrics, "generation": gen_meta}
    write_json(out_dir / "metrics.json", result)
    return result


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config, args.override)
    load_dotenv(REPO_ROOT / ".env")
    run_dir = resolve(args.run_dir)
    taxonomy = Taxonomy.load(resolve(cfg["taxonomy"]))
    prompt = load_verifier_prompt(cfg["prompts"]["system"], cfg["prompts"]["user"])
    data_path = resolve(cfg["data_dir"]) / cfg["evaluation"]["split_file"]
    rows = read_jsonl(data_path)
    if args.limit:
        rows = rows[: args.limit]
    if any(r["region"] != "test" for r in rows):
        raise SystemExit(f"{data_path} is not the test region")
    data_sha = sha256_file(data_path)

    jobs = []
    if args.include_base:
        jobs.append(("base", cfg["model"]["name"]))
    for d in sorted((run_dir / "epoch_checkpoints").glob("epoch-*"), key=lambda p: float(p.name.split("-")[1])):
        if args.only is None or d.name in args.only:
            jobs.append((d.name, str(d)))
    if not jobs:
        raise SystemExit(f"no epoch_checkpoints in {run_dir}")
    results = {}
    for name, path in jobs:
        out_name = f"{name}_limit{args.limit}" if args.limit else name
        out_dir = run_dir / args.eval_dir / out_name
        done = out_dir / "metrics.json"
        if done.exists() and not args.rescore:
            prev = read_json(done)
            if prev["checkpoint"] == path and prev.get("data_sha256") == data_sha:
                results[name] = prev
                continue
        print(f"== {name}: {path}", flush=True)
        res = evaluate_one(cfg, path, rows, prompt, taxonomy, out_dir)
        res["data_sha256"] = data_sha
        write_json(done, res)
        results[name] = res
        m = res["metrics"]
        print(f"   accuracy {m['accuracy']:.4f} · macro-F1 {m['macro_f1']:.4f} · neg. false acceptance {m['negative_false_acceptance']:.4f}"
              f" · invalid {m['invalid_rate']:.4f} · test loss {m['test_loss']:.4f}", flush=True)

    table = {k: {m: v["metrics"][m] for m in SUMMARY_KEYS} for k, v in results.items()}
    rule = cfg["evaluation"]["selection_rule"]
    epochs = {k: v for k, v in table.items() if k.startswith("epoch-")}
    if rule == REQUIRED:
        ranking, best, note = None, None, "evaluation.selection_rule is REQUIRED (open decision): no checkpoint chosen"
    else:
        ranking = rank_checkpoints(epochs, rule)
        best, note = ranking[0], "chosen on the test split (user rule 5): the chosen checkpoint's test score is optimistic"
    summary = {"created_at": now_iso(), "timezone": "Asia/Seoul", "run_dir": rel(run_dir), "config": args.config,
               "data": {"path": rel(data_path), "sha256": data_sha, "rows": len(rows), "limit": args.limit},
               "selection_rule": rule, "ranking": ranking, "best_checkpoint": best,
               "best_checkpoint_path": results[best]["checkpoint"] if best else None, "selection_note": note, "results": table}
    if not args.limit:
        write_json(run_dir / args.eval_dir / "summary.json", summary)
    print(f"best: {best} ({note})")

    if args.no_wandb or args.limit or args.only or args.eval_dir != "test_eval":
        return 0
    meta = read_json(run_dir / "run_meta.json") if (run_dir / "run_meta.json").exists() else {}
    id_file = run_dir / "wandb_run_id.txt"
    if not id_file.exists() or not meta.get("wandb_project"):
        print("no W&B run recorded for this training run; results are on disk only")
        return 0
    try:
        import wandb

        run = wandb.init(project=meta["wandb_project"], id=id_file.read_text().strip(), resume="must")
        run.define_metric("test/epoch")
        run.define_metric("test/*", step_metric="test/epoch")
        for name, m in sorted(epochs.items(), key=lambda kv: float(kv[0].split("-")[1])):
            run.log({"test/epoch": float(name.split("-")[1]), **{f"test/{k}": v for k, v in m.items() if v is not None}})
        run.summary.update({"test/best_checkpoint (chosen on test)": best, "test/selection_rule": str(rule)})
        run.finish()
    except Exception as exc:  # noqa: BLE001 - results are already on disk
        print(f"W&B logging failed ({type(exc).__name__}: {exc}); results are in {run_dir / 'test_eval'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
