"""Human review material: CSV / HTML sheets and run summaries.

The automated flags below are review aids, not verdicts. A flag never changes a
stored description, and a description shared by several cases is not treated as
a failure: reusable descriptions are the goal of the pilot.
"""

from __future__ import annotations

import html
import json
import re
from collections import Counter, defaultdict
from typing import Any, Iterable

from .validate import evidence_found_in_solution

MATH_VOCAB = {
    "add", "adds", "added", "addition", "subtract", "subtracts", "subtraction",
    "multiply", "multiplies", "multiplication", "divide", "divides", "division",
    "fraction", "fractions", "ratio", "ratios", "percent", "percentage",
    "decimal", "decimals", "unit", "units", "convert", "conversion", "total",
    "sum", "difference", "product", "quotient", "average", "mean", "rate",
    "time", "hour", "hours", "minute", "minutes", "day", "days", "week", "weeks",
    "month", "months", "year", "years", "length", "area", "volume", "perimeter",
    "angle", "triangle", "square", "circle", "value", "values", "number",
    "numbers", "step", "steps", "equation", "equations", "variable", "formula",
    "count", "counts", "counting", "amount", "price", "cost", "money", "profit",
    "interest", "distance", "speed", "weight", "quantity", "quantities",
    "problem", "question", "solution", "answer", "calculation", "calculations",
}

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]+")


def description_flags(description: str | None, question: str, solution: str, evidence: str | None) -> dict[str, Any]:
    flags: dict[str, Any] = {}
    text = description or ""
    words = _WORD_RE.findall(text)
    flags["word_count"] = len(words)
    flags["length_outside_5_15_words"] = not (5 <= len(words) <= 15) if text else True
    flags["description_is_null"] = description is None
    flags["contains_digit"] = bool(re.search(r"\d", text))
    question_words = {w.lower() for w in _WORD_RE.findall(question)}
    shared = sorted(
        {
            w.lower()
            for w in words
            if len(w) > 3 and w.lower() in question_words and w.lower() not in MATH_VOCAB
        }
    )
    flags["shared_question_tokens"] = ", ".join(shared)
    flags["evidence_quote_found_in_solution"] = evidence_found_in_solution(evidence or "", solution)
    return flags


def normalize_description(description: str | None) -> str:
    if not description:
        return ""
    return re.sub(r"[^a-z0-9 ]+", "", re.sub(r"\s+", " ", description.lower())).strip()


REVIEW_COLUMNS = [
    "dataset",
    "sample_id",
    "split",
    "source_error_label",
    "question",
    "incorrect_solution",
    "description",
    "evidence_quote",
    "status",
    "processing_status",
    "error",
    "word_count",
    "length_outside_5_15_words",
    "description_is_null",
    "contains_digit",
    "shared_question_tokens",
    "evidence_quote_found_in_solution",
    "duplicate_description_count",
    "source_annotations",
    "review_error_preserved",
    "review_context_removed",
    "review_not_overgeneral",
    "review_comment",
]


def compare_cell(row: dict[str, Any] | None) -> str:
    """One cell holding another run's description for the same case."""
    if row is None:
        return "(not in that run)"
    description = row.get("description")
    if description:
        return str(description)
    status = row.get("status") or row.get("processing_status") or ""
    return f"(no description: {status})" if status else ""


def build_review_rows(
    parsed_rows: Iterable[dict[str, Any]],
    manifest: dict[str, dict[str, Any]],
    compare: dict[str, dict[str, Any]] | None = None,
    compare_name: str = "",
    compares: list[tuple[str, dict[str, dict[str, Any]]]] | None = None,
) -> list[dict[str, Any]]:
    """`compares` adds one column per other run, in the given order.

    `compare` / `compare_name` remain for the single-run case.
    """
    if compares is None:
        compares = [(compare_name, compare)] if compare is not None else []
    parsed_rows = list(parsed_rows)
    dup_counts = Counter(
        normalize_description(r.get("description")) for r in parsed_rows if r.get("description")
    )
    rows: list[dict[str, Any]] = []
    for parsed in parsed_rows:
        record = manifest.get(parsed["sample_id"], {})
        flags = description_flags(
            parsed.get("description"),
            record.get("question", ""),
            record.get("incorrect_solution", ""),
            parsed.get("evidence_quote"),
        )
        key = normalize_description(parsed.get("description"))
        row = {
            "dataset": parsed["dataset"],
            "sample_id": parsed["sample_id"],
            "split": parsed.get("split", ""),
            "source_error_label": record.get("source_error_label", parsed.get("source_error_label", "")),
            "question": record.get("question", ""),
            "incorrect_solution": record.get("incorrect_solution", ""),
            "description": parsed.get("description"),
            "evidence_quote": parsed.get("evidence_quote"),
            "status": parsed.get("status"),
            "processing_status": parsed.get("processing_status"),
            "error": parsed.get("error", ""),
            "duplicate_description_count": dup_counts.get(key, 0) if key else 0,
            "source_annotations": json.dumps(record.get("annotations", {}), ensure_ascii=False),
            "review_error_preserved": "",
            "review_context_removed": "",
            "review_not_overgeneral": "",
            "review_comment": "",
        }
        row.update(flags)
        if compares:
            row["compare_descriptions"] = {
                name: compare_cell(rows_by_id.get(parsed["sample_id"]))
                for name, rows_by_id in compares
            }
            row["compare_names"] = [name for name, _ in compares]
            # kept for the single-run call sites
            row["compare_description"] = row["compare_descriptions"][compares[0][0]]
            row["compare_name"] = compares[0][0]
        rows.append(row)
    rows.sort(key=lambda r: (r["dataset"], r["split"], r["sample_id"]))
    return rows


