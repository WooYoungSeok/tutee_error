"""API runner: one request per case, resumable, with strict output validation.

Design notes
------------
* The model id is a required, explicit setting. There is no fallback model.
* Only three fields are sent (question, incorrect solution, source label).
* A request is cached as done only when it produced a valid, complete response.
  Truncated output ("incomplete" / max_output_tokens) is never treated as success.
* Retries cover 429, timeouts and transient server/network errors only.
  Authentication, unknown model and unsupported-parameter errors surface at once.
* Every attempt is logged with its response id, so a retry after a timeout can
  be reconciled with billing. Exactly-once delivery is not claimed.
"""

from __future__ import annotations

import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from .prompt import input_hash, input_values, render_prompt
from .util import append_jsonl, hash_obj, read_jsonl, utc_now
from .validate import parse_output

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}


class FatalAPIError(RuntimeError):
    """Configuration-level failure: retrying cannot help."""


def load_dotenv(dotenv_path: Path, override: bool = True) -> list[str]:
    """Minimal .env loader (same convention as the sibling tutee project).

    The project .env wins over an already exported variable by default, so a
    stale OPENAI_API_KEY in the shell cannot silently shadow the key set for
    this project. Returns the names of the variables it set.
    """
    if not dotenv_path.exists():
        return []
    applied: list[str] = []
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        if key in os.environ and not override:
            continue
        os.environ[key] = value
        applied.append(key)
    return applied


@dataclass
class GenerationSettings:
    model: str
    max_output_tokens: int = 1200
    temperature: float | None = None
    reasoning_effort: str | None = None
    response_format_json: bool = False
    request_timeout_s: int = 180
    max_retries: int = 4
    concurrency: int = 2

    def signature(self) -> dict[str, Any]:
        """The settings that make a cached response reusable."""
        return {
            "model": self.model,
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
            "reasoning_effort": self.reasoning_effort,
            "response_format_json": self.response_format_json,
        }


def request_key(sample_id: str, in_hash: str, prompt_hash: str, settings: GenerationSettings) -> str:
    return hash_obj(
        {
            "sample_id": sample_id,
            "input_hash": in_hash,
            "prompt_hash": prompt_hash,
            "generation": settings.signature(),
        }
    )


def build_request(prompt_text: str, settings: GenerationSettings) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": settings.model,
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt_text}],
            }
        ],
        "max_output_tokens": settings.max_output_tokens,
    }
    if settings.temperature is not None:
        payload["temperature"] = settings.temperature
    if settings.reasoning_effort:
        payload["reasoning"] = {"effort": settings.reasoning_effort}
    if settings.response_format_json:
        payload["text"] = {"format": {"type": "json_object"}}
    return payload


def classify_error(exc: Exception) -> tuple[bool, str]:
    """Return (retryable, kind)."""
    name = type(exc).__name__
    status = getattr(exc, "status_code", None)
    if name in {"AuthenticationError", "PermissionDeniedError", "NotFoundError"}:
        return False, name
    if name in {"BadRequestError", "UnprocessableEntityError"}:
        return False, name
    if name in {"RateLimitError", "APITimeoutError", "APIConnectionError", "InternalServerError"}:
        return True, name
    if isinstance(status, int):
        return status in RETRYABLE_STATUS, f"{name}({status})"
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True, name
    return False, name


def _response_to_record(response: Any) -> dict[str, Any]:
    """Extract the fields we persist from a Responses API object."""
    data: dict[str, Any] = {}
    data["response_id"] = getattr(response, "id", None)
    data["response_status"] = getattr(response, "status", None)
    incomplete = getattr(response, "incomplete_details", None)
    data["incomplete_reason"] = getattr(incomplete, "reason", None) if incomplete else None
    text = getattr(response, "output_text", None)
    if text is None:  # older/alternative shapes
        chunks = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", "") in {"output_text", "text"}:
                    chunks.append(getattr(content, "text", ""))
        text = "".join(chunks)
    data["output_text"] = text
    usage = getattr(response, "usage", None)
    if usage is not None:
        data["usage"] = usage.model_dump() if hasattr(usage, "model_dump") else dict(usage)
    else:
        data["usage"] = None
    return data


