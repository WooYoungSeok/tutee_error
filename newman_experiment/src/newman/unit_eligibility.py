"""Which questions may carry the two unit-related error types (plan 5.5, 5.7).

The hand-annotated GSM8K allowlist (llm_tutee_tutor UNIT_CONV_RAW, vendored in
data/unit_conversion_allowlist_gsm8k.json) is keyed by 0-based parquet row = raw index + group correction.

  * GSM8K rows: True if listed, False otherwise (the list covers all of GSM8K train and test).
  * Other questions: True/False through an exact question-key link to exactly one GSM8K row; a question with
    no link is None ("no confirmed allowlist"), never guessed. A user-supplied list (extra_allowlists) can
    set True for unlinked questions; a disagreement with a GSM8K link gives None and is reported.
  * The unit-related types need True: `allowed(question) is True`.

`content_audit` checks the corrections against the pinned parquet content: for every group, the fraction of
listed questions that mention a unit of that group must peak at the configured correction. A different
GSM8K ordering (or a wrong correction) moves the peak and stops data preparation.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from .common import read_json, read_jsonl, rel, sha256_file

# unit vocabulary per annotated group (audit only; never used to decide eligibility)
GROUP_PATTERNS = {
    "시간단위": r"\b(seconds?|minutes?|hours?|days?|weeks?|months?|years?|decades?|century|centuries)\b",
    "길이단위": r"\b(inch(es)?|foot|feet|yards?|meters?|metres?|centimeters?|cm|miles?|km|kilometers?|mm)\b",
    "화폐단위": r"\b(cents?|dollars?|quarters?|dimes?|nickels?|penn(y|ies))\b|\$",
    "거리단위": r"\b(miles?|feet|foot|yards?|meters?|km|kilometers?|inch(es)?)\b",
    "무게/부피": r"\b(pounds?|ounces?|oz|gallons?|quarts?|pints?|lit(er|re)s?|ml|milliliters?|kg|kilograms?|grams?|tons?|cups?|lbs?)\b",
    "묶음단위": r"\b(dozens?|pairs?|score|gross|half-dozen|packs?|box(es)?|bundles?|sets?|cases?|crates?|cartons?)\b",
}
AUDIT_OFFSETS = range(-4, 3)
AUDIT_MIN_HIT_RATE = 0.75


class EligibilityError(RuntimeError):
    pass


def load_allowlist(path: str | Path) -> dict[str, Any]:
    data = read_json(path)
    data["_path"] = rel(path)
    data["_sha256"] = sha256_file(path)
    return data


def corrected_rows(allowlist: Mapping[str, Any], n_rows: Mapping[str, int]) -> dict[tuple[str, int], list[str]]:
    """(split, 0-based parquet row) -> annotated groups. Every corrected index must exist in the parquet."""
    out: dict[tuple[str, int], list[str]] = defaultdict(list)
    for split, groups in allowlist["groups"].items():
        for group, info in groups.items():
            for raw in info["indices"]:
                idx = raw + int(info["correction"])
                if not 0 <= idx < n_rows[split]:
                    raise EligibilityError(f"{split}/{group}: corrected index {idx} (raw {raw}) outside [0, {n_rows[split]})")
                out[(split, idx)].append(group)
    counts = {s: len({i for sp, i in out if sp == s}) for s in allowlist["groups"]}
    expected = allowlist.get("expected_unique_rows") or {}
    if expected and counts != {s: expected[s] for s in counts}:
        raise EligibilityError(f"unique allowlisted rows {counts} != expected {expected}")
    return dict(out)


def content_audit(allowlist: Mapping[str, Any], questions: Mapping[str, list[str]]) -> dict[str, Any]:
    """Unit-word hit rate of every annotated group at offsets around its correction (plan 5.7: content check)."""
    report: dict[str, Any] = {"offsets": list(AUDIT_OFFSETS), "min_hit_rate": AUDIT_MIN_HIT_RATE, "groups": {}, "problems": []}
    for split, groups in allowlist["groups"].items():
        qs = questions[split]
        for group, info in groups.items():
            pattern = re.compile(GROUP_PATTERNS[group], re.I)
            rates = {}
            for off in AUDIT_OFFSETS:
                idx = [raw + off for raw in info["indices"] if 0 <= raw + off < len(qs)]
                rates[off] = sum(1 for i in idx if pattern.search(qs[i])) / len(idx) if idx else 0.0
            best = max(rates, key=lambda o: (rates[o], -abs(o - int(info["correction"]))))
            corr = int(info["correction"])
            report["groups"][f"{split}/{group}"] = {"n": len(info["indices"]), "correction": corr, "best_offset": best,
                                                     "hit_rate_at_correction": rates[corr], "hit_rates": rates}
            if best != corr:
                report["problems"].append(f"{split}/{group}: unit words peak at offset {best:+d}, not the correction {corr:+d}")
            if rates[corr] < AUDIT_MIN_HIT_RATE:
                report["problems"].append(f"{split}/{group}: hit rate {rates[corr]:.2f} < {AUDIT_MIN_HIT_RATE} at the correction")
    return report


class Eligibility:
    """Eligibility of any question for the unit-related types, with its provenance."""

    def __init__(self, gsm8k_rows: Iterable[Mapping[str, Any]], allowlist: Mapping[str, Any], question_key,
                 extra_allowlists: Iterable[Mapping[str, Any]] = ()):
        self.question_key = question_key
        rows = list(gsm8k_rows)
        n_rows = defaultdict(int)
        for r in rows:
            n_rows[r["split"]] = max(n_rows[r["split"]], r["row"] + 1)
        self.allowed_rows = corrected_rows(allowlist, n_rows)
        self.allowlist_meta = {"path": allowlist.get("_path"), "sha256": allowlist.get("_sha256"), "source": allowlist.get("source")}
        self.by_key: dict[str, dict[str, Any]] = {}
        refs: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for r in rows:
            refs[question_key(r["question"])].append((r["split"], r["row"]))
        self.conflicts: list[dict[str, Any]] = []
        for key, rr in refs.items():
            values = {(s, i) in self.allowed_rows for s, i in rr}
            src = ";".join(f"gsm8k:{s}:{i}" for s, i in sorted(rr))
            if len(values) == 1:
                self.by_key[key] = {"value": values.pop(), "source": src}
            else:  # the same question twice with different annotations: never guessed
                self.by_key[key] = {"value": None, "source": f"ambiguous:{src}"}
                self.conflicts.append({"key": key, "refs": rr, "reason": "gsm8k rows disagree"})
        self.extra_meta = []
        for extra in extra_allowlists:
            path = Path(extra["path"])
            digest = sha256_file(path)
            if extra.get("sha256") and extra["sha256"] != digest:
                raise EligibilityError(f"{path}: sha256 {digest} != configured {extra['sha256']}")
            added = 0
            for rec in read_jsonl(path):
                key = question_key(rec["question"])
                cur = self.by_key.get(key)
                tag = f"extra:{path.name}"
                if cur is None:
                    self.by_key[key] = {"value": True, "source": tag}
                    added += 1
                elif cur["value"] is not True:
                    self.by_key[key] = {"value": None, "source": f"ambiguous:{cur['source']}|{tag}"}
                    self.conflicts.append({"key": key, "reason": f"{tag} lists a question the GSM8K annotation does not"})
            self.extra_meta.append({"path": rel(path), "sha256": digest, "added": added})

    def lookup(self, question: str) -> tuple[bool | None, str]:
        hit = self.by_key.get(self.question_key(question))
        return (None, "unlinked") if hit is None else (hit["value"], hit["source"])

    def allowed(self, question: str) -> bool:
        return self.lookup(question)[0] is True

    def gsm8k_value(self, split: str, row: int) -> bool:
        return (split, row) in self.allowed_rows

    def meta(self) -> dict[str, Any]:
        return {"allowlist": self.allowlist_meta, "extra_allowlists": self.extra_meta,
                "allowlisted_rows": {s: sum(1 for sp, _ in self.allowed_rows if sp == s) for s in ("train", "test")},
                "conflicts": len(self.conflicts)}
