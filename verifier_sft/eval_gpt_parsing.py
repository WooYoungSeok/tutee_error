#!/usr/bin/env python3
"""Evaluate a local verifier with free-form generation and a GPT verdict extractor.

Follows llm_tutee_tutor RL_new_cluster_2prm_0623/evaluation/eval_reward_model_gpt_parsing.py:
  1. greedy generation with a long budget, so a model that reasons before answering can finish;
  2. gpt-4o-mini (temperature 0, max_tokens 10) reads only the generated text and returns
     aligned / not_aligned / not_matched. not_matched is scored as invalid.
Same test pairs, system/user messages, metrics and bootstrap as eval_descriptive_verifier.py.
This is a secondary protocol: the main comparison stays exact match (eval_descriptive_verifier.py).

Differences from the reference script:
  * max_new_tokens is capped so input + output stays within max_seq_length (the model's 4096 positions);
  * a failed GPT call is not counted as not_matched: the script stops and a re-run retries it;
  * generations and GPT verdicts are cached in outputs/<name>/, so re-running skips finished rows.

Usage (from verifier_sft/, OPENAI_API_KEY in ../.env):
    CUDA_VISIBLE_DEVICES=1 python eval_gpt_parsing.py --model_path Qwen/Qwen2.5-Math-7B-Instruct --name baseline_gptparse
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from errdesc.runner import load_dotenv  # noqa: E402
from eval_descriptive_verifier import score_and_report  # noqa: E402
from verifier_common import (  # noqa: E402
    build_messages,
    generation_prompt,
    load_config,
    load_prompt,
    read_jsonl,
    resolve,
)

PARSER_MODEL = "gpt-4o-mini"
# Reference system prompt; only the quoted task question is changed to this verifier's task.
PARSER_SYSTEM = (
    "You are analyzing a language model's response to the question: "
    "'Does the error description accurately describe an error actually present in the student's solution?' "
    "The model may reason at length (chain-of-thought) before giving its final verdict. "
    "Extract the FINAL verdict from the response. "
    "Reply with ONLY one of these three words: aligned, not_aligned, not_matched. "
    "Use 'not_matched' only if you truly cannot determine the verdict."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=None)
    parser.add_argument("--model_path", required=True, help="checkpoint dir or hub id")
    parser.add_argument("--name", required=True, help="output name, e.g. baseline_gptparse")
    parser.add_argument("--split", default=None, help="default: evaluation.split (test)")
    parser.add_argument("--limit", type=int, default=None, help="pilot: first N rows")
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--max_new_tokens", type=int, default=16384, help="reference default; capped by max_seq_length")
    parser.add_argument("--concurrency", type=int, default=10, help="parallel GPT calls (reference: 10)")
    parser.add_argument("--max_retries", type=int, default=4)
    return parser.parse_args()


def load_cache(path: Path, settings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cached: dict[str, dict[str, Any]] = {}
    if path.exists():
        for rec in read_jsonl(path):
            if rec["settings"] == settings and rec.get("error") is None:
                cached[rec["pair_id"]] = rec
    return cached


def generate(args: argparse.Namespace, rows: list[dict[str, Any]], prompt: dict[str, str], max_seq_length: int,
             settings: dict[str, Any], cache_path: Path) -> dict[str, dict[str, Any]]:
    done = load_cache(cache_path, settings)
    todo = [r for r in rows if r["pair_id"] not in done]
    print(f"generation: {len(rows) - len(todo)} cached · {len(todo)} to generate", flush=True)
    if not todo:
        return done

    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig

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
    eos = GenerationConfig.from_pretrained(args.model_path).eos_token_id
    stop_ids = set(eos if isinstance(eos, list) else [eos]) | {tokenizer.eos_token_id}

    prompts = {r["pair_id"]: generation_prompt(tokenizer, build_messages(prompt, r, with_target=False)) for r in todo}
    lengths = {k: len(tokenizer(v, add_special_tokens=False)["input_ids"]) for k, v in prompts.items()}
    order = sorted(prompts, key=lambda k: lengths[k])  # similar lengths per batch: less padding
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(order), args.batch_size):
        ids = order[start:start + args.batch_size]
        batch = tokenizer([prompts[k] for k in ids], return_tensors="pt", padding=True, add_special_tokens=False).to(device)
        in_len = batch["input_ids"].shape[1]
        budget = min(args.max_new_tokens, max_seq_length - in_len)
        with torch.no_grad():
            out = model.generate(
                **batch, max_new_tokens=budget, do_sample=False, temperature=None, top_p=None, top_k=None,
                pad_token_id=tokenizer.pad_token_id,
            )
        with cache_path.open("a", encoding="utf-8", newline="\n") as f:
            for k, seq in zip(ids, out[:, in_len:].tolist()):
                stop = next((i for i, t in enumerate(seq) if t in stop_ids), None)
                rec = {
                    "pair_id": k, "settings": settings, "error": None,
                    "generation": tokenizer.decode(seq, skip_special_tokens=True).strip(),
                    "new_tokens": stop if stop is not None else len(seq),
                    "finished": stop is not None,
                    "budget": budget,
                }
                done[k] = rec
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"  {min(start + args.batch_size, len(order))}/{len(order)} (budget {budget})", flush=True)
    return done


def parse_with_gpt(args: argparse.Namespace, rows: list[dict[str, Any]], generations: dict[str, dict[str, Any]],
                   settings: dict[str, Any], cache_path: Path) -> dict[str, dict[str, Any]]:
    done = load_cache(cache_path, settings)
    todo = [r for r in rows if r["pair_id"] not in done]
    print(f"gpt parsing: {len(rows) - len(todo)} cached · {len(todo)} to call", flush=True)
    if not todo:
        return done
    load_dotenv(HERE.parent / ".env")
    from openai import OpenAI

    client = OpenAI(max_retries=args.max_retries)
    lock = threading.Lock()

    def call(row: dict[str, Any]) -> None:
        text = generations[row["pair_id"]]["generation"]
        rec: dict[str, Any] = {"pair_id": row["pair_id"], "settings": settings, "error": None}
        if not text:  # reference: empty output is not_matched without a call
            rec.update(verdict="not_matched", parser_output=None, parser_model=None)
        else:
            try:
                resp = client.chat.completions.create(
                    model=PARSER_MODEL,
                    messages=[{"role": "system", "content": PARSER_SYSTEM}, {"role": "user", "content": text}],
                    max_tokens=10,
                    temperature=0,
                )
                raw = resp.choices[0].message.content or ""
                verdict = raw.strip().lower()
                rec.update(verdict=verdict if verdict in ("aligned", "not_aligned") else "not_matched",
                           parser_output=raw, parser_model=resp.model)
            except Exception as exc:  # noqa: BLE001 - recorded; the row stays uncached and is retried next run
                rec["error"] = f"{type(exc).__name__}: {exc}"
        with lock:
            with cache_path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if rec["error"] is None:
                done[row["pair_id"]] = rec

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        list(pool.map(call, todo))
    return done


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    split = args.split or config["evaluation"]["split"]
    data_path = resolve(config["output"]["data_dir"]) / f"{split}.jsonl"
    rows = read_jsonl(data_path)
    if args.limit:
        rows = rows[: args.limit]
    prompt = load_prompt(config)
    max_seq_length = config["model"]["max_seq_length"]
    out_dir = resolve(config["evaluation"]["output_dir"]) / args.name

    gen_settings = {
        "model_path": args.model_path, "max_new_tokens": args.max_new_tokens, "max_seq_length": max_seq_length,
        "system_sha256": prompt["system_sha256"], "user_sha256": prompt["user_sha256"],
    }
    generations = generate(args, rows, prompt, max_seq_length, gen_settings, out_dir / "generations.jsonl")

    parse_settings = {**gen_settings, "parser_model": PARSER_MODEL, "parser_system": PARSER_SYSTEM}
    verdicts = parse_with_gpt(args, rows, generations, parse_settings, out_dir / "gpt_parsing.jsonl")
    missing = [r["pair_id"] for r in rows if r["pair_id"] not in verdicts]
    if missing:
        print(f"{len(missing)} GPT call(s) failed; not scoring. Re-run the same command to retry them. "
              f"Errors are in {out_dir / 'gpt_parsing.jsonl'}")
        return 1

    gens = [generations[r["pair_id"]] for r in rows]
    parsed = [verdicts[r["pair_id"]] for r in rows]
    extra = {
        "gpt_parsing": {
            "parser_model": PARSER_MODEL,
            "parser_models_seen": sorted({str(p["parser_model"]) for p in parsed if p["parser_model"]}),
            "parser_system": PARSER_SYSTEM,
            "verdict_counts": dict(Counter(p["verdict"] for p in parsed)),
            "generation": {
                "finished": sum(g["finished"] for g in gens),
                "hit_budget": sum(not g["finished"] for g in gens),
                "mean_new_tokens": sum(g["new_tokens"] for g in gens) / len(gens),
                "max_new_tokens_used": max(g["new_tokens"] for g in gens),
            },
        }
    }
    decoding = {
        "greedy": True, "max_new_tokens": args.max_new_tokens, "capped_to": f"{max_seq_length} - input length",
        "batch_size": args.batch_size, "verdict": f"{PARSER_MODEL} extraction (not exact match)",
    }
    # the extracted verdict is what gets scored; the free-form text stays in generations.jsonl
    score_and_report(
        config, rows, [p["verdict"] for p in parsed], name=args.name, model=args.model_path, split=split,
        data_path=data_path, limit=args.limit, prompt=prompt, decoding=decoding, extra=extra,
    )
    print(f"verdicts {extra['gpt_parsing']['verdict_counts']} · generation {extra['gpt_parsing']['generation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