def render_html(rows: list[dict[str, Any]], title: str, self_label: str = "") -> str:
    head = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title><style>"
        "body{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;margin:1rem;}"
        "table{border-collapse:collapse;width:100%;font-size:13px;}"
        "th,td{border:1px solid #d0d0d0;padding:6px;vertical-align:top;text-align:left;}"
        "th{background:#f3f4f6;position:sticky;top:0;}"
        "td.q,td.r{white-space:pre-wrap;max-width:480px;}"
        "td.c{font-weight:600;max-width:280px;}"
        "td.other{font-weight:400;color:#374151;background:#f8fafc;}"
        ".flag{color:#b91c1c;font-weight:600;}"
        "tr:nth-child(even){background:#fafafa;}"
        "</style></head><body>"
    )
    parts = [head, f"<h1>{html.escape(title)}</h1>", f"<p>{len(rows)} cases</p>", "<table><thead><tr>"]
    compare_names = rows[0].get("compare_names", []) if rows else []
    own = f"description (C) — {self_label} (this run)" if self_label else "description (C)"
    headers = [
        "dataset", "sample_id", "split", "label (A)", "question (Q)", "incorrect solution (R)",
        own,
    ]
    headers += [f"description (C) — {name}" for name in compare_names]
    headers += [
        "evidence_quote", "status", "processing", "flags",
        "source annotations", "reviewer notes",
    ]
    parts.extend(f"<th>{html.escape(h)}</th>" for h in headers)
    parts.append("</tr></thead><tbody>")
    for row in rows:
        flags = []
        if row["description_is_null"]:
            flags.append("null description")
        if row["length_outside_5_15_words"]:
            flags.append(f"{row['word_count']} words")
        if row["contains_digit"]:
            flags.append("contains digit")
        if row["shared_question_tokens"]:
            flags.append(f"shares: {row['shared_question_tokens']}")
        if not row["evidence_quote_found_in_solution"]:
            flags.append("evidence not found verbatim")
        if row["duplicate_description_count"] > 1:
            flags.append(f"same C in {row['duplicate_description_count']} cases")
        parts.append("<tr>")
        parts.append(f"<td>{html.escape(row['dataset'])}</td>")
        parts.append(f"<td>{html.escape(row['sample_id'])}</td>")
        parts.append(f"<td>{html.escape(row['split'])}</td>")
        parts.append(f"<td>{html.escape(str(row['source_error_label']))}</td>")
        parts.append(f"<td class='q'>{html.escape(row['question'])}</td>")
        parts.append(f"<td class='r'>{html.escape(row['incorrect_solution'])}</td>")
        parts.append(f"<td class='c'>{html.escape(str(row['description']))}</td>")
        for name in compare_names:
            cell = row.get("compare_descriptions", {}).get(name, "")
            parts.append(f"<td class='c other'>{html.escape(str(cell))}</td>")
        parts.append(f"<td>{html.escape(str(row['evidence_quote']))}</td>")
        parts.append(f"<td>{html.escape(str(row['status']))}</td>")
        parts.append(f"<td>{html.escape(str(row['processing_status']))}</td>")
        parts.append(f"<td class='flag'>{html.escape('; '.join(flags))}</td>")
        parts.append(f"<td>{html.escape(row['source_annotations'][:600])}</td>")
        parts.append("<td></td>")
        parts.append("</tr>")
    parts.append("</tbody></table></body></html>")
    return "".join(parts)


