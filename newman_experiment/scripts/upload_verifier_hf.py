#!/usr/bin/env python3
"""Upload one verifier checkpoint to a PRIVATE Hugging Face model repo (user request 2026-10-01).

Uploads the model files of <run_dir>/epoch_checkpoints/<checkpoint> (training_args.bin is left out: a pickle, not
needed for inference), the run's run_meta.json and test_eval/summary.json under newman_meta/, and a model card
written from them. The repo is created private; an existing public repo of the same name is refused.
The token comes from HF_TOKEN in tutee_error/.env and is never printed.

Usage (from newman_experiment/):
  python scripts/upload_verifier_hf.py --run_dir outputs/<run> [--checkpoint epoch-5] [--repo_id <user>/<name>] [--note "..."]
  default checkpoint = test_eval/summary.json best_checkpoint; default repo = <hf user>/newman-<run name>-<checkpoint>
Records <run_dir>/hf_upload_<checkpoint>.json (repo id, commit, files, sha256 of model.safetensors).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman.common import REPO_ROOT, load_dotenv, now_iso, read_json, resolve, sha256_file, write_json  # noqa: E402

SKIP = {"training_args.bin"}
CARD_KEYS = ("accuracy", "macro_f1", "negative_recall", "negative_false_acceptance", "positive_recall", "invalid_rate", "pair_accuracy")


def card(run_dir: Path, ckpt: str, meta: dict, summary: dict | None, note: str | None) -> str:
    lines = [f"# {run_dir.name} / {ckpt}", "",
             "Newman-stage × source-error-type alignment verifier (tutee_error, `newman_experiment/`). Private research checkpoint.", ""]
    if note:
        lines += [f"**Note:** {note}", ""]
    lines += ["| item | value |", "|---|---|",
              f"| role | verifier half {meta.get('half')} ({meta.get('role')}) |",
              f"| backbone | `{meta['model'] if isinstance(meta['model'], str) else meta['model'].get('name')}` |",
              f"| run name (W&B) | `{meta['run_name']}` |",
              f"| checkpoint | `{ckpt}` |",
              f"| git commit | `{(meta.get('git') or {}).get('commit')}` |",
              f"| training data sha256 | `{(meta.get('data') or {}).get('sha256')}` |",
              f"| effective batch | {meta.get('effective_batch')} |", ""]
    if summary:
        res = summary["results"].get(ckpt, {})
        lines += [f"SFT test ({summary['data']['rows']} rows, data sha256 `{summary['data']['sha256']}`), selection rule "
                  f"`{summary['selection_rule']}`, chosen on test (optimistic):", "",
                  "| " + " | ".join(CARD_KEYS) + " |", "|" + "---|" * len(CARD_KEYS),
                  "| " + " | ".join("" if res.get(k) is None else f"{res[k]:.4f}" for k in CARD_KEYS) + " |", ""]
    lines += ["Input: the verifier system/user prompts in `newman_experiment/prompts/verifier_*.txt` with the model's chat "
              "template; output exactly `aligned` or `not_aligned` (greedy).", ""]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run_dir", required=True)
    p.add_argument("--checkpoint", default=None)
    p.add_argument("--repo_id", default=None)
    p.add_argument("--note", default=None, help="one line shown at the top of the model card")
    args = p.parse_args()
    load_dotenv(REPO_ROOT / ".env")
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN is not set (tutee_error/.env)", file=sys.stderr)
        return 2
    from huggingface_hub import HfApi

    run_dir = resolve(args.run_dir)
    summary_path = run_dir / "test_eval" / "summary.json"
    summary = read_json(summary_path) if summary_path.exists() else None
    ckpt = args.checkpoint or (summary or {}).get("best_checkpoint")
    if not ckpt:
        print("no --checkpoint and no best_checkpoint in test_eval/summary.json", file=sys.stderr)
        return 2
    ckpt_dir = run_dir / "epoch_checkpoints" / ckpt
    if not (ckpt_dir / "model.safetensors").exists() and not list(ckpt_dir.glob("model-*.safetensors")):
        print(f"no safetensors in {ckpt_dir}", file=sys.stderr)
        return 2
    meta = read_json(run_dir / "run_meta.json")
    api = HfApi(token=token)
    repo_id = args.repo_id or f"{api.whoami()['name']}/newman-{run_dir.name}-{ckpt}"
    api.create_repo(repo_id, repo_type="model", private=True, exist_ok=True)
    if not api.model_info(repo_id).private:
        print(f"refusing: {repo_id} exists and is public", file=sys.stderr)
        return 2

    staging = run_dir / f".hf_staging_{ckpt}"
    staging.mkdir(exist_ok=True)
    (staging / "README.md").write_text(card(run_dir, ckpt, meta, summary, args.note), encoding="utf-8")
    meta_dir = staging / "newman_meta"
    meta_dir.mkdir(exist_ok=True)
    (meta_dir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if summary:
        (meta_dir / "test_eval_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    files = sorted(f.name for f in ckpt_dir.iterdir() if f.is_file() and f.name not in SKIP)
    print(f"uploading {ckpt_dir} -> {repo_id} (private): {files}", flush=True)
    commit = api.upload_folder(repo_id=repo_id, folder_path=str(ckpt_dir), ignore_patterns=sorted(SKIP),
                               commit_message=f"{run_dir.name} {ckpt}")
    commit2 = api.upload_folder(repo_id=repo_id, folder_path=str(staging), commit_message="model card and run metadata")
    remote = sorted(api.list_repo_files(repo_id))
    missing = [f for f in files if f not in remote]
    record = {"uploaded_at": now_iso(), "timezone": "Asia/Seoul", "repo_id": repo_id, "private": api.model_info(repo_id).private,
              "checkpoint": ckpt, "checkpoint_dir": str(ckpt_dir), "files": files, "remote_files": remote, "missing": missing,
              "model_sha256": {f: sha256_file(ckpt_dir / f) for f in files if f.endswith(".safetensors")},
              "commits": [getattr(commit, "oid", None), getattr(commit2, "oid", None)], "note": args.note}
    write_json(run_dir / f"hf_upload_{ckpt}.json", record)
    print(f"done: https://huggingface.co/{repo_id} private={record['private']} missing={missing}")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
