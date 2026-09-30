"""What must hold before a real (non-smoke) training or evaluation run (user rule 1).

  * no open decision left as REQUIRED in the keys the run reads;
  * every draft text the run reads approved and unchanged since (approvals.py);
  * data prepared with the verified mapping workbook (not --allow-unverified-mapping).
Smoke runs (run name smoke_*) get the same list as warnings in their metadata and are never blocked.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from . import approvals
from .common import REQUIRED, SMOKE_PREFIX, find_required, get_path, read_json, resolve, sha256_file


def is_smoke(run_name: str | None) -> bool:
    return bool(run_name) and str(run_name).startswith(SMOKE_PREFIX)


def required_problems(cfg: Mapping[str, Any], keys: Iterable[str]) -> list[str]:
    out = []
    for key in keys:
        try:
            value = get_path(cfg, key)
        except (KeyError, TypeError):
            out.append(f"{key} is missing")
            continue
        if value == REQUIRED or find_required(value):
            out.append(f"{key} is still REQUIRED (open decision)")
    return out


def data_problems(meta_path) -> list[str]:
    path = resolve(meta_path)
    if not path.exists():
        return [f"{path} not found (scripts/prepare_data.py)"]
    meta = read_json(path)
    return [] if meta.get("mapping_verified") else [f"{path} was prepared without the verified mapping workbook"]


def verifier_training(cfg: Mapping[str, Any]) -> list[str]:
    p = required_problems(cfg, ["model.name", "experiment", "half"])
    p += approvals.problems(["taxonomy_definitions", "verifier_prompt", "verifier_backbones"],
                            {"verifier_prompt": [cfg["prompts"]["system"], cfg["prompts"]["user"]],
                             "taxonomy_definitions": [cfg["taxonomy"]]})
    p += data_problems(f"{cfg['data_dir']}/meta.json")
    return p


def student_run(cfg: Mapping[str, Any], evaluation: bool = False) -> list[str]:
    mock = bool(cfg.get("smoke", {}).get("mock_reward_clients"))
    keys = ["experiment", "rewards.auxiliary_reward"] + ([] if mock else ["verifier.checkpoint"])
    if evaluation:  # evaluation.select_metric only decides the best snapshot; metrics are computed while it is open
        keys += ["evaluation.verifier.checkpoint"]
    p = required_problems(cfg, keys)
    items = ["taxonomy_definitions", "student_prompt", "verifier_prompt", "answer_judge_prompt"]
    pr = cfg["prompts"]
    used = {"student_prompt": [pr["student"]], "verifier_prompt": [pr["verifier_system"], pr["verifier_user"]],
            "taxonomy_definitions": [cfg["paths"]["taxonomy"]],
            "answer_judge_prompt": [pr["answer_judge_system"], pr["answer_judge_user"], pr["answer_contract"]]}
    if cfg["rewards"]["auxiliary_reward"] == "student_likeness" or evaluation:
        items.append("student_likeness_prompt")
        used["student_likeness_prompt"] = [pr["student_likeness_system"], pr["student_likeness_user"], cfg["student_likeness"]["examples"]]
    p += approvals.problems(items, used)
    meta_path = f"{cfg['paths']['prepared_dir']}/meta.json"
    p += data_problems(meta_path)
    if resolve(meta_path).exists():
        meta = read_json(resolve(meta_path))
        contract = (meta.get("answer_contract") or {}).get("sha256")
        if contract and contract != sha256_file(resolve(pr["answer_contract"])):
            p.append("the prepared privileged.jsonl used another answer contract than prompts.answer_contract; rerun --stage rl")
    return p
