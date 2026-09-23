"""Prompt loading and safe placeholder substitution.

The confirmed prompt contains a JSON example with literal ``{`` / ``}``, so
``str.format`` cannot be used. Exactly three placeholders are substituted, in a
single left-to-right pass: substituted text is never re-scanned, so a solution
that itself contains ``{question}`` stays untouched.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .util import hash_obj, sha256_text

PLACEHOLDERS = ("question", "incorrect_solution", "source_error_label")
_PATTERN = re.compile("|".join(re.escape("{" + name + "}") for name in PLACEHOLDERS))


class PromptError(RuntimeError):
    pass


def load_prompt(path: Path) -> tuple[str, str]:
    """Return (template_text, sha256_of_template)."""
    if not path.exists():
        raise PromptError(f"prompt file not found: {path}")
    text = path.read_text(encoding="utf-8")
    missing = [name for name in PLACEHOLDERS if "{" + name + "}" not in text]
    if missing:
        raise PromptError(f"prompt {path} is missing placeholder(s): {', '.join(missing)}")
    return text, sha256_text(text)


def render_prompt(template: str, values: dict[str, str]) -> str:
    missing = [name for name in PLACEHOLDERS if name not in values]
    if missing:
        raise PromptError(f"missing input value(s): {', '.join(missing)}")

    def replace(match: re.Match[str]) -> str:
        name = match.group(0)[1:-1]
        return str(values[name])

    return _PATTERN.sub(replace, template)


def input_values(record: dict[str, Any]) -> dict[str, str]:
    """The three fields sent to the API. Annotations and raw records stay out."""
    return {
        "question": record["question"],
        "incorrect_solution": record["incorrect_solution"],
        "source_error_label": record["source_error_label"],
    }


def input_hash(record: dict[str, Any]) -> str:
    return hash_obj(input_values(record))
