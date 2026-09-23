"""Full labeling pool: every eligible record, one request per unique sample id.

The fixed 200-case sample (``data/manifest``) is left untouched. The pool is
built from the same adapters, so a case keeps the same ``sample_id`` in both.

Two outputs:

* ``pool.jsonl`` - one row per unique eligible sample id (first occurrence in
  source order), with ``split = "full"`` and the source ids of every record
  that shares it. This is what the runner sends.
* ``record_index.jsonl`` - one light row per normalized record, eligible or not,
  so the export can attach a label (or an exclusion reason) to each raw row.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable

from .adapters import NormalizedRecord

FULL_SPLIT = "full"


def index_row(record: NormalizedRecord) -> dict[str, Any]:
    return {
        "dataset": record.dataset,
        "source_file": record.source_file,
        "source_id": record.source_id,
        "sample_id": record.sample_id,
        "eligible": record.eligible,
        "exclusion_reason": record.exclusion_reason,
    }


def build_pool(records: Iterable[NormalizedRecord]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Collapse eligible records onto unique sample ids.

    Records with the same sample id have the same question, solution and label,
    so they get one request and share its result.
    """
    first: dict[str, dict[str, Any]] = {}
    sources: dict[str, list[str]] = defaultdict(list)
    exclusions: Counter = Counter()
    read = 0
    for record in records:
        read += 1
        if not record.eligible:
            exclusions[record.exclusion_reason] += 1
            continue
        sources[record.sample_id].append(record.source_id)
        if record.sample_id not in first:
            row = record.to_dict()
            row["split"] = FULL_SPLIT
            first[record.sample_id] = row
    pool = []
    for sample_id, row in first.items():
        row["source_ids"] = sources[sample_id]
        pool.append(row)
    stats = {
        "records_read": read,
        "eligible_records": sum(len(v) for v in sources.values()),
        "unique_requests": len(pool),
        "duplicate_records": sum(len(v) - 1 for v in sources.values()),
        "exclusions": dict(sorted(exclusions.items())),
        "labels": dict(sorted(Counter(r["source_error_label"] for r in pool).items())),
    }
    return pool, stats
