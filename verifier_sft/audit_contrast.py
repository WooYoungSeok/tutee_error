#!/usr/bin/env python3
"""LLM audit of contrast candidates: aligned / not_aligned / unclear for each (Q, S, C) row.

The auditor sees only the question, the solution and the description (never the origin or any
source label) and answers with JSON: required_behavior, observed_behavior, verdict. The reasons
stay in the audit record; training rows later use the verdict only (unclear rows are dropped).

The verdicts are used as labels without human review (researcher decision 2026-09-29: the prompt is
fixed after a reviewed pilot, then the auditor is trusted).

Every response is appended to <audit_dir>/audit_responses.jsonl as it arrives, so a re-run with the
same settings only calls the missing rows (pilot rows are reused by the full run when the prompt and
settings are unchanged). A row whose call failed or whose output breaks the schema is not labelled:
the script stops before writing labels and a re-run retries it.

Outputs (<audit_dir>/, or <audit_dir>/pilot/ with --pilot):
  audit_responses.jsonl   raw API records, shared by pilot and full run (git-ignored)
  audits.jsonl            one row per candidate: candidate fields + verdict + reasons
  audit_summary.md        verdict counts per split × origin × same source label
  pilot_review.md         (--pilot) every row in full, with the source labels the auditor did not see

Usage (from verifier_sft/, OPENAI_API_KEY in ../.env):
    python audit_contrast.py --config config/strict_contrast_v1.json --dry_run      # no call
    python audit_contrast.py --config config/strict_contrast_v1.json --pilot        # 20 half-A rows, draft prompt allowed
    python audit_contrast.py --config config/strict_contrast_v1.json                # needs audit.approved
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from verifier_common import load_config, read_jsonl, render_user, resolve, sha256_file, write_jsonl  # noqa: E402

VERDICTS = ("aligned", "not_aligned", "unclear")
AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "required_behavior": {"type": "string"},
        "observed_behavior": {"type": "string"},
        "verdict": {"type": "string", "enum": list(VERDICTS)},
    },
    "required": ["required_behavior", "observed_behavior", "verdict"],
    "additionalProperties": False,
}


class AuditSchemaError(ValueError):
    pass


def parse_audit(text: str | None) -> dict[str, str]:
    """Strict: a JSON object with exactly the three fields and a known verdict."""
    try:
        obj = json.loads(text or "")
    except json.JSONDecodeError as exc:
        raise AuditSchemaError(f"not JSON: {exc}") from exc
    if not isinstance(obj, dict) or set(obj) != set(AUDIT_SCHEMA["required"]):
        raise AuditSchemaError(f"unexpected keys: {sorted(obj) if isinstance(obj, dict) else type(obj).__name__}")
    if obj["verdict"] not in VERDICTS:
        raise AuditSchemaError(f"verdict {obj['verdict']!r}")
    if not all(isinstance(obj[k], str) for k in obj):
        raise AuditSchemaError("fields must be strings")
    return obj


def build_payload(audit: dict[str, Any], system: str, user_template: str, row: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": audit["model"],
        "instructions": system,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": render_user(user_template, row)}]}],
        "max_output_tokens": audit["max_output_tokens"],
    }
    if audit.get("structured_output"):
        payload["text"] = {"format": {"type": "json_schema", "name": "label_audit", "schema": AUDIT_SCHEMA, "strict": True}}
    if audit.get("reasoning_effort"):
        payload["reasoning"] = {"effort": audit["reasoning_effort"]}
    return payload


def pilot_rows(rows: list[dict[str, Any]], n_own: int, n_same: int, n_diff: int, seed: int) -> list[dict[str, Any]]:
    """Half-A pilot: cross rows from distinct question groups (n_same with the same source label, n_diff with a
    different one), plus the own rows of the first n_own of those cross rows' solutions, so the same solution is
    seen with its own and with a sibling's description."""
    rng = random.Random(seed)
    half_a = sorted((r for r in rows if r["half"] == "A"), key=lambda r: r["candidate_id"])
    own = {r["solution_sample_id"]: r for r in half_a if r["origin"] == "own"}
    cross = [r for r in half_a if r["origin"] != "own"]
    rng.shuffle(cross)
    picked, groups = [], set()
    for same, n in ((True, n_same), (False, n_diff)):
        for r in cross:
            if n and r["same_source_label"] == same and r["question_group_id"] not in groups:
                picked.append(r)
                groups.add(r["question_group_id"])
                n -= 1
    rng.shuffle(picked)
    owns = [own[r["solution_sample_id"]] for r in picked[:n_own]]
    return sorted(owns + picked, key=lambda r: (r["question_group_id"], r["solution_sample_id"], r["origin"] != "own"))


def write_pilot_review(path: Path, audits: list[dict[str, Any]]) -> None:
    L = ["# Audit pilot — every row in full", "",
         "The auditor saw only the question, the solution and the description. Origin and source labels are shown "
         "here for the reviewer only.", ""]
    for i, a in enumerate(audits, 1):
        L += [f"## {i}. {a['origin']} · verdict **{a['verdict']}**", "",
              f"- dataset {a['dataset']} · question group `{a['question_group_id']}` · candidate `{a['candidate_id']}`",
              f"- solution source label: {a['solution_source_label']} · description source label: {a['description_source_label']}"
              f" (same: {a['same_source_label']})", "",
              "**Question**", "", a["question"], "", "**Solution**", "", "```", a["solution"], "```", "",
              f"**Description**: {a['error_description']}", "",
              f"**required_behavior**: {a['required_behavior']}", "",
              f"**observed_behavior**: {a['observed_behavior']}", ""]
    path.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


