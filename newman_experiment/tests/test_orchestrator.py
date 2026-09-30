"""Scoring path of the Newman reward on CPU: mock clients, no torch.distributed, synthetic prepared data."""

from __future__ import annotations

import json

import pytest

from newman.common import load_config, read_jsonl, resolve
from newman.orchestrator import RewardOrchestrator
from newman.taxonomy import Taxonomy
from tutee_rl.orchestrator import GroupIntegrityError

EOS = 7
TAX = Taxonomy.load(resolve("configs/taxonomy.yaml"))


class FakeTokenizer:
    eos_token_id = EOS

    def batch_decode(self, ids, skip_special_tokens=True):
        return [" ".join(f"w{t}" for t in seq if not (skip_special_tokens and t == EOS)) for seq in ids]


def prepared(tmp, ids, stage_override=None):
    rows = []
    for i, cid in enumerate(ids):
        tid = TAX.adopted_ids()[i]
        rows.append({"condition_id": cid, "question_group_id": f"g{i}", "split": "train", "question": f"question {i}",
                     "source_error_id": tid, "newman_stage": stage_override or TAX.stage_of(tid),
                     "unit_conversion_eligible": False, "gsm8k_split": "train", "gsm8k_row": i})
    priv = [{"condition_id": cid, "reference_answer": "12", "answer_contract": "NUMBER"} for cid in ids]
    for name, data in (("train.jsonl", rows), ("privileged.jsonl", priv)):
        (tmp / name).write_text("".join(json.dumps(x) + "\n" for x in data), encoding="utf-8")


def cfg_for(tmp, config="configs/smoke/rl_mock.yaml"):
    return load_config(config, [f"paths.prepared_dir={tmp}", "smoke.mock_reward_clients=true", "policy.model=/nonexistent",
                                "generation.max_completion_tokens=6"])


@pytest.mark.parametrize("config", ["configs/smoke/rl_mock.yaml", "configs/student_likeness.yaml"])
def test_score_batch_end_to_end_with_mocks(tmp_path, config):
    ids = ["c1", "c2", "c3"]
    prepared(tmp_path, ids)
    orch = RewardOrchestrator(cfg_for(tmp_path, config), FakeTokenizer(), tmp_path / "run", is_main=True)
    funcs, weights = orch.reward_funcs()
    assert weights == [1.0, 0.5, 1.0]
    completion_ids = [[100 + 10 * g + i, 3, i, EOS] if i != 5 else [1, 2, 3, 4, 5, 6] for g in range(3) for i in range(8)]
    kwargs = {"condition_id": [c for c in ids for _ in range(8)], "trainer_state": None, "log_metric": None}
    main = funcs[0]([None] * 24, [None] * 24, completion_ids, **kwargs)
    aux = funcs[1]([None] * 24, [None] * 24, completion_ids, **kwargs)
    trunc = funcs[2]([None] * 24, [None] * 24, completion_ids, **kwargs)
    assert len(main) == len(aux) == len(trunc) == 24
    assert set(main) <= {-0.75, 0.0, 1.0} and all(0.0 <= a <= 1.0 for a in aux)
    assert [t for i, t in enumerate(trunc) if i % 8 == 5] == [-0.5, -0.5, -0.5]
    logged = read_jsonl(tmp_path / "run" / "rollouts" / "step_000000.jsonl")
    assert [r["condition_id"] for r in logged] == kwargs["condition_id"]
    assert {r["newman_stage"] for r in logged} == {TAX.stage_of(t) for t in TAX.adopted_ids()[:3]}
    assert "verifier_a" in logged[0] and "verifier_a" in orch.describe()


def test_evaluation_roles_and_api_items(tmp_path):
    ids = ["c1", "c2"]
    prepared(tmp_path, ids)
    orch = RewardOrchestrator(cfg_for(tmp_path), FakeTokenizer(), tmp_path / "run", is_main=True, verifier_role="b",
                              secondary_verifier=("a", {"checkpoint": "mock-a"}))
    items = [{"rank": 0, "local_idx": i, "condition_id": ids[i // 8], "k": i % 8, "ids": None, "text": f"sol {i}",
              "truncated": i % 8 == 0, "length": 5} for i in range(16)]
    results, groups, m = orch.score_global(items, 0, full=True)
    assert [r["trunc"] for r in results if r["k"] == 0] == [-0.5, -0.5]
    assert "verifier_b/accept_rate_incorrect" in m and "verifier_a/accept_rate_incorrect" in m
    assert "verifier_ba/disagreement_rate_incorrect" in m and "target/success_rate_b" in m
    wrong = [r for r in results if r["answer_check"]["verdict"] == "incorrect"]
    assert all(r["verifier_b"] and r["verifier_a"] for r in wrong)


def test_stage_that_is_not_mapping_of_the_type_is_rejected(tmp_path):
    wrong = next(s for s in TAX.stages if s != TAX.stage_of(TAX.adopted_ids()[0]))
    prepared(tmp_path, ["c1"], stage_override=wrong)
    with pytest.raises(GroupIntegrityError):
        RewardOrchestrator(cfg_for(tmp_path), FakeTokenizer(), tmp_path / "run", is_main=True)


def test_mixed_group_is_rejected(tmp_path):
    ids = ["c1", "c2"]
    prepared(tmp_path, ids)
    orch = RewardOrchestrator(cfg_for(tmp_path), FakeTokenizer(), tmp_path / "run", is_main=True)
    items = [{"rank": 0, "local_idx": i, "condition_id": ids[0] if i != 3 else ids[1], "ids": [1, EOS], "text": "x"} for i in range(8)]
    with pytest.raises(GroupIntegrityError):
        orch.score_global(items, 0)
