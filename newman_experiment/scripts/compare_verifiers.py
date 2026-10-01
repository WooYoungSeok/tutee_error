#!/usr/bin/env python3
"""One comparison table for verifiers evaluated on the same SFT test pairs (trained checkpoints and API models).

Each entry is LABEL=<dir with metrics.json and predictions.jsonl> (an eval_verifier.py snapshot folder or an
eval_verifier_api.py run folder). All entries must have the same test data sha256 and the same pair ids.
Reports the headline metrics with question-group bootstrap CIs, negatives by kind (same / different stage),
accuracy by dataset and by target stage, and paired question-group bootstrap differences against --reference.

Usage (from newman_experiment/):
  python scripts/compare_verifiers.py --entry A=outputs/<run>/test_eval/epoch-5 --entry gpt-5.1=outputs/verifier_api_gpt-5.1_... \
      [--reference A] [--out reports/verifier_comparison_<stamp>.md]
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman.common import now_iso, read_json, read_jsonl, rel, resolve, run_stamp  # noqa: E402

HEAD = ("accuracy", "macro_f1", "negative_recall", "negative_false_acceptance", "positive_recall", "invalid_rate", "pair_accuracy")


def fmt(v) -> str:
    return "–" if v is None else f"{v:.4f}"


def group_stats(preds):
    """question group -> [correct, n, accepted negatives, negatives, correct positives, positives]"""
    g = defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    for r in preds:
        s = g[r["question_group_id"]]
        s[0] += r["prediction"] == r["target"]
        s[1] += 1
        if r["target"] == "not_aligned":
            s[2] += r["prediction"] == "aligned"
            s[3] += 1
        else:
            s[4] += r["prediction"] == "aligned"
            s[5] += 1
    return g


def paired_diff(a, b, n_samples=1000, seed=42):
    import numpy as np

    gids = sorted(set(a) & set(b))
    A = np.array([a[x] for x in gids], dtype=float)
    B = np.array([b[x] for x in gids], dtype=float)
    rng = np.random.RandomState(seed)
    out = {"accuracy": [], "negative_false_acceptance": [], "positive_recall": []}
    for _ in range(n_samples):
        pick = rng.randint(0, len(gids), size=len(gids))
        sa, sb = A[pick].sum(0), B[pick].sum(0)
        out["accuracy"].append(sa[0] / sa[1] - sb[0] / sb[1])
        out["negative_false_acceptance"].append(sa[2] / sa[3] - sb[2] / sb[3])
        out["positive_recall"].append(sa[4] / sa[5] - sb[4] / sb[5])
    sa, sb = A.sum(0), B.sum(0)
    point = {"accuracy": sa[0] / sa[1] - sb[0] / sb[1], "negative_false_acceptance": sa[2] / sa[3] - sb[2] / sb[3],
             "positive_recall": sa[4] / sa[5] - sb[4] / sb[5]}
    return {k: (point[k], float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) for k, v in out.items()}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--entry", action="append", required=True, help="LABEL=<dir>")
    p.add_argument("--reference", default=None, help="label the paired differences are taken against (default: first)")
    p.add_argument("--out", default=None)
    args = p.parse_args()
    entries = {}
    for e in args.entry:
        label, _, d = e.partition("=")
        d = resolve(d)
        entries[label] = {"dir": d, "result": read_json(d / "metrics.json"), "preds": read_jsonl(d / "predictions.jsonl")}
    shas = {k: v["result"].get("data_sha256") or v["result"].get("generation", {}).get("data", {}).get("sha256") for k, v in entries.items()}
    ids = {k: sorted(r["pair_id"] for r in v["preds"]) for k, v in entries.items()}
    first = next(iter(entries))
    bad = [k for k in entries if shas[k] != shas[first] or ids[k] != ids[first]]
    if bad:
        raise SystemExit(f"not the same test data as {first}: {bad} (sha256 {shas})")
    ref = args.reference or first

    L = [f"# Verifier comparison on the SFT test pairs", "",
         f"Created {now_iso()} (Asia/Seoul). Test data sha256 `{shas[first]}`, {len(ids[first])} pair rows. "
         "CIs: 95% question-group bootstrap (1000). Trained checkpoints were chosen on this test split (optimistic).", "",
         "| verifier | source | " + " | ".join(HEAD) + " | accuracy 95% CI |", "|---|---|" + "---|" * (len(HEAD) + 1)]
    for k, v in entries.items():
        m = v["result"]["metrics"]
        ci = m.get("bootstrap_ci_question_groups", {}).get("accuracy") or {}
        L.append(f"| {k} | `{rel(v['dir'])}` | " + " | ".join(fmt(m.get(h)) for h in HEAD)
                 + f" | [{fmt(ci.get('low'))}, {fmt(ci.get('high'))}] |")
    L += ["", "Negative false acceptance by negative kind (accepted / negatives):", "",
          "| verifier | same stage | different stage |", "|---|---|---|"]
    for k, v in entries.items():
        cells = []
        for kind in ("same_stage", "different_stage"):
            neg = [r for r in v["preds"] if r["target"] == "not_aligned" and r["negative_kind"] == kind]
            acc = sum(r["prediction"] == "aligned" for r in neg)
            cells.append(f"{acc} / {len(neg)} ({acc / len(neg):.3f})" if neg else "–")
        L.append(f"| {k} | " + " | ".join(cells) + " |")
    rels = sorted({r["negative_dataset_relation"] for v in entries.values() for r in v["preds"] if r["target"] == "not_aligned"})
    L += ["", "Negative false acceptance by the negative's source (same dataset as the solution or another dataset):", "",
          "| verifier | " + " | ".join(rels) + " |", "|---|" + "---|" * len(rels)]
    for k, v in entries.items():
        cells = []
        for rel_ in rels:
            neg = [r for r in v["preds"] if r["target"] == "not_aligned" and r["negative_dataset_relation"] == rel_]
            acc = sum(r["prediction"] == "aligned" for r in neg)
            cells.append(f"{acc} / {len(neg)} ({acc / len(neg):.3f})" if neg else "–")
        L.append(f"| {k} | " + " | ".join(cells) + " |")
    for title, key in (("Accuracy by dataset", lambda r: f"{r['dataset']}|{r['benchmark'] or '-'}"),
                       ("Accuracy by target stage", lambda r: r["target_newman_stage"])):
        groups = sorted({key(r) for r in entries[first]["preds"]})
        L += ["", f"{title}:", "", "| verifier | " + " | ".join(groups) + " |", "|---|" + "---|" * len(groups)]
        for k, v in entries.items():
            cells = []
            for g in groups:
                rows = [r for r in v["preds"] if key(r) == g]
                cells.append(f"{sum(r['prediction'] == r['target'] for r in rows) / len(rows):.3f} (n={len(rows)})")
            L.append(f"| {k} | " + " | ".join(cells) + " |")
    gs = {k: group_stats(v["preds"]) for k, v in entries.items()}
    L += ["", f"Paired difference against {ref} (other − {ref}, 95% question-group bootstrap):", "",
          "| verifier | accuracy | negative false acceptance | positive recall |", "|---|---|---|---|"]
    for k in entries:
        if k == ref:
            continue
        d = paired_diff(gs[k], gs[ref])
        L.append(f"| {k} | " + " | ".join(f"{d[m][0]:+.4f} [{d[m][1]:+.4f}, {d[m][2]:+.4f}]"
                                          for m in ("accuracy", "negative_false_acceptance", "positive_recall")) + " |")
    text = "\n".join(L) + "\n"
    out = resolve(args.out or f"reports/verifier_comparison_{run_stamp()}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"-> {rel(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
