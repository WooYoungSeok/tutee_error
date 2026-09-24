#!/usr/bin/env python3
"""Evaluate a verifier (the SFT checkpoint or the untuned backbone) on a fixed split.

Same system/user template as training, greedy decoding, short answers. An
answer counts only if, after stripping whitespace, it is exactly `aligned` or
`not_aligned`; anything else is `invalid` and counts as wrong in every metric.

Usage (from verifier_sft/):
    python eval_descriptive_verifier.py --model_path Qwen/Qwen2.5-Math-7B-Instruct --name baseline
    python eval_descriptive_verifier.py --model_path checkpoints/<run>/final --name sft
    # auxiliary shortcut diagnostics (not part of the main comparison)
    python eval_descriptive_verifier.py --model_path checkpoints/<run>/final --name sft_no_solution --ablation no_solution

Writes <evaluation.output_dir>/<name>/{predictions.jsonl,metrics.json} and <output.report_dir>/eval_<name>.md
(<name>_limit<N> for a --limit run).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verifier_common import (  # noqa: E402
    NOT_ALIGNED,
    bootstrap_ci,
    breakdown,
    build_messages,
    compute_metrics,
    generation_prompt,
    load_config,
    load_prompt,
    parse_prediction,
    read_jsonl,
    resolve,
    sha256_file,
    write_json,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=None)
    parser.add_argument("--model_path", required=True, help="checkpoint dir or hub id (backbone baseline)")
    parser.add_argument("--name", required=True, help="output name, e.g. baseline / sft")
    parser.add_argument("--split", default=None, help="default: evaluation.split (test)")
    parser.add_argument("--ablation", default="none", choices=["none", "no_solution", "description_only"])
    parser.add_argument("--batch_size", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None, help="smoke test: first N rows")
    return parser.parse_args()


def fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.4f}"


def metric_rows(results: dict[str, dict[str, Any]]) -> list[list[Any]]:
    return [
        [k, m["n"], fmt(m["accuracy"]), fmt(m["macro_f1"]), fmt(m["negative_acceptance_rate"]),
         fmt(m["positive_rejection_rate"]), fmt(m["invalid_rate"]), fmt(m["pair_accuracy"])]
        for k, m in results.items()
    ]


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join([" --- "] * len(headers)) + "|"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


HEADERS = ["group", "n", "accuracy", "macro-F1", "neg. acceptance", "pos. rejection", "invalid", "pair acc."]


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    ecfg = config["evaluation"]
    split = args.split or ecfg["split"]
    batch_size = args.batch_size or ecfg["batch_size"]

    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    data_path = resolve(config["output"]["data_dir"]) / f"{split}.jsonl"
    rows = read_jsonl(data_path)
    if args.limit:
        rows = rows[: args.limit]
    prompt = load_prompt(config, ablation=args.ablation)

    tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"
    dtype_kw = "dtype" if int(transformers.__version__.split(".")[0]) >= 5 else "torch_dtype"
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path, trust_remote_code=True, device_map="auto", **{dtype_kw: torch.bfloat16}
    )
    model.eval()
    device = next(model.parameters()).device

    prompts = [generation_prompt(tokenizer, build_messages(prompt, r, with_target=False)) for r in rows]
    raw_outputs: list[str] = []
    for start in range(0, len(prompts), batch_size):
        batch = tokenizer(prompts[start:start + batch_size], return_tensors="pt", padding=True, add_special_tokens=False).to(device)
        with torch.no_grad():
            out = model.generate(
                **batch,
                max_new_tokens=ecfg["max_new_tokens"],
                do_sample=False,
                temperature=None,
                top_p=None,
                top_k=None,
                pad_token_id=tokenizer.pad_token_id,
            )
        new_tokens = out[:, batch["input_ids"].shape[1]:]
        raw_outputs += tokenizer.batch_decode(new_tokens, skip_special_tokens=True)
        print(f"  {min(start + batch_size, len(prompts))}/{len(prompts)}", flush=True)

    score_and_report(
        config, rows, raw_outputs, name=args.name, model=args.model_path, split=split, data_path=data_path,
        limit=args.limit, prompt=prompt,
        decoding={"greedy": True, "max_new_tokens": ecfg["max_new_tokens"], "batch_size": batch_size},
    )
    return 0


def score_and_report(
    config: dict[str, Any], rows: list[dict[str, Any]], raw_outputs: list[str], *, name: str, model: str,
    split: str, data_path: Path, limit: int | None, prompt: dict[str, str], decoding: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Exact-match scoring, metrics, bootstrap CI; writes predictions, metrics.json and the report.

    A --limit run is written under <name>_limit<N> so it never overwrites the full-split results.
    """
    ecfg = config["evaluation"]
    if limit:
        name = f"{name}_limit{limit}"
    predictions = []
    for row, raw in zip(rows, raw_outputs):
        pred = parse_prediction(raw)
        predictions.append({**row, "raw_output": raw, "prediction": pred, "correct": pred == row["target"]})

    overall = compute_metrics(predictions)
    by_dataset = breakdown(predictions, lambda r: r["dataset"])
    by_label = breakdown(predictions, lambda r: f"{r['dataset']} | {r['anchor_source_error_label']}")
    negatives = [p for p in predictions if p["target"] == NOT_ALIGNED]
    by_pair_label = breakdown(
        negatives,
        lambda r: f"{r['dataset']} | {r['anchor_source_error_label']} <- {r['donor_source_error_label']}",
        min_support=ecfg["min_support_for_label_pairs"],
    )
    ci = bootstrap_ci(predictions, n_samples=ecfg["bootstrap_samples"], seed=config["seed"])

    out_dir = resolve(ecfg["output_dir"]) / name
    write_jsonl(out_dir / "predictions.jsonl", predictions)
    result = {
        "name": name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "model_path": model,
        "split": split,
        "ablation": prompt["ablation"],
        "data_sha256": sha256_file(data_path),
        "limit": limit,
        "prompt": {"system_sha256": prompt["system_sha256"], "user_sha256": prompt["user_sha256"]},
        "decoding": decoding,
        **(extra or {}),
        "overall": overall,
        "bootstrap_ci_question_groups": ci,
        "by_dataset": by_dataset,
        "by_anchor_label": by_label,
        "by_anchor_donor_label_negatives": by_pair_label,
        "invalid_examples": [
            {"pair_id": p["pair_id"], "raw_output": p["raw_output"]} for p in predictions if p["prediction"] == "invalid"
        ][:50],
    }
    write_json(out_dir / "metrics.json", result)

    L = [f"# Verifier evaluation — {name}", ""]
    L += [f"model `{model}` · split `{split}` · ablation `{prompt['ablation']}` · {len(predictions)} rows "
          f"({overall['pairs']} pairs) · data sha256 `{result['data_sha256'][:16]}`", ""]
    L += ["Targets are automatic (other-label negatives, no semantic review): these are agreement rates with "
          "the automatic targets. Invalid outputs count as wrong.", ""]
    L += [md_table(HEADERS, metric_rows({"all": overall})), ""]
    L += ["95% intervals (question-group bootstrap, "
          f"{ecfg['bootstrap_samples']} samples): "
          + ", ".join(f"{k} [{fmt(v['low'])}, {fmt(v['high'])}]" for k, v in ci.items()), ""]
    pc = overall["per_class"]
    L += [md_table(["class", "precision", "recall", "F1", "support", "invalid"],
                   [[c, fmt(v["precision"]), fmt(v["recall"]), fmt(v["f1"]), v["support"], v["invalid"]] for c, v in pc.items()]), ""]
    L += ["## By dataset", "", md_table(HEADERS, metric_rows(by_dataset)), ""]
    L += ["## By anchor source label", "", md_table(HEADERS, metric_rows(by_label)), ""]
    L += [f"## Negatives by anchor <- donor label (n >= {ecfg['min_support_for_label_pairs']})", "",
          md_table(HEADERS, metric_rows(by_pair_label)) if by_pair_label else "No combination reaches the minimum support.", ""]
    report = resolve(config["output"].get("report_dir", "reports")) / f"eval_{name}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")

    print(f"accuracy {fmt(overall['accuracy'])} · macro-F1 {fmt(overall['macro_f1'])} · "
          f"pair accuracy {fmt(overall['pair_accuracy'])} · invalid {fmt(overall['invalid_rate'])}")
    print(f"predictions -> {out_dir / 'predictions.jsonl'}\nreport -> {report}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
