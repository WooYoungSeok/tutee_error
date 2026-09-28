#!/usr/bin/env python3
"""Check input format and loss masking on real examples with the real tokenizer.

For every example (default: all pairs of every split):
  * the user message is exactly the fixed template filled with Q / S / C;
  * the tokens that carry loss are exactly the label's tokens, then the tokenizer's
    eos token (e.g. Qwen `<|im_end|>`, DeepSeek `<｜end▁of▁sentence｜>`), then at most
    the template's trailing whitespace, i.e. the whole answer label is kept. Compared
    as token ids: some tokenizers decode special tokens differently from their name;
  * the inference prompt equals the training input up to the answer, so the
    model sees at inference what it saw in training;
  * nothing is truncated (length <= max_seq_length).

No model weights are loaded. Writes <output.report_dir>/format_check.md (default reports/) with one
rendered example; a --limit run writes format_check_limit<N>.md instead so the full-run report is kept.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verifier_common import (  # noqa: E402
    IGNORE_INDEX,
    build_messages,
    encode_example,
    generation_prompt,
    load_config,
    load_prompt,
    read_jsonl,
    resolve,
)

SPLITS = ("train", "validation", "test")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=None)
    parser.add_argument("--limit", type=int, default=None, help="examples per split (default: all)")
    args = parser.parse_args()

    from transformers import AutoTokenizer

    config = load_config(args.config)
    prompt = load_prompt(config)
    tokenizer = AutoTokenizer.from_pretrained(config["model"]["name"], trust_remote_code=True)
    max_len = config["model"]["max_seq_length"]
    data_dir = resolve(config["output"]["data_dir"])

    failures: list[str] = []
    checked = 0
    answer_tokens: dict[str, list[str]] = {}
    example = None
    for split in SPLITS:
        if not (data_dir / f"{split}.jsonl").exists():  # e.g. no validation file when training.use_validation is false
            continue
        rows = read_jsonl(data_dir / f"{split}.jsonl")
        for row in rows[: args.limit] if args.limit else rows:
            messages = build_messages(prompt, row, with_target=True)
            expected_user = (
                f"Question:\n{row['question']}\n\nIncorrect solution:\n{row['solution']}"
                f"\n\nError description:\n{row['error_description']}"
            )
            if messages[1]["content"] != expected_user:
                failures.append(f"{row['pair_id']}: user message differs from the template")
            enc = encode_example(tokenizer, messages)
            loss_ids = [t for t, lab in zip(enc["input_ids"], enc["labels"]) if lab != IGNORE_INDEX]
            answer = tokenizer.decode(loss_ids)
            label_ids = tokenizer(row["target"], add_special_tokens=False)["input_ids"]
            n = len(label_ids)
            if (loss_ids[:n] != label_ids or loss_ids[n:n + 1] != [tokenizer.eos_token_id]
                    or tokenizer.decode(loss_ids[n + 1:]).strip()):
                failures.append(f"{row['pair_id']}: loss tokens decode to {answer!r}")
            # encode_example guarantees at least one loss token after the prompt
            first_loss = next(i for i, lab in enumerate(enc["labels"]) if lab != IGNORE_INDEX)
            if any(lab == IGNORE_INDEX for lab in enc["labels"][first_loss:]):
                failures.append(f"{row['pair_id']}: masked token inside the answer span")
            infer_text = generation_prompt(tokenizer, messages[:-1])
            infer_ids = tokenizer(infer_text, add_special_tokens=False)["input_ids"]
            if infer_ids != enc["input_ids"][:first_loss]:
                failures.append(f"{row['pair_id']}: inference prompt differs from the training prefix")
            if len(enc["input_ids"]) > max_len:
                failures.append(f"{row['pair_id']}: {len(enc['input_ids'])} tokens > {max_len}")
            answer_tokens.setdefault(row["target"], [tokenizer.decode([t]) for t in loss_ids])
            if example is None and row["target"] == "not_aligned":
                example = (row, tokenizer.apply_chat_template(messages, tokenize=False), enc, answer)
            checked += 1

    lines = ["# Format and loss-mask check", ""]
    lines += [f"Tokenizer `{config['model']['name']}` · prompt sha256 system `{prompt['system_sha256'][:16]}` "
              f"user `{prompt['user_sha256'][:16]}` · examples checked: {checked} · failures: {len(failures)}", ""]
    lines += ["Tokens that carry loss:", ""]
    lines += [f"- `{label}`: {tokens}" for label, tokens in answer_tokens.items()]
    lines += [""]
    if failures:
        lines += ["## Failures", ""] + [f"- {f}" for f in failures[:50]] + [""]
    if example:
        row, text, enc, answer = example
        n_loss = sum(1 for lab in enc["labels"] if lab != IGNORE_INDEX)
        lines += ["## Example (training text, negative pair)", ""]
        lines += [f"`{row['pair_id']}` · donor `{row['donor_sample_id']}` · {len(enc['input_ids'])} tokens, "
                  f"{n_loss} with loss · loss tokens decode to `{answer!r}`", ""]
        lines += ["```text", text, "```", ""]
    report_dir = resolve(config["output"].get("report_dir", "reports"))
    out = report_dir / (f"format_check_limit{args.limit}.md" if args.limit else "format_check.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(f"checked {checked} examples, failures {len(failures)}")
    for label, tokens in answer_tokens.items():
        print(f"  loss tokens for {label}: {tokens}")
    for f in failures[:10]:
        print("  FAIL", f)
    print(f"report -> {out}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
