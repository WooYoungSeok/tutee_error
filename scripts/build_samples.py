#!/usr/bin/env python3
"""Normalize the raw sources, inspect them, and fix the pilot sample manifest.

Outputs
-------
data/normalized/<dataset>.jsonl   every normalized record, eligible or not
data/manifest/sample_manifest.jsonl        the fixed sample (one line per case)
data/manifest/sample_manifest_meta.json    seed, allocation, provenance, shortfalls
reports/data_inspection.md                 human readable data inspection report
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from errdesc.adapters import MissingFieldMapping, NormalizedRecord, normalize_dataset  # noqa: E402
from errdesc.config import load_config  # noqa: E402
from errdesc.paths import (  # noqa: E402
    MANIFEST_DIR,
    NORMALIZED_DIR,
    REPORTS_DIR,
    SAMPLE_MANIFEST,
    SAMPLE_MANIFEST_META,
    ensure_dirs,
)
from errdesc.sampling import assign_splits, sample_dataset  # noqa: E402
from errdesc.sources import load_source_manifest  # noqa: E402
from errdesc.util import utc_now, write_json, write_jsonl  # noqa: E402


def diversity_key_for(dataset: str, config: dict):
    if dataset == "mathclean":
        return lambda r: f"{r.annotations.get('difficulty_file')}|{r.annotations.get('extent')}"
    if dataset == "mathedu":
        group_by = (config.get("mathedu", {}).get("field_map") or {}).get("group_by") or "student_id"
        return lambda r: str(r.annotations.get(group_by))
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None, help="path to the pilot config JSON")
    parser.add_argument("--seed", type=int, default=None, help="override the config seed")
    parser.add_argument(
        "--target", type=int, default=None, help="override the per-dataset sample target"
    )
    return parser.parse_args()


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join([" --- "] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    seed = args.seed if args.seed is not None else config["seed"]
    target = args.target if args.target is not None else config["per_dataset_target"]
    dev_n = config["dev_per_dataset"]
    ensure_dirs()

    source_manifest = load_source_manifest()
    normalized: dict[str, list[NormalizedRecord]] = {}
    adapter_errors: dict[str, str] = {}

    for dataset in config["datasets"]:
        entry = source_manifest.get("datasets", {}).get(dataset, {})
        revision = entry.get("revision", "")
        try:
            records = normalize_dataset(dataset, revision=revision, config=config.get(dataset, {}))
        except MissingFieldMapping as exc:
            adapter_errors[dataset] = str(exc)
            records = []
        normalized[dataset] = records
        write_jsonl(NORMALIZED_DIR / f"{dataset}.jsonl", (r.to_dict() for r in records))
        print(
            f"[{dataset}] normalized={len(records)} "
            f"eligible={sum(1 for r in records if r.eligible)}",
            flush=True,
        )
        if dataset in adapter_errors:
            print(f"[{dataset}] {adapter_errors[dataset]}", flush=True)

    # --- cross dataset duplicate questions -------------------------------
    groups_by_dataset = {
        ds: {r.question_group_id for r in recs if r.eligible} for ds, recs in normalized.items()
    }
    cross_overlaps = {}
    names = list(groups_by_dataset)
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            shared = groups_by_dataset[left] & groups_by_dataset[right]
            if shared:
                cross_overlaps[f"{left}|{right}"] = len(shared)

    # --- sampling ---------------------------------------------------------
    used_groups: set[str] = set()
    selected_all: list[NormalizedRecord] = []
    reports = {}
    for dataset in config["datasets"]:
        selected, report = sample_dataset(
            dataset=dataset,
            records=normalized[dataset],
            target=target,
            seed=seed,
            used_question_groups=used_groups,
            diversity_key=diversity_key_for(dataset, config),
        )
        assign_splits(dataset, selected, dev_n=dev_n, seed=seed)
        reports[dataset] = report
        selected_all.extend(selected)
        print(
            f"[{dataset}] selected={len(selected)}/{target} "
            f"dev={sum(1 for r in selected if r.split == 'dev')} "
            f"shortfall={report.shortfall}",
            flush=True,
        )

    manifest_rows = [r.to_dict() for r in selected_all]
    write_jsonl(SAMPLE_MANIFEST, manifest_rows)

    meta = {
        "created_at_utc": utc_now(),
        "seed": seed,
        "per_dataset_target": target,
        "dev_per_dataset": dev_n,
        "config_path": config["_config_path"],
        "prompt_file": config["prompt_file"],
        "total_selected": len(selected_all),
        "total_target": target * len(config["datasets"]),
        "datasets": {ds: reports[ds].to_dict() for ds in reports},
        "adapter_errors": adapter_errors,
        "cross_dataset_question_group_overlaps": cross_overlaps,
        "source_revisions": {
            ds: source_manifest.get("datasets", {}).get(ds, {}).get("revision", "")
            for ds in config["datasets"]
        },
        "split_counts": dict(Counter(f"{r.dataset}:{r.split}" for r in selected_all)),
    }
    write_json(SAMPLE_MANIFEST_META, meta)

    # --- inspection report -------------------------------------------------
    lines: list[str] = []
    lines.append("# Data inspection report")
    lines.append("")
    lines.append(f"Generated (UTC): {meta['created_at_utc']}  ")
    lines.append(f"Seed: {seed} · per-dataset target: {target} · dev per dataset: {dev_n}")
    lines.append("")
    lines.append("## 1. Sources and provenance")
    lines.append("")
    rows = []
    for dataset in config["datasets"]:
        entry = source_manifest.get("datasets", {}).get(dataset, {})
        files = entry.get("files", [])
        rows.append(
            [
                dataset,
                entry.get("status", "missing"),
                entry.get("repo") or entry.get("homepage", ""),
                entry.get("revision", "-")[:12] or "-",
                len(files),
                sum(f.get("bytes", 0) for f in files),
            ]
        )
    lines.append(md_table(["dataset", "status", "source", "revision", "files", "bytes"], rows))
    lines.append("")
    lines.append(
        "Per-file URLs, byte sizes and SHA-256 digests: `data/raw/source_manifest.json`."
    )
    lines.append("")
    lines.append("## 2. Normalized records, eligibility and exclusions")
    lines.append("")
    rows = []
    for dataset in config["datasets"]:
        recs = normalized[dataset]
        rows.append(
            [
                dataset,
                len(recs),
                sum(1 for r in recs if r.eligible),
                len({r.question_group_id for r in recs if r.eligible}),
                len({r.sample_id for r in recs if r.eligible}),
            ]
        )
    lines.append(
        md_table(
            ["dataset", "records read", "eligible", "unique question groups", "unique sample ids"],
            rows,
        )
    )
    lines.append("")
    for dataset in config["datasets"]:
        recs = normalized[dataset]
        reasons = Counter(r.exclusion_reason for r in recs if not r.eligible)
        if reasons:
            lines.append(f"**{dataset} exclusions**")
            lines.append("")
            lines.append(
                md_table(["reason", "count"], [[k, v] for k, v in sorted(reasons.items())])
            )
            lines.append("")
    if adapter_errors:
        lines.append("**Adapter errors**")
        lines.append("")
        for dataset, message in adapter_errors.items():
            lines.append(f"- `{dataset}`: {message}")
        lines.append("")
    lines.append("## 3. Original error label frequencies (eligible pool)")
    lines.append("")
    for dataset in config["datasets"]:
        report = reports[dataset]
        if not report.label_counts:
            lines.append(f"**{dataset}**: no eligible records.")
            lines.append("")
            continue
        lines.append(f"**{dataset}** (pool {report.pool_size})")
        lines.append("")
        lines.append(
            md_table(
                ["original label", "pool", "planned", "selected"],
                [
                    [
                        label,
                        count,
                        report.planned.get(label, 0),
                        report.selected.get(label, 0),
                    ]
                    for label, count in sorted(
                        report.label_counts.items(), key=lambda kv: (-kv[1], kv[0])
                    )
                ],
            )
        )
        lines.append("")
        if report.exhausted_strata:
            lines.append(f"- exhausted strata: {', '.join(report.exhausted_strata)}")
        if report.redistributed:
            lines.append(f"- redistributed slots: {report.redistributed}")
        if report.shortfall:
            lines.append(f"- **shortfall: {report.shortfall} case(s) below the target**")
        for note in report.notes:
            lines.append(f"- {note}")
        lines.append("")
    lines.append("## 4. Duplicates across datasets")
    lines.append("")
    if cross_overlaps:
        lines.append(
            md_table(
                ["dataset pair", "shared question groups"],
                [[k, v] for k, v in sorted(cross_overlaps.items())],
            )
        )
        lines.append("")
        lines.append(
            "Shared groups are sampled at most once: the dataset processed first "
            f"(config order: {', '.join(config['datasets'])}) keeps the case."
        )
    else:
        lines.append("No question group is shared between the eligible pools.")
    lines.append("")
    lines.append("## 5. Fixed sample")
    lines.append("")
    rows = []
    for dataset in config["datasets"]:
        subset = [r for r in selected_all if r.dataset == dataset]
        rows.append(
            [
                dataset,
                len(subset),
                sum(1 for r in subset if r.split == "dev"),
                sum(1 for r in subset if r.split == "holdout"),
                len({r.question_group_id for r in subset}),
            ]
        )
    rows.append(
        [
            "total",
            len(selected_all),
            sum(1 for r in selected_all if r.split == "dev"),
            sum(1 for r in selected_all if r.split == "holdout"),
            len({r.question_group_id for r in selected_all}),
        ]
    )
    lines.append(md_table(["dataset", "selected", "dev", "holdout", "question groups"], rows))
    lines.append("")
    lines.append("### Metadata distribution of the sample")
    lines.append("")
    for dataset in config["datasets"]:
        subset = [r for r in selected_all if r.dataset == dataset]
        if not subset:
            continue
        facets: dict[str, Counter] = defaultdict(Counter)
        facet_keys = {
            "extent", "difficulty_file", "type_dir", "source_benchmark", "subset",
            "student_id", "mathedu_split_file", "mathqa_category",
        }
        for record in subset:
            for key, value in record.annotations.items():
                if key in facet_keys and (isinstance(value, (str, bool, int)) or value is None):
                    facets[key][str(value)] += 1
            if dataset == "stepwise":
                has_desc = bool(str(record.annotations.get("error_description") or "").strip())
                facets["error_description present"][str(has_desc)] += 1
        if facets:
            lines.append(f"**{dataset}**")
            lines.append("")
            for key, counter in sorted(facets.items()):
                pretty = ", ".join(f"{k}: {v}" for k, v in sorted(counter.items()))
                lines.append(f"- {key} — {pretty}")
            lines.append("")
    lines.append("## 6. Notes")
    lines.append("")
    lines.append(
        "- Sample ids are `dataset:sha256(question, solution, label)[:16]`; "
        "`source_id` points at the original file and record index."
    )
    lines.append(
        "- The sample manifest is fixed: it must not be rebuilt when the prompt changes."
    )
    lines.append(
        "- MathEDU is real student work; Stepwise, MathClean and EIC contain "
        "model-generated solutions."
    )
    (REPORTS_DIR / "data_inspection.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"sample manifest -> {SAMPLE_MANIFEST} ({len(manifest_rows)} rows)")
    print(f"manifest meta   -> {SAMPLE_MANIFEST_META}")
    print(f"inspection report -> {REPORTS_DIR / 'data_inspection.md'}")
    print(f"normalized records -> {NORMALIZED_DIR}")
    if MANIFEST_DIR.exists():
        shortfalls = {ds: reports[ds].shortfall for ds in reports if reports[ds].shortfall}
        if shortfalls:
            print(f"WARNING: shortfalls remain: {shortfalls}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
