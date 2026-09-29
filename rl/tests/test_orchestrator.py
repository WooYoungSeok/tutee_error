"""Scoring path of the TRL adapter on CPU: mock clients, no torch.distributed, synthetic prepared data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tutee_rl.common import load_config, read_jsonl  # noqa: E402
from tutee_rl.orchestrator import GroupIntegrityError, RewardOrchestrator  # noqa: E402

EOS = 7


class FakeTokenizer:
    eos_token_id = EOS

    def batch_decode(self, ids, skip_special_tokens=True):
        return [" ".join(f"w{t}" for t in seq if not (skip_special_tokens and t == EOS)) for seq in ids]


def _prepared(tmp: Path, pair_ids):
    rows = [{"PairId": p, "QuestionId": p.split("__")[0], "MisconceptionId": 1, "problem": f"problem {p}",
             "target_misconception_description": "adds instead of multiplying", "group_id": p, "split": "train"} for p in pair_ids]
    priv = [{"PairId": p, "AnswerContract": "NUMBER_OR_STRUCTURED_MATH", "CorrectAnswerText": "12",
             "TargetDistractors": [{"option": "B", "text": "7"}], "OtherLabeledDistractors": [], "UnlabeledDistractors": []} for p in pair_ids]
    for name, data in (("train.jsonl", rows), ("privileged.jsonl", priv)):
        (tmp / name).write_text("".join(json.dumps(x) + "\n" for x in data), encoding="utf-8")


@pytest.mark.parametrize("config", ["configs/smoke_mock.yaml", "configs/student_likeness.yaml"])
def test_score_batch_end_to_end_with_mocks(tmp_path, config):
    pair_ids = ["1__1", "2__1", "3__1"]
    _prepared(tmp_path, pair_ids)
    cfg = load_config(ROOT / config, [f"paths.prepared_dir={tmp_path}", "smoke.mock_reward_clients=true",
                                      "policy.model=/nonexistent", "generation.max_completion_tokens=6"])
    orch = RewardOrchestrator(cfg, FakeTokenizer(), tmp_path / "run", is_main=True)
    funcs, weights = orch.reward_funcs()
    assert weights == [1.0, 0.5, 1.0]
    completion_ids = [[100 + 10 * g + i, 3, i, EOS] if i != 5 else [1, 2, 3, 4, 5, 6] for g in range(3) for i in range(8)]
    kwargs = {"PairId": [p for p in pair_ids for _ in range(8)], "trainer_state": None, "log_metric": None}
    main = funcs[0]([None] * 24, [None] * 24, completion_ids, **kwargs)
    aux = funcs[1]([None] * 24, [None] * 24, completion_ids, **kwargs)
    trunc = funcs[2]([None] * 24, [None] * 24, completion_ids, **kwargs)
    assert len(main) == len(aux) == len(trunc) == 24
    assert all(0.0 <= a <= 1.0 for a in aux)
    assert [t for i, t in enumerate(trunc) if i % 8 == 5] == [-0.5, -0.5, -0.5]  # no EOS at the limit
    assert all(t == 0.0 for i, t in enumerate(trunc) if i % 8 != 5)
    logged = read_jsonl(tmp_path / "run" / "rollouts" / "step_000000.jsonl")
    assert [r["PairId"] for r in logged] == kwargs["PairId"]
    assert len(read_jsonl(tmp_path / "run" / "rollouts" / "groups_000000.jsonl")) == 3
    assert "bleu_signature" in orch.describe()


def test_mixed_group_is_rejected(tmp_path):
    pair_ids = ["1__1", "2__1"]
    _prepared(tmp_path, pair_ids)
    cfg = load_config(ROOT / "configs/smoke_mock.yaml", [f"paths.prepared_dir={tmp_path}", "policy.model=/nonexistent"])
    orch = RewardOrchestrator(cfg, FakeTokenizer(), tmp_path / "run", is_main=True)
    items = [{"rank": 0, "local_idx": i, "pair_id": pair_ids[0] if i != 3 else pair_ids[1], "ids": [1, EOS], "text": "x"} for i in range(8)]
    with pytest.raises(GroupIntegrityError):
        orch._score_global(items, 0)
