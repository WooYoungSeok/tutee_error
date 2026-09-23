"""Attach generated error descriptions to copies of the raw source files.

The raw files are only read. Each exported file mirrors one raw file row for
row, with one added key per row (``LABEL_FIELD``):

* labeled rows:  {"labeled": true, "description", "status", "evidence_quote",
                  "sample_id", "run_id"}
* other rows:    {"labeled": false, "reason": <exclusion reason or
                  "not_generated:<processing status>">}

The model's own values are copied as they are; ``description`` may be null and
``status`` may be "ambiguous" or "label_conflict".
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .util import stable_json

LABEL_FIELD = "generated_error_description"


class ExportError(RuntimeError):
    pass


def source_index(source_id: str) -> int:
    """`<relative path>#<row index>` -> row index."""
    return int(source_id.rsplit("#", 1)[1])


def label_payload(result: dict[str, Any] | None, sample_id: str, run_id: str) -> dict[str, Any]:
    if result is None:
        return {"labeled": False, "reason": "not_generated:missing", "sample_id": sample_id}
    if result.get("processing_status") != "ok":
        return {
            "labeled": False,
            "reason": f"not_generated:{result.get('processing_status')}",
            "sample_id": sample_id,
        }
    return {
        "labeled": True,
        "description": result.get("description"),
        "status": result.get("status"),
        "evidence_quote": result.get("evidence_quote"),
        "sample_id": sample_id,
        "run_id": run_id,
    }


def labels_by_source_file(
    index_rows: Iterable[dict[str, Any]],
    results: dict[str, dict[str, Any]],
    run_id: str,
) -> dict[str, dict[int, dict[str, Any]]]:
    """source_file -> {row index -> label payload}, for every indexed record."""
    by_file: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in index_rows:
        if row["eligible"]:
            payload = label_payload(results.get(row["sample_id"]), row["sample_id"], run_id)
        else:
            payload = {"labeled": False, "reason": row["exclusion_reason"]}
        by_file[row["source_file"]][source_index(row["source_id"])] = payload
    return dict(by_file)


# --- reading and writing raw files in their own format ---------------------


def read_rows(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Rows of a .json list or .jsonl file, and how the file was written.

    Blank .jsonl lines are skipped, as in util.read_jsonl, so row indexes match
    the source ids produced by the adapters.
    """
    text = path.read_text(encoding="utf-8")
    fmt = {
        "kind": "jsonl" if path.suffix.lower() == ".jsonl" else "json",
        "ascii": text.isascii(),
        "final_newline": text.endswith("\n"),
    }
    if fmt["kind"] == "jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        rows = json.loads(text)
        if not isinstance(rows, list):
            raise ExportError(f"{path}: expected a JSON list")
        fmt["indent"] = 4 if text.startswith("[\n") else None
    return rows, fmt


def write_rows(path: Path, rows: list[dict[str, Any]], fmt: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt["kind"] == "jsonl":
        text = "\n".join(json.dumps(row, ensure_ascii=fmt["ascii"]) for row in rows)
    else:
        text = json.dumps(rows, ensure_ascii=fmt["ascii"], indent=fmt.get("indent"))
    if fmt.get("final_newline", True) and not text.endswith("\n"):
        text += "\n"
    # "\n" as in the raw files; text mode would write "\r\n" on Windows
    path.write_text(text, encoding="utf-8", newline="\n")


def attach(rows: list[dict[str, Any]], labels: dict[int, dict[str, Any]], where: str) -> list[dict[str, Any]]:
    """New rows with LABEL_FIELD added; the input rows are not modified."""
    if len(labels) != len(rows) or set(labels) != set(range(len(rows))):
        raise ExportError(
            f"{where}: {len(rows)} rows in the file but {len(labels)} indexed records; "
            "rebuild data/full with scripts/build_full_pool.py"
        )
    out = []
    for index, row in enumerate(rows):
        if LABEL_FIELD in row:
            raise ExportError(f"{where}#{index}: the row already has a {LABEL_FIELD!r} key")
        new = dict(row)
        new[LABEL_FIELD] = labels[index]
        out.append(new)
    return out


def row_key(row: dict[str, Any]) -> str:
    """Identity of a raw row, used to label exact copies stored in other files."""
    return stable_json({k: v for k, v in row.items() if k != LABEL_FIELD})


def attach_by_identity(
    rows: list[dict[str, Any]], labels_by_row: dict[str, dict[str, Any]], where: str
) -> list[dict[str, Any]]:
    """Label rows that are exact copies of already labeled rows (e.g. MathEDU leave_one_out)."""
    out = []
    for index, row in enumerate(rows):
        key = row_key(row)
        if key not in labels_by_row:
            raise ExportError(f"{where}#{index}: no identical row in the labeled source files")
        new = dict(row)
        new[LABEL_FIELD] = labels_by_row[key]
        out.append(new)
    return out


def payload_counts(rows: Iterable[dict[str, Any]]) -> Counter:
    counts: Counter = Counter()
    for row in rows:
        payload = row[LABEL_FIELD]
        if payload["labeled"]:
            counts[f"labeled:{payload['status']}"] += 1
        else:
            counts[f"not_labeled:{payload['reason']}"] += 1
    return counts
