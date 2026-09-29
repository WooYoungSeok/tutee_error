"""Async clients for the three model calls in the reward.

* AnswerChecker   gpt-5-nano, one logical call per rollout: extract the final answer and grade it.
* VerifierClient  the frozen SFT verifier behind a vLLM server, two samples per incorrect rollout.
* PairwiseJudge   student-likeness A/B judge (OpenAI Responses API or a local vLLM server).

Failure policy (plan 4.4 / 8.4): content-level nulls are results; execution failures (API errors,
truncated responses, JSON/schema violations) are retried a bounded number of times and then raise
RewardExecutionError, which aborts the rollout batch. A failure is never converted into `incorrect`,
`not_aligned` or `tie`.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from typing import Any, Mapping, Sequence

from .common import hash_obj, render, sha256_text

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}
NULL_STRINGS = {"null", "none", "nil", "n/a", ""}


class RewardExecutionError(RuntimeError):
    """A reward call could not be completed; the rollout batch must stop (never scored as a content result)."""


class SchemaViolation(ValueError):
    pass


def classify_error(exc: BaseException) -> tuple[bool, str]:
    """(retryable, kind). Auth, unknown model and bad parameters are fatal at once."""
    name = type(exc).__name__
    status = getattr(exc, "status_code", None)
    if name in {"AuthenticationError", "PermissionDeniedError", "NotFoundError", "BadRequestError", "UnprocessableEntityError"}:
        return False, name
    if name in {"RateLimitError", "APITimeoutError", "APIConnectionError", "InternalServerError"}:
        return True, name
    if isinstance(status, int):
        return status in RETRYABLE_STATUS, f"{name}({status})"
    if isinstance(exc, (TimeoutError, ConnectionError, asyncio.TimeoutError)):
        return True, name
    return False, name


async def _backoff(attempt: int) -> None:
    await asyncio.sleep(min(60.0, 2.0 ** attempt) * (0.5 + random.random()))


def _response_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text is not None:
        return text
    chunks = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            if getattr(content, "type", "") in {"output_text", "text"}:
                chunks.append(getattr(content, "text", ""))
    return "".join(chunks)


def _usage(obj: Any) -> dict[str, Any] | None:
    usage = getattr(obj, "usage", None)
    if usage is None:
        return None
    return usage.model_dump() if hasattr(usage, "model_dump") else dict(usage)


async def responses_call(client: Any, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    raw = await client.responses.with_raw_response.create(timeout=timeout, **payload)
    response = raw.parse()
    incomplete = getattr(response, "incomplete_details", None)
    return {
        "response_id": getattr(response, "id", None),
        "request_id": raw.headers.get("x-request-id") if hasattr(raw, "headers") else None,
        "status": getattr(response, "status", None),
        "incomplete_reason": getattr(incomplete, "reason", None) if incomplete else None,
        "output_text": _response_text(response),
        "usage": _usage(response),
        "latency_s": round(time.monotonic() - started, 3),
    }


# --- gpt-5-nano answer extraction + grading ----------------------------------

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "extracted_answer": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "verdict": {"anyOf": [{"type": "string", "enum": ["correct", "incorrect"]}, {"type": "null"}]},
        "reason": {"type": "string"},
    },
    "required": ["extracted_answer", "verdict", "reason"],
    "additionalProperties": False,
}


def parse_answer_check(text: str) -> dict[str, Any]:
    """Strict: JSON object with exactly the three fields; JSON null (Python None) for unclear answers.

    A missing answer with a correct/incorrect verdict, or the strings "null"/"None", is a schema violation
    (retried), never silently mapped to incorrect.
    """
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise SchemaViolation(f"not JSON: {exc}") from exc
    if not isinstance(obj, dict) or set(obj) != {"extracted_answer", "verdict", "reason"}:
        raise SchemaViolation(f"unexpected keys: {sorted(obj) if isinstance(obj, dict) else type(obj).__name__}")
    answer, verdict, reason = obj["extracted_answer"], obj["verdict"], obj["reason"]
    if answer is not None and not isinstance(answer, str):
        raise SchemaViolation("extracted_answer must be a string or null")
    if isinstance(answer, str) and answer.strip().lower() in NULL_STRINGS:
        raise SchemaViolation(f"extracted_answer is the string {answer!r} instead of JSON null")
    if verdict is not None and verdict not in ("correct", "incorrect"):
        raise SchemaViolation(f"verdict {verdict!r}")
    if not isinstance(reason, str):
        raise SchemaViolation("reason must be a string")
    if answer is None and verdict is not None:
        raise SchemaViolation("extracted_answer is null but verdict is not")
    return {"extracted_answer": answer, "verdict": verdict, "reason": reason}


class AnswerChecker:
    def __init__(self, cfg: Mapping[str, Any], system_prompt: str, user_template: str, client: Any):
        self.cfg = cfg
        self.system_prompt = system_prompt
        self.user_template = user_template
        self.client = client
        self.sem = asyncio.Semaphore(int(cfg["concurrency"]))
        self.prompt_version = sha256_text(system_prompt + "\n\x00\n" + user_template)
        self.cache: dict[str, dict[str, Any]] = {}
        self._inflight: dict[str, asyncio.Future] = {}

    def settings(self) -> dict[str, Any]:
        return {k: self.cfg.get(k) for k in ("model", "structured_output", "reasoning_effort", "max_output_tokens")}

    def payload(self, user_text: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.cfg["model"],
            "instructions": self.system_prompt,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": user_text}]}],
            "max_output_tokens": int(self.cfg["max_output_tokens"]),
        }
        if self.cfg.get("structured_output"):
            payload["text"] = {"format": {"type": "json_schema", "name": "final_answer_check", "schema": ANSWER_SCHEMA, "strict": True}}
        if self.cfg.get("reasoning_effort"):
            payload["reasoning"] = {"effort": self.cfg["reasoning_effort"]}
        return payload

    async def check(self, problem: str, answer_contract: str, reference: str, solution: str) -> dict[str, Any]:
        user_text = render(self.user_template, {
            "problem": problem, "answer_contract": answer_contract,
            "correct_answer_text": reference, "generated_solution": solution,
        })
        key = hash_obj({"settings": self.settings(), "prompt": self.prompt_version, "user": user_text})
        if key in self.cache:
            return {**self.cache[key], "cached": True}
        if key in self._inflight:  # identical solutions in one batch share a single call
            return {**(await asyncio.shield(self._inflight[key])), "cached": True}
        future = asyncio.get_running_loop().create_future()
        self._inflight[key] = future
        try:
            result = await self._call(user_text)
            self.cache[key] = result
            future.set_result(result)
            return {**result, "cached": False}
        except BaseException as exc:
            future.set_exception(exc)
            future.exception()  # mark retrieved
            raise
        finally:
            self._inflight.pop(key, None)

    async def _call(self, user_text: str) -> dict[str, Any]:
        payload = self.payload(user_text)
        failures: list[str] = []
        attempts = int(self.cfg["max_attempts"])
        for attempt in range(attempts):
            async with self.sem:
                try:
                    api = await responses_call(self.client, payload, float(self.cfg["request_timeout_s"]))
                except Exception as exc:  # noqa: BLE001 - classified below
                    retryable, kind = classify_error(exc)
                    failures.append(f"{kind}: {str(exc)[:200]}")
                    if not retryable:
                        raise RewardExecutionError(f"answer check fatal error {kind}: {exc}") from exc
                    api = None
            if api is not None:
                if api["status"] == "incomplete" or api["incomplete_reason"]:
                    failures.append(f"incomplete: {api['incomplete_reason']}")
                else:
                    try:
                        parsed = parse_answer_check(api["output_text"])
                        return {**parsed, "raw_text": api["output_text"], "model": self.cfg["model"],
                                "prompt_version": self.prompt_version, "response_id": api["response_id"],
                                "request_id": api["request_id"], "usage": api["usage"], "latency_s": api["latency_s"],
                                "attempts": attempt + 1, "failures": failures}
                    except SchemaViolation as exc:
                        failures.append(f"schema: {exc} | raw={api['output_text'][:300]!r}")
            if attempt + 1 < attempts:
                await _backoff(attempt)
        raise RewardExecutionError(f"answer check failed after {attempts} attempts: {failures[-3:]}")


# --- verifier (vLLM, token-id prompts) ---------------------------------------


class VerifierClient:
    """Two independent samples (n=2, no fixed seed) from the frozen SFT verifier.

    Prompts are rendered and tokenized here with the verifier's own tokenizer exactly as in
    verifier_sft (chat template, add_generation_prompt, add_special_tokens=False) and sent as token ids,
    so the server cannot add a second BOS. Stop ids mirror HF generate (generation_config eos ids).
    """

    def __init__(self, cfg: Mapping[str, Any], prompt: dict[str, str], tokenizer: Any, stop_token_ids: list[int],
                 repetition_penalty: float, client: Any):
        import sys

        from .common import VERIFIER_SFT_DIR

        sys.path.insert(0, str(VERIFIER_SFT_DIR))
        import verifier_common  # the SFT contract: build_messages / generation_prompt / parse_prediction

        self.vc = verifier_common
        self.cfg = cfg
        self.prompt = prompt
        self.tokenizer = tokenizer
        self.stop_token_ids = stop_token_ids
        self.repetition_penalty = float(repetition_penalty)
        self.client = client
        self.sem = asyncio.Semaphore(int(cfg["concurrency"]))

    def prompt_ids(self, question: str, solution: str, description: str) -> list[int]:
        record = {"question": question, "solution": solution, "error_description": description}
        text = self.vc.generation_prompt(self.tokenizer, self.vc.build_messages(self.prompt, record, with_target=False))
        return self.tokenizer(text, add_special_tokens=False)["input_ids"]

    def sampling(self) -> dict[str, Any]:
        return {"n": int(self.cfg["samples"]), "temperature": float(self.cfg["temperature"]), "top_p": float(self.cfg["top_p"]),
                "top_k": int(self.cfg["top_k"]), "max_tokens": int(self.cfg["max_new_tokens"]),
                "repetition_penalty": self.repetition_penalty, "stop_token_ids": self.stop_token_ids,
                "skip_special_tokens": True}

    async def judge(self, question: str, solution: str, description: str) -> dict[str, Any]:
        ids = self.prompt_ids(question, solution, description)
        s = self.sampling()
        failures: list[str] = []
        attempts = int(self.cfg["max_attempts"])
        for attempt in range(attempts):
            async with self.sem:
                started = time.monotonic()
                try:
                    resp = await self.client.completions.create(
                        model=self.cfg["served_name"], prompt=ids, n=s["n"], temperature=s["temperature"],
                        top_p=s["top_p"], max_tokens=s["max_tokens"], timeout=float(self.cfg["request_timeout_s"]),
                        extra_body={"top_k": s["top_k"], "repetition_penalty": s["repetition_penalty"],
                                    "stop_token_ids": s["stop_token_ids"], "skip_special_tokens": True},
                    )
                except Exception as exc:  # noqa: BLE001
                    retryable, kind = classify_error(exc)
                    failures.append(f"{kind}: {str(exc)[:200]}")
                    if not retryable:
                        raise RewardExecutionError(f"verifier fatal error {kind}: {exc}") from exc
                    resp = None
            if resp is not None:
                choices = sorted(resp.choices, key=lambda c: c.index)
                if len(choices) != s["n"]:
                    failures.append(f"expected {s['n']} samples, got {len(choices)}")
                else:
                    raw = [c.text for c in choices]
                    return {"raw": raw, "labels": [self.vc.parse_prediction(t) for t in raw],
                            "finish_reasons": [c.finish_reason for c in choices], "prompt_tokens": len(ids),
                            "latency_s": round(time.monotonic() - started, 3), "attempts": attempt + 1}
            if attempt + 1 < attempts:
                await _backoff(attempt)
        raise RewardExecutionError(f"verifier failed after {attempts} attempts: {failures[-3:]}")


# --- student-likeness pairwise judge -----------------------------------------

WINNER_SCHEMA = {
    "type": "object",
    "properties": {"winner": {"type": "string", "enum": ["A", "B", "tie"]}},
    "required": ["winner"],
    "additionalProperties": False,
}


def parse_winner(text: str, allow_tie: bool) -> str:
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise SchemaViolation(f"not JSON: {exc}") from exc
    if not isinstance(obj, dict) or set(obj) != {"winner"}:
        raise SchemaViolation(f"unexpected object {obj!r}")
    winner = obj["winner"]
    valid = ("A", "B", "tie") if allow_tie else ("A", "B")
    if winner not in valid:
        raise SchemaViolation(f"winner {winner!r}")
    return winner


class PairwiseJudge:
    def __init__(self, cfg: Mapping[str, Any], system_prompt: str, user_template: str, examples: Sequence[Mapping[str, Any]], client: Any):
        if len(examples) != int(cfg["num_examples"]):
            raise ValueError(f"expected {cfg['num_examples']} examples, got {len(examples)}")
        self.cfg = cfg
        self.system_prompt = system_prompt
        self.user_template = user_template
        self.examples = examples
        self.client = client
        self.backend = cfg["backend"]
        self.sem = asyncio.Semaphore(int(cfg["concurrency"]))
        self.prompt_version = sha256_text(system_prompt + "\n\x00\n" + user_template + "\n\x00\n"
                                          + "".join(e["question"] + "\x00" + e["student_solution"] for e in examples))

    def user_text(self, question: str, solution_a: str, solution_b: str) -> str:
        e1, e2 = self.examples
        return render(self.user_template, {
            "example_1_question": e1["question"], "example_1_solution": e1["student_solution"],
            "example_2_question": e2["question"], "example_2_solution": e2["student_solution"],
            "question_context": question, "solution_A": solution_a, "solution_B": solution_b,
        })

    def decoding_record(self) -> dict[str, Any]:
        if self.backend == "vllm":
            return {"backend": "vllm", "temperature": 0.0, "structured_output": "json_schema"}
        rec = {"backend": "openai", "temperature": "not sent (not supported by reasoning models)", "structured_output": "json_schema"}
        if self.cfg.get("reasoning_effort"):
            rec["reasoning_effort"] = self.cfg["reasoning_effort"]
        return rec

    async def _once(self, user_text: str) -> dict[str, Any]:
        timeout = float(self.cfg["request_timeout_s"])
        if self.backend == "openai":
            payload: dict[str, Any] = {
                "model": self.cfg["model"], "instructions": self.system_prompt,
                "input": [{"role": "user", "content": [{"type": "input_text", "text": user_text}]}],
                "max_output_tokens": int(self.cfg["max_output_tokens"]),
                "text": {"format": {"type": "json_schema", "name": "student_likeness", "schema": WINNER_SCHEMA, "strict": True}},
            }
            if self.cfg.get("reasoning_effort"):
                payload["reasoning"] = {"effort": self.cfg["reasoning_effort"]}
            return await responses_call(self.client, payload, timeout)
        started = time.monotonic()
        resp = await self.client.chat.completions.create(
            model=self.cfg["model"], temperature=0.0, max_tokens=int(self.cfg["max_output_tokens"]), timeout=timeout,
            messages=[{"role": "system", "content": self.system_prompt}, {"role": "user", "content": user_text}],
            response_format={"type": "json_schema", "json_schema": {"name": "student_likeness", "schema": WINNER_SCHEMA, "strict": True}},
        )
        choice = resp.choices[0]
        return {"response_id": resp.id, "request_id": None, "status": "completed",
                "incomplete_reason": "length" if choice.finish_reason == "length" else None,
                "output_text": choice.message.content or "", "usage": _usage(resp), "latency_s": round(time.monotonic() - started, 3)}

    async def compare(self, question: str, solution_a: str, solution_b: str) -> dict[str, Any]:
        user_text = self.user_text(question, solution_a, solution_b)
        failures: list[str] = []
        attempts = int(self.cfg["max_attempts"])
        for attempt in range(attempts):
            async with self.sem:
                try:
                    api = await self._once(user_text)
                except Exception as exc:  # noqa: BLE001
                    retryable, kind = classify_error(exc)
                    failures.append(f"{kind}: {str(exc)[:200]}")
                    if not retryable:
                        raise RewardExecutionError(f"student-likeness judge fatal error {kind}: {exc}") from exc
                    api = None
            if api is not None:
                if api["status"] == "incomplete" or api["incomplete_reason"]:
                    failures.append(f"incomplete: {api['incomplete_reason']}")
                else:
                    try:
                        winner = parse_winner(api["output_text"], bool(self.cfg["allow_tie"]))
                        return {"winner": winner, "raw_text": api["output_text"], "response_id": api["response_id"],
                                "request_id": api["request_id"], "usage": api["usage"], "latency_s": api["latency_s"],
                                "attempts": attempt + 1, "failures": failures}
                    except SchemaViolation as exc:
                        failures.append(f"schema: {exc}")
            if attempt + 1 < attempts:
                await _backoff(attempt)
        raise RewardExecutionError(f"student-likeness judge failed after {attempts} attempts: {failures[-3:]}")