def call_once(client: Any, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    raw = client.responses.with_raw_response.create(timeout=timeout, **payload)
    request_id = raw.headers.get("x-request-id") if hasattr(raw, "headers") else None
    response = raw.parse()
    record = _response_to_record(response)
    record["request_id"] = request_id
    return record


def run_one(
    client: Any,
    record: dict[str, Any],
    prompt_template: str,
    prompt_hash: str,
    prompt_version: str,
    settings: GenerationSettings,
    call: Callable[..., dict[str, Any]] = call_once,
) -> dict[str, Any]:
    values = input_values(record)
    prompt_text = render_prompt(prompt_template, values)
    in_hash = input_hash(record)
    key = request_key(record["sample_id"], in_hash, prompt_hash, settings)

    out: dict[str, Any] = {
        "request_key": key,
        "sample_id": record["sample_id"],
        "dataset": record["dataset"],
        "split": record.get("split", ""),
        "source_error_label": record["source_error_label"],
        "prompt_version": prompt_version,
        "prompt_hash": prompt_hash,
        "input_hash": in_hash,
        "generation": settings.signature(),
        "requested_at_utc": utc_now(),
        "attempts": [],
    }

    payload = build_request(prompt_text, settings)
    delay = 2.0
    for attempt in range(1, settings.max_retries + 1):
        started = time.monotonic()
        attempt_log: dict[str, Any] = {"attempt": attempt, "started_at_utc": utc_now()}
        try:
            api = call(client, payload, settings.request_timeout_s)
        except Exception as exc:  # noqa: BLE001 - classified right below
            retryable, kind = classify_error(exc)
            attempt_log.update(
                {
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "error_kind": kind,
                    "error": str(exc)[:500],
                    "retryable": retryable,
                    "request_id": getattr(exc, "request_id", None),
                }
            )
            out["attempts"].append(attempt_log)
            if not retryable:
                raise FatalAPIError(f"{kind}: {exc}") from exc
            if attempt == settings.max_retries:
                out.update(
                    {
                        "processing_status": "api_error",
                        "error": f"{kind}: {exc}"[:500],
                        "parsed": None,
                        "raw_output_text": None,
                    }
                )
                return out
            time.sleep(delay + random.uniform(0, 0.5))
            delay = min(delay * 2, 30)
            continue

        latency_ms = int((time.monotonic() - started) * 1000)
        attempt_log.update(
            {
                "latency_ms": latency_ms,
                "response_id": api.get("response_id"),
                "request_id": api.get("request_id"),
                "response_status": api.get("response_status"),
            }
        )
        out["attempts"].append(attempt_log)

        out.update(
            {
                "response_id": api.get("response_id"),
                "request_id": api.get("request_id"),
                "response_status": api.get("response_status"),
                "incomplete_reason": api.get("incomplete_reason"),
                "usage": api.get("usage"),
                "latency_ms": latency_ms,
                "raw_output_text": api.get("output_text"),
                "completed_at_utc": utc_now(),
            }
        )

        if api.get("response_status") == "incomplete" or api.get("incomplete_reason"):
            out.update(
                {
                    "processing_status": "truncated",
                    "error": f"incomplete response: {api.get('incomplete_reason')}",
                    "parsed": None,
                }
            )
            return out

        parsed = parse_output(api.get("output_text"))
        out.update(
            {
                "processing_status": parsed["processing_status"],
                "error": parsed["error"],
                "parsed": parsed["parsed"],
                "json_repaired": parsed["repaired"],
                "extra_keys": parsed["extra_keys"],
            }
        )
        return out

    return out  # pragma: no cover - loop always returns


def load_completed(raw_path: Path) -> dict[str, dict]:
    """Request keys already completed successfully, from a previous run."""
    done: dict[str, dict] = {}
    if not raw_path.exists():
        return done
    for row in read_jsonl(raw_path):
        if row.get("processing_status") == "ok" and row.get("request_key"):
            done[row["request_key"]] = row
    return done


def run_batch(
    client: Any,
    records: Iterable[dict[str, Any]],
    prompt_template: str,
    prompt_hash: str,
    prompt_version: str,
    settings: GenerationSettings,
    raw_path: Path,
    call: Callable[..., dict[str, Any]] = call_once,
    on_result: Callable[[dict], None] | None = None,
) -> list[dict[str, Any]]:
    records = list(records)
    completed = load_completed(raw_path)
    lock = threading.Lock()
    results: list[dict[str, Any]] = []
    pending = []
    for record in records:
        key = request_key(
            record["sample_id"], input_hash(record), prompt_hash, settings
        )
        if key in completed:
            row = dict(completed[key])
            row["reused_from_previous_run"] = True
            results.append(row)
            if on_result:
                on_result(row)
        else:
            pending.append(record)

    fatal: list[Exception] = []

    def work(record: dict[str, Any]) -> None:
        if fatal:
            return
        try:
            row = run_one(
                client, record, prompt_template, prompt_hash, prompt_version, settings, call=call
            )
        except FatalAPIError as exc:
            with lock:
                fatal.append(exc)
            return
        with lock:
            append_jsonl(raw_path, row)
            results.append(row)
            if on_result:
                on_result(row)

    if pending:
        with ThreadPoolExecutor(max_workers=max(1, settings.concurrency)) as pool:
            list(pool.map(work, pending))

    if fatal:
        raise fatal[0]
    return results
