"""Model input contracts: the verifier (plan 6.1) and the Student (plan 7).

Verifier: (Q, incorrect solution S, target Newman stage N, target source error type E) -> exactly `aligned` or
`not_aligned`. SFT training, the served reward verifier (A) and the test verifier (B) build their messages only
through `verifier_messages`, so all three read one template and one taxonomy. The pair's own label metadata
(original type, whether it is a negative) never enters the input. Tokenization with loss on the assistant answer
only, the exact-match parser (anything else is `invalid`) and the metrics are verifier_sft's, unchanged.

Student: system = instruction with the (N, E) names and definitions from the taxonomy; user = the question.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .common import import_verifier_sft, render, read_template, rel, resolve, sha256_file
from .taxonomy import Taxonomy

_vc = import_verifier_sft("verifier_common")
ALIGNED, NOT_ALIGNED, LABELS, INVALID, IGNORE_INDEX = _vc.ALIGNED, _vc.NOT_ALIGNED, _vc.LABELS, _vc.INVALID, _vc.IGNORE_INDEX
encode_example = _vc.encode_example          # loss on the assistant label + end tokens only, never truncated
generation_prompt = _vc.generation_prompt
parse_prediction = _vc.parse_prediction      # exact match after strip; `not_aligned` never matches `aligned`
question_key = _vc.question_key
question_group_id = _vc.question_group_id

CONDITION_PLACEHOLDERS = ("newman_framework", "newman_stage_name", "newman_stage_definition", "source_error_name", "source_error_definition")
VERIFIER_USER_PLACEHOLDERS = ("question", "solution", *CONDITION_PLACEHOLDERS)


class PromptError(RuntimeError):
    pass


def render_condition(template: str, values: Mapping[str, Any]) -> str:
    """Single-pass rendering; a line holding a placeholder whose value is None is left out entirely (the two Stepwise
    types have no workbook definition, user decision 2026-09-30: no definition line rather than a made-up one)."""
    missing = [k for k, v in values.items() if v is None]
    lines = [ln for ln in template.split("\n") if not any("{" + k + "}" in ln for k in missing)]
    kept = "\n".join(lines)
    return render(kept, {k: v for k, v in values.items() if v is not None and "{" + k + "}" in kept})


def load_verifier_prompt(system_path: str | Path, user_path: str | Path) -> dict[str, str]:
    system, user = read_template(system_path), read_template(user_path)
    missing = [p for p in VERIFIER_USER_PLACEHOLDERS if "{" + p + "}" not in user]
    if missing:
        raise PromptError(f"{user_path} is missing placeholder(s) {missing}")
    stray = [p for p in VERIFIER_USER_PLACEHOLDERS if "{" + p + "}" in system]
    if stray:
        raise PromptError(f"{system_path} must not contain placeholders, found {stray}")
    return {"system": system, "user": user,
            "system_path": rel(resolve(system_path)), "user_path": rel(resolve(user_path)),
            "system_sha256": sha256_file(resolve(system_path)), "user_sha256": sha256_file(resolve(user_path))}


def verifier_messages(prompt: Mapping[str, str], taxonomy: Taxonomy, question: str, solution: str, error_id: str,
                      target: str | None = None) -> list[dict[str, str]]:
    user = render_condition(prompt["user"], {"question": question, "solution": solution, **taxonomy.prompt_values(error_id)})
    messages = [{"role": "system", "content": prompt["system"]}, {"role": "user", "content": user}]
    if target is not None:
        if target not in LABELS:
            raise ValueError(f"target must be one of {LABELS}: {target!r}")
        messages.append({"role": "assistant", "content": target})
    return messages


def build_messages(prompt: Mapping[str, str], taxonomy: Taxonomy, record: Mapping[str, Any], with_target: bool) -> list[dict[str, str]]:
    """A prepared pair record -> chat messages (training: with the label; inference: without)."""
    return verifier_messages(prompt, taxonomy, record["question"], record["solution"], record["target_error_id"],
                             record["target"] if with_target else None)


def load_student_template(path: str | Path) -> str:
    template = read_template(path)
    missing = [p for p in CONDITION_PLACEHOLDERS if "{" + p + "}" not in template]
    if missing:
        raise PromptError(f"{path} is missing placeholder(s) {missing}")
    return template


def student_messages(template: str, taxonomy: Taxonomy, row: Mapping[str, Any]) -> list[dict[str, str]]:
    """Training and evaluation input of the Student: instruction + (N, E) as system, the question as user."""
    return [{"role": "system", "content": render_condition(template, taxonomy.prompt_values(row["source_error_id"]))},
            {"role": "user", "content": row["question"]}]


def pair_token_count(tokenizer: Any, prompt: Mapping[str, str], taxonomy: Taxonomy, record: Mapping[str, Any]) -> int:
    """Full training length: chat template, system prompt, user message and assistant label."""
    return len(encode_example(tokenizer, build_messages(prompt, taxonomy, record, with_target=True))["input_ids"])