def summarize(rows: list[dict[str, Any]], run_meta: dict[str, Any]) -> str:
    by_dataset: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_dataset[row["dataset"]].append(row)

    lines = [f"# Run summary — {run_meta.get('run_id', '?')}", ""]
    lines.append(f"- model: `{run_meta.get('model')}`" + ("  (MOCK RUN)" if run_meta.get("mock") else ""))
    lines.append(f"- prompt: `{run_meta.get('prompt_file')}` version {run_meta.get('prompt_version')} sha256 `{str(run_meta.get('prompt_sha256'))[:16]}`")
    lines.append(f"- split: {run_meta.get('split')} · cases: {len(rows)}")
    lines.append(f"- finished (UTC): {run_meta.get('finished_at_utc')}")
    lines.append("")

    lines.append("## Processing status (request level)")
    lines.append("")
    counts = Counter(r["processing_status"] for r in rows)
    lines.append("| processing_status | count |")
    lines.append("| --- | --- |")
    for key, value in sorted(counts.items()):
        lines.append(f"| {key} | {value} |")
    lines.append("")

    lines.append("## Model status by dataset (data level)")
    lines.append("")
    statuses = ["ok", "ambiguous", "label_conflict", "(none)"]
    lines.append("| dataset | cases | " + " | ".join(statuses) + " |")
    lines.append("| --- | --- |" + "|".join([" --- "] * len(statuses)) + "|")
    for dataset in sorted(by_dataset):
        subset = by_dataset[dataset]
        counter = Counter(r["status"] or "(none)" for r in subset)
        lines.append(
            f"| {dataset} | {len(subset)} | " + " | ".join(str(counter.get(s, 0)) for s in statuses) + " |"
        )
    lines.append("")

    lines.append("## Description length (words)")
    lines.append("")
    lines.append("| dataset | n with description | min | median | max | outside 5-15 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for dataset in sorted(by_dataset):
        lengths = sorted(r["word_count"] for r in by_dataset[dataset] if r["description"])
        if not lengths:
            lines.append(f"| {dataset} | 0 | - | - | - | - |")
            continue
        median = lengths[len(lengths) // 2]
        outside = sum(
            1 for r in by_dataset[dataset] if r["description"] and r["length_outside_5_15_words"]
        )
        lines.append(
            f"| {dataset} | {len(lengths)} | {lengths[0]} | {median} | {lengths[-1]} | {outside} |"
        )
    lines.append("")

    lines.append("## Repeated descriptions")
    lines.append("")
    dup = Counter(
        normalize_description(r["description"]) for r in rows if r["description"]
    )
    repeated = [(k, v) for k, v in dup.items() if v > 1]
    if repeated:
        lines.append(
            f"{len(repeated)} description(s) appear more than once "
            f"({sum(v for _, v in repeated)} cases). Reuse across questions is expected, "
            "not an automatic failure."
        )
        lines.append("")
        lines.append("| description (normalized) | count |")
        lines.append("| --- | --- |")
        for key, value in sorted(repeated, key=lambda kv: (-kv[1], kv[0]))[:25]:
            lines.append(f"| {key} | {value} |")
    else:
        lines.append("Every description is distinct.")
    lines.append("")

    lines.append("## Automated review flags")
    lines.append("")
    flag_counts = {
        "null description": sum(1 for r in rows if r["description_is_null"]),
        "outside 5-15 words": sum(1 for r in rows if r["description"] and r["length_outside_5_15_words"]),
        "contains a digit": sum(1 for r in rows if r["contains_digit"]),
        "shares an uncommon token with the question": sum(1 for r in rows if r["shared_question_tokens"]),
        "evidence_quote not found verbatim": sum(
            1 for r in rows if not r["evidence_quote_found_in_solution"]
        ),
    }
    lines.append("| flag | cases |")
    lines.append("| --- | --- |")
    for key, value in flag_counts.items():
        lines.append(f"| {key} | {value} |")
    lines.append("")
    lines.append(
        "These flags mark rows worth a look. They are not correctness judgements, "
        "and no stored response was edited to satisfy them."
    )
    lines.append("")

    usage = run_meta.get("usage_totals") or {}
    lines.append("## Tokens and errors")
    lines.append("")
    lines.append(f"- token usage totals: {usage}")
    lines.append(
        f"- failed requests: {sum(v for k, v in counts.items() if k != 'ok')} "
        f"(non-ok processing statuses)"
    )
    lines.append(
        "- cost: not computed here. Multiply the token totals by the price you "
        "confirmed for this model; reasoning tokens, if any, are billed as output tokens."
    )
    lines.append("")
    lines.append("## Review criteria (fill in the review columns)")
    lines.append("")
    lines.append("1. error preserved — does C point at the error in R and A?")
    lines.append("2. context removed — would C still apply with different story, values and step order?")
    lines.append("3. not over-general — is C more than a statement that fits almost any wrong answer?")
    lines.append("")
    lines.append(
        "Also note unsupported claims about missing knowledge, and disagreements "
        "with the source annotations."
    )
    return "\n".join(lines) + "\n"
