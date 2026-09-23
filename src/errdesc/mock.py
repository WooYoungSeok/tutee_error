"""Offline mock of the API call, for dry runs and tests.

It exercises the same code path as the real client (``run_one`` / ``run_batch``)
without any network access, and can be scripted to return malformed JSON,
truncated responses or transient failures.
"""

from __future__ import annotations

import itertools
import json
import threading
from typing import Any, Callable

_counter = itertools.count(1)
_lock = threading.Lock()


def _next_id(prefix: str) -> str:
    with _lock:
        return f"{prefix}_{next(_counter):06d}"


def make_mock_call(
    behavior: Callable[[str, int], dict[str, Any]] | None = None,
) -> Callable[..., dict[str, Any]]:
    """Return a ``call(client, payload, timeout)`` function.

    ``behavior(prompt_text, call_index)`` may return a dict overriding any of
    ``output_text``, ``response_status``, ``incomplete_reason`` or raise to
    simulate an API exception.
    """
    index = itertools.count(1)

    def call(client: Any, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
        call_index = next(index)
        prompt_text = payload["input"][0]["content"][0]["text"]
        result: dict[str, Any] = {
            "response_id": _next_id("resp_mock"),
            "request_id": _next_id("req_mock"),
            "response_status": "completed",
            "incomplete_reason": None,
            "usage": {
                "input_tokens": max(1, len(prompt_text) // 4),
                "output_tokens": 40,
                "total_tokens": max(1, len(prompt_text) // 4) + 40,
            },
            "output_text": json.dumps(
                {
                    "description": "Mock description of the exemplified error",
                    "evidence_quote": "mock evidence",
                    "status": "ok",
                }
            ),
        }
        if behavior is not None:
            override = behavior(prompt_text, call_index)
            if override:
                result.update(override)
        return result

    return call


class MockClient:
    """Placeholder stand-in; the mock never touches it."""

    api_key = "(mock)"
