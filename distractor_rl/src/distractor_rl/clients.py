"""gpt-5-nano distractor check, a second call made only for incorrect answers (user decisions 2026-10-02).

The final answer is extracted and graded by the Eedi answer judge, unchanged (tutee_rl.clients.AnswerChecker with
../rl/prompts/answer_judge_*.txt; a single call that also saw the options mixed "matches no option" into the verdict
in the smoke run). For an incorrect answer this call compares the extracted answer with the condition's target
distractors only (the options whose misconception is the condition's): prompts/distractor_match_*.txt.
Request path, attempts, backoff and abort policy follow tutee_rl.clients.AnswerChecker.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Mapping, Sequence

from tutee_rl.clients import RewardExecutionError, SchemaViolation, _backoff, classify_error, responses_call
from tutee_rl.common import hash_obj, render, sha256_text

MATCH_SCHEMA = {
    "type": "object",
    "properties": {"matched_option": {"anyOf": [{"type": "string"}, {"type": "null"}]}, "reason": {"type": "string"}},
    "required": ["matched_option", "reason"],
    "additionalProperties": False,
}


def format_options(targets: Sequence[Mapping[str, Any]]) -> str:
    """'A: <text>' per target distractor, in option order."""
    return "\n".join(f"{t['option']}: {t['text']}" for t in sorted(targets, key=lambda t: t["option"]))


def parse_match(text: str, letters: Sequence[str]) -> dict[str, Any]:
    """JSON with exactly matched_option and reason. A letter that is not a given option is dropped and recorded
    (never retried: user 2026-10-02); malformed JSON is a schema violation (retried)."""
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise SchemaViolation(f"not JSON: {exc}") from exc
    if not isinstance(obj, dict) or set(obj) != {"matched_option", "reason"}:
        raise SchemaViolation(f"unexpected keys: {sorted(obj) if isinstance(obj, dict) else type(obj).__name__}")
    matched, reason = obj["matched_option"], obj["reason"]
    if not isinstance(reason, str):
        raise SchemaViolation("reason must be a string")
    dropped = None
    if matched is not None:
        letter = matched.strip().upper() if isinstance(matched, str) else None
        if letter in letters:
            matched = letter
        else:
            dropped, matched = f"not a given option: {matched!r}", None
    return {"matched_option": matched, "reason": reason, "matched_option_dropped": dropped}


class DistractorMatcher:
    def __init__(self, cfg: Mapping[str, Any], system_prompt: str, user_template: str, client: Any):
        self.cfg = cfg  # the answer_check settings: model, reasoning effort, max output, timeout, attempts
        self.system_prompt, self.user_template, self.client = system_prompt, user_template, client
        self.sem = asyncio.Semaphore(int(cfg["concurrency"]))
        self.prompt_version = sha256_text(system_prompt + "\n\x00\n" + user_template)
        self.cache: dict[str, dict[str, Any]] = {}

    def settings(self) -> dict[str, Any]:
        return {k: self.cfg.get(k) for k in ("model", "structured_output", "reasoning_effort", "max_output_tokens")}

    def payload(self, user_text: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.cfg["model"], "instructions": self.system_prompt,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": user_text}]}],
            "max_output_tokens": int(self.cfg["max_output_tokens"]),
            "text": {"format": {"type": "json_schema", "name": "target_distractor_match", "schema": MATCH_SCHEMA, "strict": True}},
        }
        if self.cfg.get("reasoning_effort"):
            payload["reasoning"] = {"effort": self.cfg["reasoning_effort"]}
        return payload

    async def match(self, problem: str, answer_contract: str, extracted_answer: str,
                    targets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        letters = [t["option"] for t in targets]
        user_text = render(self.user_template, {"problem": problem, "answer_contract": answer_contract,
                                                "options": format_options(targets), "extracted_answer": extracted_answer})
        key = hash_obj({"settings": self.settings(), "prompt": self.prompt_version, "user": user_text})
        if key in self.cache:
            return {**self.cache[key], "cached": True}
        payload, failures = self.payload(user_text), []
        attempts = int(self.cfg["max_attempts"])
        for attempt in range(attempts):
            async with self.sem:
                try:
                    api = await responses_call(self.client, payload, float(self.cfg["request_timeout_s"]))
                except Exception as exc:  # noqa: BLE001 - classified below
                    retryable, kind = classify_error(exc)
                    failures.append(f"{kind}: {str(exc)[:200]}")
                    if not retryable:
                        raise RewardExecutionError(f"distractor match fatal error {kind}: {exc}") from exc
                    api = None
            if api is not None:
                if api["status"] == "incomplete" or api["incomplete_reason"]:
                    failures.append(f"incomplete: {api['incomplete_reason']}")
                else:
                    try:
                        out = {**parse_match(api["output_text"], letters), "raw_text": api["output_text"],
                               "prompt_version": self.prompt_version, "response_id": api["response_id"],
                               "request_id": api["request_id"], "usage": api["usage"], "latency_s": api["latency_s"],
                               "attempts": attempt + 1, "failures": failures}
                        self.cache[key] = out
                        return {**out, "cached": False}
                    except SchemaViolation as exc:
                        failures.append(f"schema: {exc} | raw={api['output_text'][:300]!r}")
            if attempt + 1 < attempts:
                await _backoff(attempt)
        raise RewardExecutionError(f"distractor match failed after {attempts} attempts: {failures[-3:]}")


class MockDistractorMatcher:
    """Smoke only: a deterministic match for half of the incorrect answers."""

    prompt_version = "mock"

    def settings(self) -> dict[str, Any]:
        return {"model": "MOCK"}

    async def match(self, problem, answer_contract, extracted_answer, targets) -> dict[str, Any]:
        from tutee_rl.mock import _h

        hit = bool(targets) and _h(str(extracted_answer) + problem, "distractor") < 50
        return {"matched_option": targets[0]["option"] if hit else None, "reason": "mock", "matched_option_dropped": None,
                "raw_text": "", "response_id": None, "request_id": None, "usage": None, "latency_s": 0.0, "attempts": 1,
                "failures": [], "cached": False}


# --- extraction only (verifiable variant, user 2026-10-03) -------------------------------------------------------

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {"extracted_answer": {"anyOf": [{"type": "string"}, {"type": "null"}]}, "reason": {"type": "string"}},
    "required": ["extracted_answer", "reason"],
    "additionalProperties": False,
}


def parse_extraction(text: str) -> dict[str, Any]:
    """JSON with exactly extracted_answer and reason; the string "null"/"" or a placeholder ("none", "n/a") standing in
    for a missing answer is a schema violation (retried), as in the Eedi parser."""
    from tutee_rl.clients import NULL_STRINGS

    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise SchemaViolation(f"not JSON: {exc}") from exc
    if not isinstance(obj, dict) or set(obj) != {"extracted_answer", "reason"}:
        raise SchemaViolation(f"unexpected keys: {sorted(obj) if isinstance(obj, dict) else type(obj).__name__}")
    answer, reason = obj["extracted_answer"], obj["reason"]
    if answer is not None and not isinstance(answer, str):
        raise SchemaViolation("extracted_answer must be a string or null")
    if isinstance(answer, str) and answer.strip().lower() in NULL_STRINGS:
        raise SchemaViolation(f"extracted_answer is the string {answer!r} instead of JSON null")
    if not isinstance(reason, str):
        raise SchemaViolation("reason must be a string")
    return {"extracted_answer": answer, "reason": reason}


class AnswerExtractor(DistractorMatcher):
    """gpt-5-nano final-answer extraction without grading (prompts/answer_extract_*.txt); same request policy."""

    def payload(self, user_text: str) -> dict[str, Any]:
        payload = super().payload(user_text)
        payload["text"] = {"format": {"type": "json_schema", "name": "final_answer_extraction", "schema": EXTRACT_SCHEMA, "strict": True}}
        return payload

    async def extract(self, problem: str, answer_contract: str, solution: str) -> dict[str, Any]:
        user_text = render(self.user_template, {"problem": problem, "answer_contract": answer_contract, "generated_solution": solution})
        key = hash_obj({"settings": self.settings(), "prompt": self.prompt_version, "user": user_text})
        if key in self.cache:
            return {**self.cache[key], "cached": True}
        payload, failures = self.payload(user_text), []
        attempts = int(self.cfg["max_attempts"])
        for attempt in range(attempts):
            async with self.sem:
                try:
                    api = await responses_call(self.client, payload, float(self.cfg["request_timeout_s"]))
                except Exception as exc:  # noqa: BLE001 - classified below
                    retryable, kind = classify_error(exc)
                    failures.append(f"{kind}: {str(exc)[:200]}")
                    if not retryable:
                        raise RewardExecutionError(f"answer extraction fatal error {kind}: {exc}") from exc
                    api = None
            if api is not None:
                if api["status"] == "incomplete" or api["incomplete_reason"]:
                    failures.append(f"incomplete: {api['incomplete_reason']}")
                else:
                    try:
                        out = {**parse_extraction(api["output_text"]), "raw_text": api["output_text"], "model": self.cfg["model"],
                               "prompt_version": self.prompt_version, "response_id": api["response_id"],
                               "request_id": api["request_id"], "usage": api["usage"], "latency_s": api["latency_s"],
                               "attempts": attempt + 1, "failures": failures}
                        self.cache[key] = out
                        return {**out, "cached": False}
                    except SchemaViolation as exc:
                        failures.append(f"schema: {exc} | raw={api['output_text'][:300]!r}")
            if attempt + 1 < attempts:
                await _backoff(attempt)
        raise RewardExecutionError(f"answer extraction failed after {attempts} attempts: {failures[-3:]}")


class MockAnswerExtractor:
    prompt_version = "mock"

    def settings(self) -> dict[str, Any]:
        return {"model": "MOCK"}

    async def extract(self, problem, answer_contract, solution) -> dict[str, Any]:
        from tutee_rl.mock import _h

        null = _h(solution, "extract") < 10
        return {"extracted_answer": None if null else f"ans{_h(solution, 'value') % 5}", "reason": "mock", "raw_text": "",
                "model": "MOCK", "response_id": None, "request_id": None, "usage": None, "latency_s": 0.0, "attempts": 1,
                "failures": [], "cached": False}
