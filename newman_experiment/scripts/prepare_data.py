#!/usr/bin/env python3
"""Relabel the SFT pool with the Newman taxonomy, fix the global question split, the SFT pairs and the RL conditions.

  --stage audit   compute everything, write only the audit report (sizes, including the RL options; no decision)
  --stage sft     workbook check -> SFT cases (v2 filters) -> Newman types -> unit eligibility -> global groups ->
                  train:test 80:20 -> halves A/B -> one positive + one negative per anchor -> tokenizer length check
                  -> data/prepared/sft/{half_a,half_b,test}.jsonl + meta.json, manifests/, reports/data_audit.md
  --stage rl      GSM8K conditions (Q, reference answer, N, E) for RL train/test; needs every rl_data decision in
                  configs/data.yaml and the split manifest written by --stage sft (recomputed and compared)
                  -> data/prepared/rl/{train,test,privileged}.jsonl + meta.json

Without the mapping workbook at the configured path, --allow-unverified-mapping takes the stages from the taxonomy
file and writes everything under output.unverified_root (git-ignored), marked mapping_verified=false: audits and
smoke tests only, real training refuses that data.

Usage (from newman_experiment/, after `source env.sh`):
  python scripts/prepare_data.py --stage sft
  python scripts/prepare_data.py --stage rl
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman.common import (  # noqa: E402
    ConfigError,
    find_required,
    git_state,
    load_config,
    now_iso,
    read_json,
    read_jsonl,
    read_template,
    rel,
    resolve,
    sha256_file,
    write_json,
    write_jsonl,
)
from newman.negatives import REGIONS, audit as negative_audit, make_pairs  # noqa: E402
from newman.rl_conditions import assign as assign_conditions, scenario_sizes, select_questions  # noqa: E402
from newman.sources import exclusion_table, load_gsm8k, load_sft_cases  # noqa: E402
from newman.splits import TEST, TRAIN, assign_halves, assign_split, assign_validation, build_groups, region  # noqa: E402
from newman.taxonomy import Taxonomy, find_file, unverified_mapping_report, verify_workbook  # noqa: E402
from newman.unit_eligibility import Eligibility, content_audit, load_allowlist  # noqa: E402
from newman.verifier_format import (  # noqa: E402
    load_verifier_prompt,
    pair_token_count,
    question_group_id,
    question_key,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default="configs/data.yaml")
    p.add_argument("--override", action="append", default=[], help="a.b.c=value (YAML value), repeatable; with a verified "
                   "workbook only through the config file (the decision is recorded there)")
    p.add_argument("--stage", required=True, choices=["audit", "sft", "rl"])
    p.add_argument("--allow-unverified-mapping", action="store_true", help="no workbook: audit/smoke outputs only")
    p.add_argument("--skip-length-check", action="store_true", help="do not load the backbone tokenizers")
    p.add_argument("--no-fetch", action="store_true", help="do not download GSM8K (must already be in inputs.gsm8k_dir)")
    return p.parse_args()


# --- 1. taxonomy and workbook --------------------------------------------------------


def mapping(cfg, taxonomy: Taxonomy, allow_unverified: bool) -> dict[str, Any]:
    configured = resolve(taxonomy.mapping_source["workbook"])
    workbook = find_file(configured)
    if workbook is not None:
        report = verify_workbook(workbook, taxonomy)
        if report["problems"]:
            raise SystemExit("mapping workbook disagrees with configs/taxonomy.yaml:\n  - " + "\n  - ".join(report["problems"]))
        return report
    if not allow_unverified:
        raise SystemExit(f"mapping workbook not found: {configured}\n  upload it there (sha256 {taxonomy.mapping_source['sha256']}), "
                         "or pass --allow-unverified-mapping for an audit/smoke run")
    return unverified_mapping_report(taxonomy, f"workbook not found at {rel(configured)}")


# --- 2. cases, eligibility, groups, split, halves ------------------------------------------


def forced_groups(cfg) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    forced_train: dict[str, list[str]] = defaultdict(list)
    forced_a: dict[str, list[str]] = defaultdict(list)
    ft = cfg["split"]["force_train"]
    if ft.get("prompt_dev_groups"):
        for r in read_jsonl(resolve(cfg["inputs"]["prompt_dev_manifest"])):
            if r.get("split") == "dev":
                forced_train[question_group_id(r["question"])].append("prompt_dev")
    if ft.get("judge_example_groups_half_a"):
        for ex in read_json(resolve(cfg["inputs"]["judge_examples"]))["examples"]:
            gid = question_group_id(ex["question"])
            forced_train[gid].append(f"judge_example:mathedu_{ex['mathedu_id']}")
            forced_a[gid].append(f"judge_example:mathedu_{ex['mathedu_id']}")
    return dict(forced_train), dict(forced_a)


def build(cfg, taxonomy: Taxonomy, fetch: bool) -> dict[str, Any]:
    cases, case_stats = load_sft_cases(cfg, taxonomy)
    gsm8k = load_gsm8k(cfg, fetch=fetch)
    allowlist = load_allowlist(resolve(cfg["inputs"]["unit_allowlist"]))
    by_split = {s: [r["question"] for r in sorted((x for x in gsm8k if x["split"] == s), key=lambda x: x["row"])]
                for s in ("train", "test")}
    audit_units = content_audit(allowlist, by_split)
    if audit_units["problems"]:
        raise SystemExit("unit allowlist does not fit the GSM8K parquet content:\n  - " + "\n  - ".join(audit_units["problems"]))
    extra = [{"path": resolve(e["path"]), "sha256": e.get("sha256")} for e in cfg["unit_eligibility"]["extra_allowlists"]]
    elig = Eligibility(gsm8k, allowlist, question_key, extra)

    eligible = [c for c in cases if not c["exclusion_reason"]]
    for c in eligible:
        c["unit_conversion_eligible"], c["unit_eligibility_source"] = elig.lookup(c["question"])
    groups = build_groups(eligible, gsm8k, question_group_id, elig.gsm8k_value)
    forced_train, forced_a = forced_groups(cfg)
    split_info = assign_split(groups, float(cfg["split"]["test_ratio"]), int(cfg["seed"]), forced_train)
    half_info = assign_halves(groups, int(cfg["seed"]), forced_a)
    for c in eligible:
        g = groups[c["question_group_id"]]
        c["split"], c["half"] = g.split, g.half
        c["region"] = region(g.split, g.half)
    return {"cases": cases, "eligible": eligible, "case_stats": case_stats, "gsm8k": gsm8k, "eligibility": elig,
            "unit_audit": audit_units, "groups": groups, "split_info": split_info, "half_info": half_info,
            "forced_train": forced_train, "forced_a": forced_a}


# --- 3. length -------------------------------------------------------------------------------


def length_check(cfg, taxonomy: Taxonomy, pairs: list[dict[str, Any]], manifest: list[dict[str, Any]]) -> dict[str, Any]:
    """Token counts with each backbone's tokenizer on the pairs it trains or is tested on; an anchor over the limit
    in any relevant backbone is dropped as a whole (test anchors: over in either backbone)."""
    from transformers import AutoTokenizer

    max_len = int(cfg["length"]["max_seq_length"])
    info: dict[str, Any] = {"max_seq_length": max_len, "backbones": {}}
    too_long: set[str] = set()
    for vpath in cfg["length"]["verifier_configs"]:
        vcfg = load_config(vpath)
        tok = AutoTokenizer.from_pretrained(vcfg["model"]["name"], trust_remote_code=True)
        prompt = load_verifier_prompt(vcfg["prompts"]["system"], vcfg["prompts"]["user"])
        regions = {f"half_{vcfg['half'].lower()}", "test"}
        lens = []
        for p in pairs:
            if p["region"] not in regions:
                continue
            n = pair_token_count(tok, prompt, taxonomy, p)
            p.setdefault("n_tokens", {})[vcfg["half"]] = n
            lens.append(n)
            if n > max_len:
                too_long.add(p["anchor_sample_id"])
        lens.sort()
        info["backbones"][vcfg["half"]] = {
            "model": vcfg["model"]["name"], "regions": sorted(regions), "pairs": len(lens),
            "min": lens[0] if lens else None, "median": lens[len(lens) // 2] if lens else None,
            "p99": lens[int(0.99 * (len(lens) - 1))] if lens else None, "max": lens[-1] if lens else None}
    for m in manifest:
        if m["anchor_sample_id"] in too_long:
            m.update(status="excluded", reason=f"exceeds_max_seq_length:{max_len}")
    info["dropped_anchors"] = sorted(too_long)
    kept = [p for p in pairs if p["anchor_sample_id"] not in too_long]
    pairs[:] = kept
    return info


# --- 4. checks ---------------------------------------------------------------------------------


def run_checks(built: dict[str, Any], pairs: list[dict[str, Any]], manifest: list[dict[str, Any]], taxonomy: Taxonomy,
               max_len: int | None, cross: bool = False) -> list[tuple[str, bool, str]]:
    groups = built["groups"]
    eligible = {c["sample_id"]: c for c in built["eligible"]}
    checks = []
    checks.append(("every question group has one split", all(g.split in (TRAIN, TEST) for g in groups.values()), ""))
    no_half = [g.group_id for g in groups.values() if g.split == TRAIN and g.sft_ids and g.half not in ("A", "B")]
    checks.append(("every SFT train group has one half", not no_half, f"{len(no_half)} without"))
    region_of_group: dict[str, set[str]] = defaultdict(set)
    for p in pairs:
        region_of_group[p["question_group_id"]].add(p["region"])
    shared = [g for g, rs in region_of_group.items() if len(rs) > 1]
    checks.append(("half A / half B / test share no question group", not shared, f"{len(shared)} groups"))
    negs = [p for p in pairs if p["target"] == "not_aligned"]
    poss = [p for p in pairs if p["target"] == "aligned"]
    checks.append(("positive target type = the anchor's own type", all(p["target_error_id"] == p["anchor_error_id"] for p in poss), ""))
    checks.append(("negative type differs from the anchor type", all(p["target_error_id"] != p["anchor_error_id"] for p in negs), ""))
    checks.append(("every pair's stage = mapping(its type)",
                   all(p["target_newman_stage"] == taxonomy.stage_of(p["target_error_id"]) for p in pairs), ""))
    checks.append(("unit-related negatives only on allowlisted questions",
                   all(p["unit_conversion_eligible"] is True for p in negs if taxonomy.types[p["target_error_id"]].unit_related), ""))
    checks.append(("no excluded type in any pair",
                   all(p["target_error_id"] in taxonomy.types and p["anchor_error_id"] in taxonomy.types for p in pairs), ""))
    per_anchor = Counter((p["anchor_sample_id"], p["target"]) for p in pairs)
    anchors = {p["anchor_sample_id"] for p in pairs}
    n_neg = 2 if cross else 1
    checks.append((f"every kept anchor has one positive and {n_neg} negative(s)",
                   all(per_anchor[(a, "aligned")] == 1 and per_anchor[(a, "not_aligned")] == n_neg for a in anchors), ""))
    first = [p for p in negs if p["pair_id"].endswith("::neg")]
    checks.append(("the first negative comes from the anchor's own dataset",
                   all(p["negative_dataset_relation"] == "same_dataset" for p in first), ""))
    if cross:
        second = [p for p in negs if p["pair_id"].endswith("::neg_cross")]
        checks.append(("the second negative is another dataset and another Newman stage",
                       len(second) == len(anchors) and all(p["negative_dataset_relation"] == "other_dataset"
                                                           and p["negative_kind"] == "different_stage" for p in second), ""))
    checks.append(("Q and S of a negative are the anchor's own",
                   all(p["question"] == eligible[p["anchor_sample_id"]]["question"]
                       and p["solution"] == eligible[p["anchor_sample_id"]]["solution"] for p in pairs), ""))
    forced_in_test = [gid for gid in built["forced_train"] if gid in groups and groups[gid].split == TEST]
    checks.append(("forced-train groups (prompt dev, judge examples) not in test", not forced_in_test, f"{len(forced_in_test)}"))
    judge_not_a = [gid for gid in built["forced_a"] if gid in groups and groups[gid].sft_ids and groups[gid].half != "A"]
    checks.append(("judge-example groups in half A", not judge_not_a, f"{len(judge_not_a)}"))
    if max_len is not None:
        over = [p for p in pairs if max((p.get("n_tokens") or {0: 0}).values()) > max_len]
        checks.append((f"no pair over {max_len} tokens", not over, f"{len(over)}"))
    return checks


# --- 5. report ----------------------------------------------------------------------------------


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(map(str, headers)) + " |", "|" + "|".join([" --- "] * len(headers)) + "|"]
    out += ["| " + " | ".join("" if c is None else str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def write_report(path: Path, cfg, taxonomy: Taxonomy, mapping_report, built, pairs, manifest, neg_audit, length_info,
                 checks, rl_scenarios, meta) -> None:
    L: list[str] = [f"# Newman data audit ({meta['stage']})", ""]
    L += [f"Created {meta['created_at']} (Asia/Seoul) · seed {cfg['seed']} · git `{(meta['git'].get('commit') or '')[:12]}` · "
          f"mapping verified: **{mapping_report['verified']}**", ""]
    if not mapping_report["verified"]:
        L += [f"> UNVERIFIED MAPPING ({mapping_report.get('reason')}): stages taken from configs/taxonomy.yaml. "
              "Audit/smoke only; real training refuses this data.", ""]
    L += ["Targets of the SFT pairs are automatic (own type = aligned, another type of the same source dataset = "
          "not_aligned); negatives are not semantically reviewed (plan 5.4).", ""]

    L += ["## 1. Inputs", ""]
    rows = [[k, v["path"], f"`{v['sha256'][:16]}`"] for k, v in meta["inputs"].items()]
    L += [md_table(["input", "path", "sha256"], rows), ""]

    L += ["## 2. Newman mapping (workbook column D)", ""]
    rows = []
    for tid in sorted([*taxonomy.types, *taxonomy.excluded]):
        t = mapping_report["types"].get(tid, {})
        item = taxonomy.types.get(tid) or taxonomy.excluded[tid]
        definition = "(none)" if tid in taxonomy.types and taxonomy.types[tid].definition is None else ("yes" if tid in taxonomy.types else "-")
        rows.append([item.dataset, item.name, tid, t.get("row"), t.get("mapping_cell_raw"), t.get("decision"), definition])
    L += [md_table(["dataset", "name (column A)", "type id", "row", "column D", "applied", "definition (column B)"], rows), ""]

    L += ["## 3. Case selection (pool records)", ""]
    table = exclusion_table(built["cases"])
    reasons = sorted({r for v in table.values() for r in v})
    L += [md_table(["dataset", *reasons], [[ds, *[v.get(r, "") for r in reasons]] for ds, v in table.items()]), ""]
    ml = built["case_stats"]["multi_label_solutions_excluded"]
    if ml:
        L += [f"Student solutions with more than one error label (pool or raw normalized records; user instruction "
              f"2026-09-30) are excluded: solutions {ml['solutions']}, of which found only through raw labels outside the "
              f"pool {ml['solutions_found_only_with_raw_labels']}; their records {ml['cases']}.", ""]
    by_type = Counter(c["error_id"] for c in built["eligible"])
    rows = [[t.dataset, t.id, t.newman_stage, by_type[t.id]] for t in sorted(taxonomy.types.values(), key=lambda t: t.id)]
    L += ["Eligible cases per adopted type (a count of solutions, not of the 16 types):", ""]
    L += [md_table(["dataset", "type", "stage", "cases"], rows), ""]

    L += ["## 4. Unit-conversion eligibility (plan 5.5, 5.7)", ""]
    em = built["eligibility"].meta()
    L += [f"GSM8K allowlist `{em['allowlist']['path']}` (sha256 `{em['allowlist']['sha256'][:16]}`): unique rows "
          f"{em['allowlisted_rows']}; extra lists {em['extra_allowlists'] or 'none'}; conflicts {em['conflicts']}.", ""]
    rows = [[k, v["n"], f"{v['correction']:+d}", f"{v['best_offset']:+d}", f"{v['hit_rate_at_correction']:.2f}",
             " ".join(f"{o:+d}:{r:.2f}" for o, r in v["hit_rates"].items())] for k, v in built["unit_audit"]["groups"].items()]
    L += ["Content check against the pinned parquet (unit words of each group, by index offset):", ""]
    L += [md_table(["split/group", "n", "correction", "peak", "hit rate", "by offset"], rows), ""]
    link = Counter((c["dataset"], c["benchmark"] or "-", str(c["unit_conversion_eligible"])) for c in built["eligible"])
    rows = [[ds, b, link[(ds, b, "True")], link[(ds, b, "False")], link[(ds, b, "None")]]
            for ds, b in sorted({(k[0], k[1]) for k in link})]
    L += ["SFT cases by eligibility (None = no confirmed allowlist: the unit-related types are never their negatives):", ""]
    L += [md_table(["dataset", "benchmark", "True", "False", "None"], rows), ""]

    L += ["## 5. Global question groups and split (train:test = 80:20, halves 50:50)", ""]
    groups = built["groups"]
    kinds = Counter(("sft" if g.sft_ids else "gsm8k_only", g.split, g.half or "-") for g in groups.values())
    L += [md_table(["groups", "split", "half", "count"], [[k[0], k[1], k[2], v] for k, v in sorted(kinds.items())]), ""]
    reg = Counter((c["dataset"], c["benchmark"] or "-", c["region"]) for c in built["eligible"])
    rows = [[ds, b, *[reg[(ds, b, r)] for r in REGIONS]] for ds, b in sorted({(k[0], k[1]) for k in reg})]
    L += ["SFT cases per region:", "", md_table(["dataset", "benchmark", *REGIONS], rows), ""]
    gs = Counter((s, g.split) for g in groups.values() for s, _ in g.gsm8k)
    L += [f"GSM8K rows by original split and global split: {dict(sorted(gs.items()))}.", ""]
    L += [f"Forced into train: {len(built['split_info']['forced_train'])} groups; into half A: {len(built['half_info']['forced_a'])}.", ""]

    L += ["## 6. SFT pairs and negatives (plan 5.4)", ""]
    L += [f"Negative type: uniform over the candidate scope `{cfg['negatives']['candidates']}` except the anchor's own type; "
          "unit-related types only on allowlisted questions, where they have priority unless the anchor's own type is "
          "unit-related.", ""]
    if cfg["negatives"].get("cross_dataset_different_stage"):
        L += ["Second negative per anchor (`::neg_cross`): uniform over the types of another source dataset at another "
              "Newman stage, with the same unit rules and priority; separate RNG, so the first negatives equal the "
              "one-negative version.", ""]
    draws = Counter((m["region"], m.get("draw")) for m in manifest if m["status"] == "paired")
    L += [f"Draws with unit priority: " + ", ".join(f"{r} {draws[(r, 'unit_priority')]}" for r in REGIONS) + ".", ""]
    cdraws = Counter((m["region"], m.get("cross_draw")) for m in manifest if m["status"] == "paired" and m.get("cross_draw"))
    if cdraws:
        L += [f"Second-negative draws with unit priority: " + ", ".join(f"{r} {cdraws[(r, 'unit_priority')]}" for r in REGIONS) + ".", ""]
    rows = [[r, a["anchors"], a["paired"], a["no_negative_candidate"], a["negative_kind"].get("same_stage", 0),
             a["negative_kind"].get("different_stage", 0), a["negative_dataset_relation"].get("same_dataset", 0),
             a["negative_dataset_relation"].get("other_dataset", 0), sum(1 for p in pairs if p["region"] == r)]
            for r, a in neg_audit.items()]
    L += [md_table(["region", "anchors", "paired", "no candidate", "same-stage neg", "different-stage neg",
                    "same-dataset neg", "other-dataset neg", "pair rows"], rows), ""]
    rows = []
    for tid in taxonomy.adopted_ids():
        row = [tid]
        for r in REGIONS:
            v = neg_audit[r]["types"][tid]
            row.append(f"{v['positives']} / {v['negatives_as_target']}" + (f" (unit removed {v['unit_candidate_removed']})"
                                                                          if v["unit_candidate_removed"] else ""))
        rows.append(row)
    L += ["Positives / negatives carrying the type, per region:", "", md_table(["type", *REGIONS], rows), ""]
    flagged = {r: a["types_without_negatives"] for r, a in neg_audit.items() if a["types_without_negatives"]}
    if flagged:
        L += ["**Types with positives but no negative** (the label name alone predicts `aligned` there, plan 5.4): "
              + "; ".join(f"{r}: {', '.join(v)}" for r, v in flagged.items()), ""]

    L += ["## 7. Length", ""]
    if length_info:
        rows = [[h, v["model"], ", ".join(v["regions"]), v["pairs"], v["min"], v["median"], v["p99"], v["max"]]
                for h, v in length_info["backbones"].items()]
        L += [md_table(["half", "tokenizer", "regions", "pairs", "min", "median", "p99", "max"], rows), ""]
        L += [f"Anchors dropped for length (> {length_info['max_seq_length']}): {len(length_info['dropped_anchors'])}.", ""]
    else:
        L += ["Skipped (--skip-length-check). train_verifier.py still refuses over-length pairs.", ""]

    L += ["## 8. RL scenario sizes (reference; the decisions are in configs/data.yaml rl_data and data/prepared/rl/meta.json)", ""]
    if rl_scenarios:
        for label, sc in rl_scenarios.items():
            keys = list(sc[0])
            L += [f"GSM8K source splits {label} (6 conditions per optimizer step at 48 completions):", "",
                  md_table(keys, [[row[k] for k in keys] for row in sc]), ""]

    L += ["## 9. Checks", ""]
    L += [md_table(["check", "result", "detail"], [[n, "pass" if ok else "**FAIL**", d] for n, ok, d in checks]), ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


# --- 6. RL questions ------------------------------------------------------------------------------


def rl_questions(built: dict[str, Any], source_splits: list[str]) -> dict[str, list[dict[str, Any]]]:
    groups, elig = built["groups"], built["eligibility"]
    out: dict[str, list[dict[str, Any]]] = {TRAIN: [], TEST: []}
    for r in built["gsm8k"]:
        if r["split"] not in source_splits:
            continue
        gid = question_group_id(r["question"])
        g = groups[gid]
        out[g.split].append({"gsm8k_split": r["split"], "gsm8k_row": r["row"], "question": r["question"],
                             "reference_answer": r["reference_answer"], "question_group_id": gid, "split": g.split,
                             "unit_conversion_eligible": elig.gsm8k_value(r["split"], r["row"]),
                             "group_has_sft_cases": bool(g.sft_ids), "group_sft_half": g.half})
    return out


# --- main --------------------------------------------------------------------------------------------


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config, args.override)
    taxonomy = Taxonomy.load(resolve(cfg["inputs"]["taxonomy"]))
    mapping_report = mapping(cfg, taxonomy, args.allow_unverified_mapping)
    verified = bool(mapping_report["verified"])
    if args.override and verified:
        raise SystemExit("--override is for audit/smoke runs; write decisions into configs/data.yaml (a committed record)")
    root = resolve(cfg["output"]["unverified_root"]) if not verified else None
    prepared_dir = (root / "prepared") if root else resolve(cfg["output"]["prepared_dir"])
    manifest_dir = (root / "manifests") if root else resolve(cfg["output"]["manifest_dir"])
    report_path = (root / "data_audit.md") if root else resolve(cfg["output"]["report"])
    if args.stage == "audit":
        report_path = report_path.with_name(report_path.stem + "_preview.md")

    built = build(cfg, taxonomy, fetch=not args.no_fetch)
    cross = bool(cfg["negatives"].get("cross_dataset_different_stage", False))
    if int(cfg["negatives"]["per_anchor"]) != (2 if cross else 1):
        raise SystemExit("negatives.per_anchor must be 2 with cross_dataset_different_stage, else 1")
    pairs, manifest = make_pairs(built["eligible"], taxonomy, int(cfg["seed"]), bool(cfg["negatives"].get("unit_priority", False)),
                                 cfg["negatives"]["candidates"], cross)
    length_info = None if args.skip_length_check else length_check(cfg, taxonomy, pairs, manifest)
    neg_audit = negative_audit(pairs, manifest, taxonomy)
    checks = run_checks(built, pairs, manifest, taxonomy, None if length_info is None else length_info["max_seq_length"], cross)
    prompts_per_step = 6
    rl_scen = {str(s): scenario_sizes(rl_questions(built, s), taxonomy, prompts_per_step) for s in (["train"], ["train", "test"])}

    inputs = {**built["case_stats"]["inputs"],
              **{f"gsm8k_{s}": {"path": rel(resolve(cfg['inputs']['gsm8k_dir']) / f"{s}.parquet"),
                                "sha256": cfg["gsm8k"]["files"][s]["sha256"]} for s in ("train", "test")},
              "unit_allowlist": {"path": rel(resolve(cfg["inputs"]["unit_allowlist"])), "sha256": sha256_file(resolve(cfg["inputs"]["unit_allowlist"]))},
              "taxonomy": {"path": rel(taxonomy.path), "sha256": taxonomy.sha256}}
    if mapping_report.get("sha256"):
        inputs["mapping_workbook"] = {"path": taxonomy.mapping_source["workbook"], "sha256": mapping_report["sha256"]}
    meta: dict[str, Any] = {
        "created_at": now_iso(), "timezone": "Asia/Seoul", "stage": args.stage, "seed": cfg["seed"],
        "config": {"chain": cfg["_config_chain"], "sha256": cfg["_config_sha256"]}, "git": git_state(),
        "mapping_verified": verified, "mapping_version": taxonomy.version, "taxonomy_sha256": taxonomy.sha256,
        "inputs": inputs,
    }
    ok = all(c for _, c, _ in checks)

    if args.stage in ("audit", "sft"):
        write_report(report_path, cfg, taxonomy, mapping_report, built, pairs, manifest, neg_audit, length_info, checks, rl_scen, meta)
        print(f"report -> {report_path}")
    if args.stage == "audit":
        for name, passed, detail in checks:
            print(f"  [{'ok' if passed else 'FAIL'}] {name} {'' if passed else detail}")
        return 0 if ok else 1

    if args.stage == "sft":
        if not ok:
            for name, passed, detail in checks:
                print(f"  [{'ok' if passed else 'FAIL'}] {name} {'' if passed else detail}")
            print("checks failed: nothing written except the report", file=sys.stderr)
            return 1
        out = prepared_dir / "sft"
        counts = {}
        for r in REGIONS:
            rows = [p for p in pairs if p["region"] == r]
            write_jsonl(out / f"{r}.jsonl", rows)
            counts[r] = {"pair_rows": len(rows), "anchors": len({p["anchor_sample_id"] for p in rows}),
                         "question_groups": len({p["question_group_id"] for p in rows}),
                         "sha256": sha256_file(out / f"{r}.jsonl")}
        write_json(out / "meta.json", {**meta, "regions": counts, "length": length_info, "negative_audit": neg_audit,
                                       "unit_eligibility": built["eligibility"].meta(),
                                       "split": {"test_ratio": cfg["split"]["test_ratio"], "per_stratum": built["split_info"]["per_stratum"],
                                                 "halves": built["half_info"]["per_stratum"]},
                                       "checks_passed": ok})
        write_json(manifest_dir / "taxonomy_mapping.json", {**mapping_report, "taxonomy_sha256": taxonomy.sha256,
                                                             "mapping_version": taxonomy.version})
        mf = ("sample_id", "dataset", "benchmark", "source_error_label", "error_id", "newman_stage", "question_group_id",
              "exclusion_reason", "unit_conversion_eligible", "unit_eligibility_source", "split", "half", "region", "source_ids")
        write_jsonl(manifest_dir / "case_manifest.jsonl",
                    [{**{k: c.get(k) for k in mf},
                      "mapping_cell_raw": (mapping_report["types"].get(c["error_id"]) or {}).get("mapping_cell_raw") if c.get("error_id") else None}
                     for c in built["cases"]])
        write_jsonl(manifest_dir / "question_groups.jsonl", [g.record() for _, g in sorted(built["groups"].items())])
        write_jsonl(manifest_dir / "sft_pair_manifest.jsonl", manifest)
        write_jsonl(manifest_dir / "unit_eligibility_gsm8k.jsonl",
                    [{"gsm8k_split": r["split"], "gsm8k_row": r["row"], "eligible": built["eligibility"].gsm8k_value(r["split"], r["row"]),
                      "groups": built["eligibility"].allowed_rows.get((r["split"], r["row"]), []),
                      "question_group_id": question_group_id(r["question"])} for r in built["gsm8k"]])
        for r, c in counts.items():
            print(f"  {r:7s} anchors {c['anchors']:5d}  pair rows {c['pair_rows']:5d}  groups {c['question_groups']:5d}")
        print(f"wrote {out} and {manifest_dir}")
        return 0

    # --- rl ---
    rd = cfg["rl_data"]
    missing = find_required(rd)
    if missing:
        raise SystemExit("rl_data decisions are still REQUIRED in configs/data.yaml: " + ", ".join(f"rl_data.{k}" for k in missing))
    saved = manifest_dir / "question_groups.jsonl"
    if not saved.exists():
        raise SystemExit(f"{saved} not found: run --stage sft first (the RL split must be the SFT split)")
    now = {g.group_id: g.record() for g in built["groups"].values()}
    before = {r["question_group_id"]: r for r in read_jsonl(saved)}
    drift = [gid for gid in set(now) | set(before) if (now.get(gid) or {}).get("split") != (before.get(gid) or {}).get("split")
             or (now.get(gid) or {}).get("half") != (before.get(gid) or {}).get("half")]
    if drift:
        raise SystemExit(f"{len(drift)} question groups differ from {saved} (inputs changed?): e.g. {drift[:3]}")
    source_splits = list(rd["gsm8k_source_splits"])
    qs = rl_questions(built, source_splits)
    contract_path = resolve(rd["answer_contract"])
    contract = read_template(contract_path)
    val_groups, val_info = assign_validation(qs[TRAIN], built["groups"], float(rd["validation_ratio"]), int(cfg["seed"]))
    qs = {TRAIN: [q for q in qs[TRAIN] if q["question_group_id"] not in val_groups],
          "validation": [{**q, "split": "validation"} for q in qs[TRAIN] if q["question_group_id"] in val_groups],
          TEST: qs[TEST]}
    limits = {TRAIN: rd["max_train_questions"], "validation": rd["max_validation_questions"], TEST: rd["max_test_questions"]}
    rows_by_split, priv = {}, []
    for split in (TRAIN, "validation", TEST):
        limit = limits[split]
        picked = select_questions(qs[split], limit, int(cfg["seed"]), split)
        conds = assign_conditions(picked, taxonomy, rd["conditions_per_question"], rd["type_assignment"], int(cfg["seed"]), split)
        rows_by_split[split] = conds
        ref = {(q["gsm8k_split"], q["gsm8k_row"]): q["reference_answer"] for q in picked}
        priv += [{"condition_id": c["condition_id"], "reference_answer": ref[(c["gsm8k_split"], c["gsm8k_row"])],
                  "answer_contract": contract} for c in conds]
    bad_unit = [c["condition_id"] for s in rows_by_split.values() for c in s
                if taxonomy.types[c["source_error_id"]].unit_related and c["unit_conversion_eligible"] is not True]
    bad_split = [c["condition_id"] for s, rows in rows_by_split.items() for c in rows if c["split"] != s]
    test_in_sft_train = [c["condition_id"] for c in rows_by_split[TEST] if built["groups"][c["question_group_id"]].half in ("A", "B")]
    val_with_sft = [c["condition_id"] for c in rows_by_split["validation"] if built["groups"][c["question_group_id"]].sft_ids]
    split_groups = {s: {c["question_group_id"] for c in rows} for s, rows in rows_by_split.items()}
    shared = (split_groups[TRAIN] & split_groups["validation"]) | (split_groups[TRAIN] & split_groups[TEST]) \
        | (split_groups["validation"] & split_groups[TEST])
    rl_checks = [("unit-related conditions only on allowlisted questions", not bad_unit, f"{len(bad_unit)}"),
                 ("every condition in its question group's split", not bad_split, f"{len(bad_split)}"),
                 ("no RL test question in the verifier training halves", not test_in_sft_train, f"{len(test_in_sft_train)}"),
                 ("no validation question in any verifier SFT data", not val_with_sft, f"{len(val_with_sft)}"),
                 ("train / validation / test share no question group", not shared, f"{len(shared)}"),
                 ("every stage = mapping(type)", all(c["newman_stage"] == taxonomy.stage_of(c["source_error_id"])
                                                     for s in rows_by_split.values() for c in s), "")]
    for name, passed, detail in rl_checks:
        print(f"  [{'ok' if passed else 'FAIL'}] {name} {'' if passed else detail}")
    if not all(p for _, p, _ in rl_checks):
        return 1
    out = prepared_dir / "rl"
    for split, rows in rows_by_split.items():
        write_jsonl(out / f"{split}.jsonl", rows)
    write_jsonl(out / "privileged.jsonl", priv)
    summary = {split: {"conditions": len(rows), "questions": len({(c["gsm8k_split"], c["gsm8k_row"]) for c in rows}),
                       "question_groups": len({c["question_group_id"] for c in rows}),
                       "by_type": dict(sorted(Counter(c["source_error_id"] for c in rows).items())),
                       "by_stage": dict(sorted(Counter(c["newman_stage"] for c in rows).items())),
                       "unit_eligible_questions": len({(c["gsm8k_split"], c["gsm8k_row"]) for c in rows if c["unit_conversion_eligible"]}),
                       "sha256": sha256_file(out / f"{split}.jsonl")}
               for split, rows in rows_by_split.items()}
    write_json(out / "meta.json", {**meta, "rl_data": dict(rd), "answer_contract": {"path": rel(contract_path), "sha256": sha256_file(contract_path)},
                                   "splits": summary, "validation": val_info, "checks": [{"check": n, "passed": p} for n, p, _ in rl_checks],
                                   "sft_split_manifest": {"path": rel(saved), "sha256": sha256_file(saved)}})
    for split, s in summary.items():
        print(f"  {split}: {s['conditions']} conditions on {s['questions']} questions ({s['question_groups']} groups)")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ConfigError as exc:
        raise SystemExit(f"config error: {exc}") from exc
