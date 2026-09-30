#!/usr/bin/env python3
"""Markdown for rl/EXPERIMENTS.md read from a run's own records (user rule 2: settings and results are copied from
run_meta.json / generation_meta.json / metrics.json / summary.json, never from memory or the config's intent).

Usage (from newman_experiment/):  python scripts/record_experiment.py outputs/<run> [outputs/<run> ...]
Prints one "실행 확인" block per run (verifier SFT or Student GRPO); paste it into rl/EXPERIMENTS.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newman.common import read_json, resolve  # noqa: E402


def fmt(v, digits=4):
    if isinstance(v, float):
        return f"{v:.{digits}f}"
    return "-" if v is None else str(v)


def table(rows):
    return "\n".join(["| 항목 | 값 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rows])


def verifier_block(run: Path, meta: dict) -> str:
    c, t = meta["config"], meta["config"]["training"]
    opt = meta.get("optimizer") or {}
    snaps = ", ".join(f"epoch-{s['epoch']} ({s.get('size_gb')} GB)" for s in meta.get("snapshots", [])) or "-"
    rows = [("run / W&B", f"`{meta['run_name']}` / {meta.get('wandb_project') or 'none'}"),
            ("역할 / half", f"{meta['role']} / {meta['half']}"), ("backbone", f"`{meta['model']}`"),
            ("데이터", f"`{meta['data']['file']}` sha256 `{meta['data']['sha256'][:12]}`, {meta['data']['pair_rows']} rows / "
                     f"{meta['data']['anchors']} anchors, mapping verified {meta['data']['prepared_meta_mapping_verified']}"),
            ("학습", f"{t['num_train_epochs']} epoch, lr {t['learning_rate']}, wd {t['weight_decay']}, warmup {t['warmup_ratio']}, "
                   f"{t['lr_scheduler_type']}, batch {t['per_device_train_batch_size']}x{t['gradient_accumulation_steps']}x{meta['world_size']} "
                   f"= {meta['effective_batch']}, max grad norm {t['max_grad_norm']}, bf16 {t['bf16']}, max len {c['max_seq_length']}"),
            ("optimizer (실제)", f"{' > '.join(opt.get('classes', [])) or '-'} {opt.get('param_group_0', '')}"),
            ("저장", f"snapshots {snaps}; resume checkpoints {meta.get('resume_checkpoints') or 'none'}"),
            ("프롬프트 / taxonomy", f"system `{meta['prompt']['system_sha256'][:12]}` user `{meta['prompt']['user_sha256'][:12]}` / "
                                 f"`{meta['taxonomy']['sha256'][:12]}`"),
            ("승인", ", ".join(f"{k}: {v['state']}" for k, v in meta["approvals"].items())),
            ("버전 / git", f"torch {meta['versions'].get('torch')}, transformers {meta['versions'].get('transformers')}, deepspeed "
                         f"{meta['versions'].get('deepspeed')} / `{(meta['git'].get('commit') or '')[:12]}` dirty {meta['git'].get('tracked_changes')}"),
            ("시간", f"{meta['created_at']} → {meta.get('finished_at', '(running)')}")]
    out = [f"#### {meta['run_name']} (실행 확인)", "", table(rows), ""]
    s = run / "test_eval" / "summary.json"
    if s.exists():
        summary = read_json(s)
        keys = ("accuracy", "macro_f1", "negative_recall", "negative_false_acceptance", "positive_recall", "invalid_rate", "test_loss")
        out += [f"SFT test (`{summary['data']['path']}` {summary['data']['rows']} rows, sha256 `{summary['data']['sha256'][:12]}`), "
                f"selection rule {summary['selection_rule']}, best **{summary['best_checkpoint']}** — {summary['selection_note']}", "",
                "| checkpoint | " + " | ".join(keys) + " |", "|---|" + "---|" * len(keys)]
        out += [f"| {n} | " + " | ".join(fmt(m[k]) for k in keys) + " |" for n, m in summary["results"].items()]
        out += [""]
    return "\n".join(out)


def student_block(run: Path, meta: dict) -> str:
    c = meta["config"]
    t, g, rw = c["training"], c["generation"], meta["reward"]
    ac = rw.get("answer_check", {})
    ver = rw.get("verifier_a", {})
    rows = [("run / W&B", f"`{meta['run_name']}` / {meta.get('wandb_project') or 'none'}"), ("policy", f"`{c['policy']['model']}`"),
            ("데이터", f"{meta['data']['conditions']} train conditions, sha256 `{meta['data']['train_sha256'][:12]}`, prompt tokens max "
                     f"{meta['data']['prompt_tokens_max']} / mean {meta['data']['prompt_tokens_mean']:.0f}, mapping verified "
                     f"{meta['data']['prepared_meta'].get('mapping_verified')}"),
            ("샘플링", f"G {g['num_generations']}, T {g['temperature']}, top_p {g['top_p']}, top_k {g['top_k']}, rep {g['repetition_penalty']}, "
                     f"max {g['max_completion_tokens']} tokens"),
            ("GRPO", f"{meta['completions_per_step']} completions = {meta['prompts_per_step']} conditions / step ({meta['num_processes']} GPU), "
                     f"~{meta['steps_per_epoch_estimate']} step/epoch, {t['num_train_epochs']} epoch, lr {t['learning_rate']}, beta {t['beta']}, "
                     f"eps {t['epsilon']}, {t['loss_type']}, scale {t['scale_rewards']}"),
            ("IS 보정", ", ".join(f"{k} {v}" for k, v in meta["trl_loss"].items() if "importance" in k or "bias" in k)),
            ("reward", f"weights {rw['reward_weights']}, aux {rw['mode']}"),
            ("gpt-5-nano 채점 (실제 요청)", f"{ac.get('request_fields')} prompt `{str(ac.get('prompt_version'))[:12]}`"),
            ("verifier A", f"`{ver.get('checkpoint')}` {ver.get('sampling')}"),
            ("저장", f"snapshots {[s['epoch'] for s in meta.get('snapshots', [])]}, resume checkpoints {len(meta.get('resume_checkpoints') or [])}"),
            ("승인", ", ".join(f"{k}: {v['state']}" for k, v in meta["approvals"].items())),
            ("버전 / git", f"torch {meta['versions'].get('torch')}, trl {meta['versions'].get('trl')}, vllm {meta['versions'].get('vllm')} / "
                         f"`{(meta['git'].get('commit') or '')[:12]}` dirty {meta['git'].get('tracked_changes')}"),
            ("시간", f"{meta['created_at']} → {meta.get('finished_at', '(running)')}")]
    if rw.get("student_likeness"):
        rows.insert(9, ("student-likeness judge", str(rw["student_likeness"])))
    out = [f"#### {meta['run_name']} (실행 확인)", "", table(rows), ""]
    s = run / "test_eval" / "summary.json"
    if s.exists():
        summary = read_json(s)
        keys = ("wrong_rate", "b_accept_given_wrong", "b_joint_success", "a_accept_given_wrong", "ab_disagreement_given_wrong",
                "zero_success_condition_rate", "reward_total_mean", "truncation_rate")
        out += [f"Test (verifier B `{summary['test_verifier']}`), select metric {summary['select_metric']}, best **{summary['best_snapshot']}** "
                f"— {summary['selection_note']}", "", "| model | " + " | ".join(keys) + " |", "|---|" + "---|" * len(keys)]
        out += [f"| {n} | " + " | ".join(fmt(r.get(k)) for k in keys) + " |" for n, r in summary["results"].items()]
        out += [""]
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for arg in sys.argv[1:]:
        run = resolve(arg)
        meta = read_json(run / "run_meta.json")
        print(verifier_block(run, meta) if "role" in meta else student_block(run, meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
