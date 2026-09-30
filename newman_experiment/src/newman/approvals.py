"""User approval of draft research texts (user rule 1: research design is confirmed with the user first).

Draft texts already exist (taxonomy definitions, verifier/Student prompts, the GSM8K answer contract, the reused
judge prompts, the verifier backbones). An approval records the sha256 of the exact files (or the exact config
values) the user approved; a real run refuses to start unless every item it uses is approved and unchanged
since. Smoke runs (run name smoke_*) record the status but are never blocked. Open decisions without a draft stay
`REQUIRED` in the configs instead (common.find_required).

Approve after the user has confirmed the content:  python scripts/approve.py <item> --note "..."
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from .common import get_path, hash_obj, load_config, now_iso, rel, resolve, sha256_file

APPROVALS_FILE = "configs/approvals.yaml"

ITEMS: dict[str, dict[str, Any]] = {
    "taxonomy_definitions": {
        "what": "Newman stage and source error-type names/definitions read by the Student and both verifiers",
        "files": ["configs/taxonomy.yaml"]},
    "verifier_prompt": {
        "what": "binary verifier system/user prompt (plan 6.1 draft)",
        "files": ["prompts/verifier_system.txt", "prompts/verifier_user.txt"]},
    "student_prompt": {
        "what": "Student instruction (plan 7 draft)",
        "files": ["prompts/student.txt"]},
    "answer_judge_prompt": {
        "what": "gpt-5-nano answer extraction/grading prompt (Eedi run's approved text, reused) + GSM8K answer contract (draft)",
        "files": ["../rl/prompts/answer_judge_system.txt", "../rl/prompts/answer_judge_user.txt", "prompts/gsm8k_answer_contract.txt"]},
    "student_likeness_prompt": {
        "what": "pairwise student-likeness judge prompt and the two MathEDU examples (Eedi run's approved text, reused)",
        "files": ["../rl/prompts/student_likeness_system.txt", "../rl/prompts/student_likeness_user.txt",
                  "../rl/data/mathedu_student_examples.json"]},
    "verifier_backbones": {
        "what": "verifier backbones: A (reward) and B (test) (plan 6.2 draft)",
        "values": {"A": ("configs/verifier_half_a.yaml", "model.name"), "B": ("configs/verifier_half_b.yaml", "model.name")}},
}


def fingerprint(item: str) -> dict[str, Any]:
    spec = ITEMS[item]
    out: dict[str, Any] = {}
    if "files" in spec:
        out["files"] = {f: (sha256_file(resolve(f)) if resolve(f).exists() else None) for f in spec["files"]}
    if "values" in spec:
        out["values"] = {k: get_path(load_config(cfg), key) for k, (cfg, key) in spec["values"].items()}
    return out


def load_approvals(path: str | Path = APPROVALS_FILE) -> dict[str, Any]:
    import yaml

    p = resolve(path)
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}


def status(item: str, approvals: Mapping[str, Any] | None = None) -> tuple[str, str]:
    """('approved' | 'pending' | 'changed', detail)."""
    approvals = load_approvals() if approvals is None else approvals
    rec = approvals.get(item) or {}
    if not rec.get("approved"):
        return "pending", ITEMS[item]["what"]
    now = fingerprint(item)
    then = {k: rec.get(k) for k in now}
    if hash_obj(now) != hash_obj(then):
        changed = [f for f, h in (now.get("files") or {}).items() if (then.get("files") or {}).get(f) != h]
        changed += [k for k, v in (now.get("values") or {}).items() if (then.get("values") or {}).get(k) != v]
        return "changed", f"changed since approval on {rec.get('approved_on')}: {changed}"
    return "approved", f"approved on {rec.get('approved_on')}"


def problems(items: Iterable[str], files_in_use: Mapping[str, Iterable[str | Path]] | None = None) -> list[str]:
    """Blocking problems for a real run. `files_in_use[item]` = the files the run actually reads for that item."""
    approvals = load_approvals()
    out = []
    for item in items:
        state, detail = status(item, approvals)
        if state != "approved":
            out.append(f"{item}: {state} ({detail}) -> python scripts/approve.py {item} after the user confirms it")
        used = (files_in_use or {}).get(item)
        if used is not None:
            expected = {rel(resolve(f)) for f in ITEMS[item]["files"]}
            actual = {rel(resolve(f)) for f in used}
            if actual != expected:
                out.append(f"{item}: the run reads {sorted(actual)}, the approval covers {sorted(expected)}")
    return out


def snapshot(items: Iterable[str] | None = None) -> dict[str, Any]:
    """Approval state of every item, for run metadata."""
    approvals = load_approvals()
    return {item: {"state": status(item, approvals)[0], **fingerprint(item)} for item in (items or ITEMS)}


def approve(item: str, note: str, path: str | Path = APPROVALS_FILE) -> dict[str, Any]:
    import yaml

    if item not in ITEMS:
        raise KeyError(f"unknown item {item!r}; one of {sorted(ITEMS)}")
    approvals = load_approvals(path)
    fp = fingerprint(item)
    missing = [f for f, h in (fp.get("files") or {}).items() if h is None]
    if missing:
        raise FileNotFoundError(f"cannot approve {item}: missing {missing}")
    approvals[item] = {"approved": True, "approved_on": now_iso(), "note": note, **fp}
    header = ("# Written by scripts/approve.py after the user confirmed each item (user rule 1).\n"
              "# Real runs check these hashes; editing an approved file re-opens its item.\n")
    resolve(path).write_text(header + yaml.safe_dump(approvals, allow_unicode=True, sort_keys=True), encoding="utf-8", newline="\n")
    return approvals[item]
