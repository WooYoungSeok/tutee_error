#!/usr/bin/env python3
"""Check the verifier input format and loss mask on the prepared pairs with a backbone's real tokenizer.

For every pair of the half the config trains on and of the test split:
  * the user message is exactly the template filled with Q / S / the target (N, E) from the taxonomy;
  * the loss tokens are exactly the label's tokens, then the tokenizer's eos token, then at most the template's
    trailing whitespace (compared as token ids);
  * the inference prompt equals the training input up to the answer;
  * nothing exceeds max_seq_length, and `aligned`, `not_aligned` + eos fit in evaluation.max_new_tokens.
No model weights are loaded. Writes reports/format_check_<experiment>.md.

Usage (from newman_experiment/):  python scripts/check_formatting.py --config configs/verifier_half_a.yaml [--limit N]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman.common import load_config, read_jsonl, resolve  # noqa: E402
from newman.taxonomy import Taxonomy  # noqa: E402
from newman.verifier_format import (  # noqa: E402
    IGNORE_INDEX,
    build_messages,
    encode_example,
    generation_prompt,
    load_verifier_prompt,
)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--override", action="append", default=[], help="a.b.c=value (YAML value), repeatable")
    p.add_argument("--limit", type=int, default=None, help="pairs per file")
    args = p.parse_args()
    from transformers import AutoTokenizer

    cfg = load_config(args.config, args.override)
    taxonomy = Taxonomy.load(resolve(cfg["taxonomy"]))
    prompt = load_verifier_prompt(cfg["prompts"]["system"], cfg["prompts"]["user"])
    tok = AutoTokenizer.from_pretrained(cfg["model"]["name"], trust_remote_code=True)
    max_len, max_new = int(cfg["max_seq_length"]), int(cfg["evaluation"]["max_new_tokens"])
    failures, checked, example = [], 0, None
    label_budget = {lab: len(tok(lab, add_special_tokens=False)["input_ids"]) + 1 for lab in ("aligned", "not_aligned")}
    for lab, n in label_budget.items():
        if n > max_new:
            failures.append(f"label {lab!r} + eos needs {n} tokens > evaluation.max_new_tokens {max_new}")
    for name in (cfg["data_file"], cfg["evaluation"]["split_file"]):
        rows = read_jsonl(resolve(cfg["data_dir"]) / name)
        for row in rows[: args.limit] if args.limit else rows:
            messages = build_messages(prompt, taxonomy, row, with_target=True)
            c = taxonomy.condition(row["target_error_id"])
            expected = (f"Question:\n{row['question']}\n\nIncorrect solution:\n{row['solution']}\n\n"
                        f"Problem-solving stage (Newman's Error Analysis):\n{taxonomy.framework}\n"
                        f"Specified stage: {c['stage_name']}\n{c['stage_definition']}\n\nError type:\n{c['error_name']}"
                        + (f"\n{c['error_definition']}" if c["error_definition"] is not None else ""))
            if messages[1]["content"] != expected:
                failures.append(f"{row['pair_id']}: user message differs from the template")
            if c["stage_id"] != row["target_newman_stage"]:
                failures.append(f"{row['pair_id']}: stage {row['target_newman_stage']} is not mapping({row['target_error_id']})")
            enc = encode_example(tok, messages)
            loss_ids = [t for t, lab in zip(enc["input_ids"], enc["labels"]) if lab != IGNORE_INDEX]
            label_ids = tok(row["target"], add_special_tokens=False)["input_ids"]
            n = len(label_ids)
            if loss_ids[:n] != label_ids or loss_ids[n:n + 1] != [tok.eos_token_id] or tok.decode(loss_ids[n + 1:]).strip():
                failures.append(f"{row['pair_id']}: loss tokens decode to {tok.decode(loss_ids)!r}")
            first = next(i for i, lab in enumerate(enc["labels"]) if lab != IGNORE_INDEX)
            if any(lab == IGNORE_INDEX for lab in enc["labels"][first:]):
                failures.append(f"{row['pair_id']}: masked token inside the answer span")
            infer = tok(generation_prompt(tok, messages[:-1]), add_special_tokens=False)["input_ids"]
            if infer != enc["input_ids"][:first]:
                failures.append(f"{row['pair_id']}: inference prompt differs from the training prefix")
            if len(enc["input_ids"]) > max_len:
                failures.append(f"{row['pair_id']}: {len(enc['input_ids'])} tokens > {max_len}")
            if example is None and row["target"] == "not_aligned":
                example = (row, tok.apply_chat_template(messages, tokenize=False), len(enc["input_ids"]), tok.decode(loss_ids))
            checked += 1
    lines = [f"# Format and loss-mask check — {cfg['experiment']}", "",
             f"Tokenizer `{cfg['model']['name']}` · prompt sha256 system `{prompt['system_sha256'][:16]}` user "
             f"`{prompt['user_sha256'][:16]}` · taxonomy `{taxonomy.sha256[:16]}` · pairs checked {checked} · failures {len(failures)}", "",
             f"Answer budget (label + eos tokens): {label_budget} (max_new_tokens {max_new})", ""]
    if failures:
        lines += ["## Failures", ""] + [f"- {f}" for f in failures[:50]] + [""]
    if example:
        row, text, n_tok, answer = example
        lines += ["## Example (negative pair, training text)", "", f"`{row['pair_id']}` · {n_tok} tokens · loss tokens decode to `{answer!r}`",
                  "", "```text", text, "```", ""]
    out = resolve("reports") / f"format_check_{cfg['experiment']}{'_limit' + str(args.limit) if args.limit else ''}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"checked {checked} pairs, failures {len(failures)} -> {out}")
    for f in failures[:10]:
        print("  FAIL", f)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