def write_summary(path: Path, config: dict[str, Any], settings: dict[str, Any], audits: list[dict[str, Any]]) -> None:
    L = [f"# Audit summary — {config['experiment']}", ""]
    L += [f"Model `{settings['model']}` · reasoning effort {settings['reasoning_effort'] or 'model default'} · "
          f"system `{settings['system_sha256'][:16]}` · user `{settings['user_sha256'][:16]}`", ""]
    L += ["Verdicts are used as labels without human review. `unclear` rows are excluded from training.", ""]
    L += ["| split | origin | same source label | rows | aligned | not_aligned | unclear |", "| --- | --- | --- | --- | --- | --- | --- |"]
    cells: dict[tuple, Counter] = defaultdict(Counter)
    for a in audits:
        cells[(a["split"], a["origin"], a["same_source_label"])][a["verdict"]] += 1
    for (s, o, sl), c in sorted(cells.items(), key=str):
        n = sum(c.values())
        L += [f"| {s} | {o} | {sl} | {n} | " + " | ".join(f"{c[v]} ({100 * c[v] / n:.0f}%)" for v in VERDICTS) + " |"]
    L += [""]
    path.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True)
    parser.add_argument("--candidates", default=None, help="default: output.candidates")
    parser.add_argument("--pilot", action="store_true", help="20 half-A rows (5 own, 7 + 8 cross); draft prompt allowed")
    parser.add_argument("--dry_run", action="store_true", help="print one request, call nothing")
    args = parser.parse_args()

    config = load_config(args.config)
    audit = config["audit"]
    rows = read_jsonl(resolve(args.candidates or config["output"]["candidates"]))
    if not audit.get("audit_own_rows", True):
        rows = [r for r in rows if r["origin"] != "own"]
    if args.pilot:
        rows = pilot_rows(rows, n_own=5, n_same=7, n_diff=8, seed=config.get("seed", 42))
    system = resolve(audit["system"]).read_text(encoding="utf-8")
    user_template = resolve(audit["user"]).read_text(encoding="utf-8")
    settings = {
        "model": audit["model"],
        "reasoning_effort": audit.get("reasoning_effort"),
        "max_output_tokens": audit["max_output_tokens"],
        "structured_output": audit.get("structured_output"),
        "system_sha256": sha256_file(resolve(audit["system"])),
        "user_sha256": sha256_file(resolve(audit["user"])),
    }

    if args.dry_run:
        print(json.dumps(build_payload(audit, system, user_template, rows[0]), ensure_ascii=False, indent=2))
        print(f"\n{len(rows)} candidate rows would be audited with {settings}")
        return 0
    if not audit.get("approved") and not args.pilot:
        raise SystemExit("audit.approved is false: the audit prompt and settings are a draft awaiting review")

    base_dir = resolve(config["output"]["audit_dir"])
    cache_path = base_dir / "audit_responses.jsonl"
    out_dir = base_dir / "pilot" if args.pilot else base_dir
    done: dict[str, dict[str, Any]] = {}
    if cache_path.exists():
        for rec in read_jsonl(cache_path):
            if rec["settings"] == settings and rec.get("error") is None:
                done[rec["candidate_id"]] = rec
    todo = [r for r in rows if r["candidate_id"] not in done]
    print(f"{len(rows)} rows · {len(rows) - len(todo)} cached · {len(todo)} to call · model {audit['model']}")

    if todo:
        from errdesc.runner import call_once, load_dotenv

        load_dotenv(HERE.parent / ".env")
        from openai import OpenAI

        client = OpenAI(max_retries=audit["max_retries"], timeout=audit["timeout_s"])
        base_dir.mkdir(parents=True, exist_ok=True)
        lock = threading.Lock()
        counter = {"n": 0}

        def call(row: dict[str, Any]) -> None:
            rec: dict[str, Any] = {"candidate_id": row["candidate_id"], "settings": settings, "error": None}
            try:
                rec.update(call_once(client, build_payload(audit, system, user_template, row), audit["timeout_s"]))
                if rec.get("incomplete_reason"):
                    raise AuditSchemaError(f"incomplete: {rec['incomplete_reason']}")
                rec["parsed"] = parse_audit(rec.get("output_text"))
            except Exception as exc:  # noqa: BLE001 - recorded; the row stays unlabelled and is retried next run
                rec["error"] = f"{type(exc).__name__}: {exc}"
            with lock:
                with cache_path.open("a", encoding="utf-8", newline="\n") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if rec["error"] is None:
                    done[row["candidate_id"]] = rec
                counter["n"] += 1
                if counter["n"] % 25 == 0 or counter["n"] == len(todo):
                    print(f"  {counter['n']}/{len(todo)}", flush=True)

        with ThreadPoolExecutor(max_workers=max(1, audit["concurrency"])) as pool:
            list(pool.map(call, todo))

    missing = [r["candidate_id"] for r in rows if r["candidate_id"] not in done]
    if missing:
        print(f"{len(missing)} row(s) failed; no labels written. Re-run to retry. Errors in {cache_path}")
        return 1

    audits = []
    for r in rows:
        rec = done[r["candidate_id"]]
        audits.append({**r, **rec["parsed"], "audit_model": audit["model"], "audit_response_id": rec.get("response_id")})
    write_jsonl(out_dir / "audits.jsonl", audits)
    write_summary(out_dir / "audit_summary.md", config, settings, audits)
    if args.pilot:
        write_pilot_review(out_dir / "pilot_review.md", audits)
    print(f"verdicts {dict(Counter(a['verdict'] for a in audits))} -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
