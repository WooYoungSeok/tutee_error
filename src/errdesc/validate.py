"""Validation of the model's JSON output.

``processing_status`` describes what happened to the *request* (ok, malformed
JSON, invalid schema, truncated output, API failure). It is kept separate from
the model's own ``status`` field (ok / ambiguous / label_conflict), which is a
statement about the data.
"""

from __future__ import annotations

import json
import re
from typing import Any

VALID_STATUSES = ("ok", "ambiguous", "label_conflict")
REQUIRED_KEYS = ("description", "evidence_quote", "status")

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


class ParseResult(dict):
    """dict with: parsed, processing_status, error, repaired, extra_keys."""


def parse_output(text: str | None) -> ParseResult:
    result = ParseResult(
        parsed=None, processing_status="ok", error="", repaired=False, extra_keys=[]
    )
    if text is None or not text.strip():
        result["processing_status"] = "empty_response"
        result["error"] = "model returned no text"
        return result

    payload: Any = None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        match = _FENCE_RE.match(text)
        if match:
            try:
                payload = json.loads(match.group(1))
                result["repaired"] = True
            except json.JSONDecodeError as exc2:
                result["processing_status"] = "json_parse_error"
                result["error"] = f"{exc2}"
                return result
        else:
            result["processing_status"] = "json_parse_error"
            result["error"] = f"{exc}"
            return result

    if not isinstance(payload, dict):
        result["processing_status"] = "schema_invalid"
        result["error"] = f"expected a JSON object, got {type(payload).__name__}"
        return result

    problems: list[str] = []
    missing = [k for k in REQUIRED_KEYS if k not in payload]
    if missing:
        problems.append(f"missing key(s): {', '.join(missing)}")

    description = payload.get("description")
    if not (description is None or isinstance(description, str)):
        problems.append("description must be a string or null")
    elif isinstance(description, str) and description.strip().lower() in {"null", "none"}:
        problems.append('description is the string "null" instead of JSON null')

    evidence = payload.get("evidence_quote")
    if not isinstance(evidence, str):
        problems.append("evidence_quote must be a string")

    status = payload.get("status")
    if not isinstance(status, str):
        problems.append("status must be a string")
    elif status not in VALID_STATUSES:
        problems.append(
            f"status must be one of {VALID_STATUSES}, got {status!r}"
        )

    result["extra_keys"] = sorted(set(payload) - set(REQUIRED_KEYS))
    if problems:
        result["processing_status"] = "schema_invalid"
        result["error"] = "; ".join(problems)
        result["parsed"] = payload
        return result

    result["parsed"] = {
        "description": description,
        "evidence_quote": evidence,
        "status": status,
    }
    return result


def evidence_found_in_solution(evidence: str, solution: str) -> bool:
    """Loose containment check used only to flag rows for human review."""
    if not evidence or not evidence.strip():
        return False

    def squash(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower()

    return squash(evidence) in squash(solution)
