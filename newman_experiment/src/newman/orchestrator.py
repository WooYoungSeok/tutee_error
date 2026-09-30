"""TRL adapter for the Newman reward: one scoring pass per rollout batch, exposed as three reward functions.

Same structure and failure policy as tutee_rl.orchestrator (the Eedi run): TRL calls every reward function on
every rank with that rank's slice of the batch; the first gathers all ranks' completions, rank 0 scores whole
groups of `num_generations` (network calls run concurrently on a background event loop) and broadcasts the
per-rollout results; the other two read the cached result. A reward call that cannot complete aborts the batch
(RewardExecutionError); it is never scored as incorrect / not_aligned / tie.

Per rollout of one condition (Q, N, E), plan 8.3:
  main_i  = -0.75   final answer correct, or no clear final answer (null)
          =  1      incorrect and the verifier says `aligned` in both samples
          =  0      incorrect otherwise (not_aligned or invalid in either sample)
  trunc_i = -0.5    length limit reached without EOS
  aux_i   in [0, 1] BLEU diversity or pairwise student-likeness inside G (incorrect and accepted), 0 when |G| < 2
reward_weights = [1, auxiliary_weight (0.5), 1]; KL stays in the GRPO objective.

The verifier is the frozen half-A model in training (metrics verifier_a/*). Test evaluation passes the half-B
model (verifier_b/*) and can add A as a diagnostic that never enters the reward (A/B disagreement, plan 10.3).
"""

from __future__ import annotations

import asyncio
import threading
import time
import traceback
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from tutee_rl.clients import AnswerChecker, PairwiseJudge, RewardExecutionError, openai_api_client
from tutee_rl.orchestrator import GroupIntegrityError, policy_eos_ids
from tutee_rl.rewards import (
    TruncationInfo,
    combine_group,
    diversity_scores,
    make_bleu,
    normalized_win_scores,
    pair_schedule,
    truncation_info,
)

from .common import hash_obj, read_json, read_jsonl, read_template, resolve, write_jsonl
from .taxonomy import STAGE_IDS, Taxonomy
from .verifier_format import load_verifier_prompt

KEY = "condition_id"


def _dist():
    import torch.distributed as dist

    return dist if dist.is_available() and dist.is_initialized() else None


def accepted(labels: Sequence[str] | None) -> bool:
    return bool(labels) and all(x == "aligned" for x in labels)


class RewardOrchestrator:
    def __init__(self, cfg: Mapping[str, Any], policy_tokenizer: Any, run_dir: Path, is_main: bool,
                 verifier_role: str = "a", secondary_verifier: tuple[str, Mapping[str, Any]] | None = None):
        self.cfg = cfg
        self.mode = cfg["rewards"]["auxiliary_reward"]
        self.num_generations = int(cfg["generation"]["num_generations"])
        self.max_completion = int(cfg["generation"]["max_completion_tokens"])
        self.tokenizer = policy_tokenizer
        self.eos_ids = policy_eos_ids(policy_tokenizer, cfg["policy"]["model"])
        self.run_dir = Path(run_dir)
        self.is_main = is_main
        self.seed = int(cfg["seed"])
        self.role = verifier_role
        self.secondary_role, self.secondary_cfg = secondary_verifier if secondary_verifier else (None, None)
        self._last: tuple[str, list[dict[str, Any]]] | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        if is_main:
            self._init_main()

    # --- setup (rank 0 only) -------------------------------------------------

    def _init_main(self) -> None:
        cfg = self.cfg
        prepared = resolve(cfg["paths"]["prepared_dir"])
        self.taxonomy = Taxonomy.load(resolve(cfg["paths"]["taxonomy"]))
        self.privileged = {r[KEY]: r for r in read_jsonl(prepared / "privileged.jsonl")}
        self.rows: dict[str, dict[str, Any]] = {}
        for split in ("train", "validation", "test"):
            path = prepared / f"{split}.jsonl"
            if path.exists():
                self.rows.update({r[KEY]: r for r in read_jsonl(path)})
        bad = [cid for cid, r in self.rows.items() if self.taxonomy.stage_of(r["source_error_id"]) != r["newman_stage"]]
        if bad:
            raise GroupIntegrityError(f"{len(bad)} conditions whose stage is not mapping(E) under the current taxonomy, e.g. {bad[:3]}")
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, name="reward-loop", daemon=True).start()
        self._run(self._init_clients())
        self.bleu = make_bleu(**{k: cfg["diversity"][k] for k in ("smooth_method", "effective_order", "tokenize", "lowercase")})

    async def _init_clients(self) -> None:
        cfg = self.cfg
        self.secondary = None
        if cfg.get("smoke", {}).get("mock_reward_clients"):
            from tutee_rl.mock import MockAnswerChecker, MockJudge, MockVerifier

            self.answer, self.verifier = MockAnswerChecker(), MockVerifier()
            self.secondary = MockVerifier() if self.secondary_cfg else None
            self.judge = MockJudge() if self.mode == "student_likeness" else None
            return

        from openai import AsyncOpenAI

        from .clients import make_verifier

        p, ac, sl = cfg["prompts"], cfg["answer_check"], cfg["student_likeness"]
        pool = int(ac["concurrency"]) + (int(sl["concurrency"]) if self.mode == "student_likeness" and sl["backend"] == "openai" else 0)
        self.openai = openai_api_client(float(ac["request_timeout_s"]), pool, float(cfg["openai_client"]["keepalive_expiry_s"]))
        self.answer = AnswerChecker(ac, read_template(p["answer_judge_system"]), read_template(p["answer_judge_user"]), self.openai)
        vprompt = load_verifier_prompt(p["verifier_system"], p["verifier_user"])
        self.verifier = make_verifier(cfg["verifier"], vprompt, self.taxonomy)
        if self.secondary_cfg:
            self.secondary = make_verifier(self.secondary_cfg, vprompt, self.taxonomy)
        self.judge = None
        if self.mode == "student_likeness":
            examples = read_json(resolve(sl["examples"]))["examples"]
            client = self.openai if sl["backend"] == "openai" else AsyncOpenAI(base_url=sl["base_url"], api_key="EMPTY", max_retries=0)
            self.judge = PairwiseJudge(sl, read_template(p["student_likeness_system"]), read_template(p["student_likeness_user"]),
                                       examples, client)

    def _run(self, coro):
        assert self.loop is not None
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()

    def describe(self) -> dict[str, Any]:
        """Settings recorded in the run metadata, including the exact API payload shape (reasoning effort sent)."""
        out: dict[str, Any] = {"mode": self.mode, "policy_eos_ids": sorted(self.eos_ids), "verifier_role": self.role}
        if self.is_main:
            out["answer_check"] = {**self.answer.settings(), "prompt_version": self.answer.prompt_version}
            if hasattr(self.answer, "payload"):
                payload = self.answer.payload("<user text>")
                out["answer_check"]["request_fields"] = {k: v for k, v in payload.items() if k not in ("instructions", "input")}
            out[f"verifier_{self.role}"] = {"checkpoint": self.cfg["verifier"]["checkpoint"], "sampling": self.verifier.sampling()}
            if self.secondary is not None:
                out[f"verifier_{self.secondary_role}"] = {"checkpoint": self.secondary_cfg["checkpoint"],
                                                          "sampling": self.secondary.sampling(), "enters_reward": False}
            out["mock_reward_clients"] = bool(self.cfg.get("smoke", {}).get("mock_reward_clients"))
            out["bleu_signature"] = str(self.bleu.get_signature())
            out["taxonomy_sha256"] = self.taxonomy.sha256
            if self.judge is not None:
                out["student_likeness"] = {"model": self.cfg["student_likeness"].get("model"), "prompt_version": self.judge.prompt_version,
                                           "decoding": self.judge.decoding_record()}
        return out

    # --- TRL reward functions ------------------------------------------------

    def reward_funcs(self) -> tuple[list[Callable[..., list[float]]], list[float]]:
        def main(prompts, completions, completion_ids, **kwargs):
            return [r["main"] for r in self._score(completion_ids, kwargs)]

        def aux(prompts, completions, completion_ids, **kwargs):
            return [r["aux"] for r in self._cached(completion_ids, kwargs)]

        def format_truncation(prompts, completions, completion_ids, **kwargs):
            return [r["trunc"] for r in self._cached(completion_ids, kwargs)]

        aux.__name__ = f"aux_{self.mode}"
        return [main, aux, format_truncation], [1.0, float(self.cfg["rewards"]["auxiliary_weight"]), 1.0]

    @staticmethod
    def _fingerprint(completion_ids: Sequence[Sequence[int]], keys: Sequence[str]) -> str:
        return hash_obj({"ids": [list(map(int, x)) for x in completion_ids], "keys": list(keys)})

    def _cached(self, completion_ids, kwargs) -> list[dict[str, Any]]:
        fp = self._fingerprint(completion_ids, kwargs[KEY])
        if self._last is None or self._last[0] != fp:
            raise RuntimeError("reward cache miss: `main` must run first on the same batch")
        return self._last[1]

    def _score(self, completion_ids, kwargs) -> list[dict[str, Any]]:
        keys = list(kwargs[KEY])
        state = kwargs.get("trainer_state")
        step = int(getattr(state, "global_step", 0) or 0)
        log_metric = kwargs.get("log_metric")
        dist = _dist()
        rank = dist.get_rank() if dist else 0

        texts = self.tokenizer.batch_decode(completion_ids, skip_special_tokens=True)
        local = [{"rank": rank, "local_idx": i, KEY: keys[i], "ids": list(map(int, completion_ids[i])), "text": texts[i].strip()}
                 for i in range(len(keys))]
        if dist:
            gathered: list[Any] = [None] * dist.get_world_size()
            dist.all_gather_object(gathered, local)
            items = [x for part in gathered for x in part]
        else:
            items = local

        payload: list[Any] = [None]
        if self.is_main:
            try:
                results, metrics = self.score_global(items, step)
                payload = [{"ok": True, "results": results, "metrics": metrics}]
            except Exception as exc:  # noqa: BLE001 - every rank must learn about the failure
                traceback.print_exc()
                payload = [{"ok": False, "error": f"{type(exc).__name__}: {exc}"}]
        if dist:
            dist.broadcast_object_list(payload, src=0)
        outcome = payload[0]
        if not outcome["ok"]:
            raise RewardExecutionError(f"reward scoring aborted this rollout batch: {outcome['error']}")
        mine = sorted((r for r in outcome["results"] if r["rank"] == rank), key=lambda r: r["local_idx"])
        if len(mine) != len(local):
            raise GroupIntegrityError("broadcast results do not match the local batch")
        if self.is_main and log_metric is not None:
            for name, value in outcome["metrics"].items():
                log_metric(name, value)
        self._last = (self._fingerprint(completion_ids, keys), mine)
        return mine

    # --- scoring (rank 0) ----------------------------------------------------

    def score_global(self, items: list[dict[str, Any]], step: int, full: bool = False):
        """Score consecutive blocks of num_generations (one condition each). Items carry token `ids`, or (API
        baselines) `ids=None` with an explicit `truncated` flag. full=True returns the complete rollout records."""
        g = self.num_generations
        if len(items) % g:
            raise GroupIntegrityError(f"{len(items)} completions is not a multiple of num_generations={g}")
        groups = [items[i:i + g] for i in range(0, len(items), g)]
        seen: set[str] = set()
        for block in groups:
            keys = {x[KEY] for x in block}
            if len(keys) != 1:
                raise GroupIntegrityError(f"a block of {g} consecutive completions mixes conditions {sorted(keys)}")
            key = next(iter(keys))
            if key in seen:
                raise GroupIntegrityError(f"condition {key} appears in two groups of one batch")
            if key not in self.privileged or key not in self.rows:
                raise GroupIntegrityError(f"condition {key} has no prepared row / privileged answer")
            seen.add(key)
        started = time.monotonic()
        scored = self._run(self._score_groups(groups, step))
        elapsed = time.monotonic() - started
        results = [r for rows, _ in scored for r in rows]
        group_logs = [glog for _, glog in scored]
        self._write_logs(step, results, group_logs)
        metrics = self.metrics(results, group_logs, elapsed)
        if full:
            return results, group_logs, metrics
        return [{k: r[k] for k in ("rank", "local_idx", "main", "aux", "trunc")} for r in results], metrics

    async def _score_groups(self, groups: list[list[dict[str, Any]]], step: int):
        return await asyncio.gather(*[self._score_group(block, step) for block in groups])

    def _truncation(self, item: Mapping[str, Any]) -> TruncationInfo:
        if item.get("ids") is not None:
            return truncation_info(item["ids"], self.eos_ids, self.max_completion)
        cut = bool(item["truncated"])
        return TruncationInfo(truncated=cut, ends_with_eos=not cut, length=int(item.get("length") or 0), anomaly=False)

    async def _score_group(self, block: list[dict[str, Any]], step: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        key = block[0][KEY]
        row, priv = self.rows[key], self.privileged[key]
        problem, error_id = row["question"], row["source_error_id"]

        async def one(item):
            check = await self.answer.check(problem, str(priv["answer_contract"]), str(priv["reference_answer"]), item["text"])
            if check["verdict"] != "incorrect":
                return check, None, None
            calls = [self.verifier.judge(problem, item["text"], error_id)]
            if self.secondary is not None:
                calls.append(self.secondary.judge(problem, item["text"], error_id))
            out = await asyncio.gather(*calls)
            return check, out[0], (out[1] if len(out) > 1 else None)

        scored = await asyncio.gather(*[one(item) for item in block])
        checks = [c for c, _, _ in scored]
        vers = [v for _, v, _ in scored]
        secs = [s for _, _, s in scored]
        verdicts = [c["verdict"] for c in checks]
        labels = [v["labels"] if v else None for v in vers]
        trunc = [self._truncation(item) for item in block]
        texts = [item["text"] for item in block]

        accepted_now = [i for i in range(len(block)) if verdicts[i] == "incorrect" and accepted(labels[i])]
        glog: dict[str, Any] = {"step": step, KEY: key, "source_error_id": error_id, "newman_stage": row["newman_stage"],
                                "question_group_id": row["question_group_id"], "K": len(accepted_now), "accepted": accepted_now}
        aux_scores: dict[int, float] = {}
        if len(accepted_now) >= 2:
            if self.mode == "diversity":
                aux_scores, detail = diversity_scores(texts, accepted_now, self.bleu)
                glog.update(detail)
            else:
                schedule = pair_schedule(accepted_now, self.seed, step, key)
                calls = await asyncio.gather(*[self.judge.compare(problem, texts[a], texts[b]) for a, b in schedule])
                aux_scores = normalized_win_scores(accepted_now, [(a, b, c["winner"]) for (a, b), c in zip(schedule, calls)])
                glog["pairs"] = [{"A": a, "B": b, "winner": c["winner"],
                                  "winner_index": a if c["winner"] == "A" else b if c["winner"] == "B" else None,
                                  "raw_text": c["raw_text"], "response_id": c["response_id"], "request_id": c["request_id"],
                                  "usage": c["usage"], "latency_s": c["latency_s"], "attempts": c["attempts"]}
                                 for (a, b), c in zip(schedule, calls)]
        rw = self.cfg["rewards"]
        combined = combine_group(verdicts, labels, trunc, lambda acc: aux_scores, float(rw["lambda_correct_penalty"]),
                                 float(rw["null_verdict_main_reward"]), float(rw["format"]["truncation_penalty"]))
        if combined["accepted"] != accepted_now:
            raise GroupIntegrityError("accepted set mismatch")
        glog["aux_scores"] = {str(k): v for k, v in aux_scores.items()}
        w = float(rw["auxiliary_weight"])
        out = []
        for i, item in enumerate(block):
            rec = {
                "rank": item.get("rank", 0), "local_idx": item.get("local_idx", i), "step": step, KEY: key, "group_pos": i,
                "k": item.get("k", i), "source_error_id": error_id, "newman_stage": row["newman_stage"],
                "question_group_id": row["question_group_id"], "unit_conversion_eligible": row["unit_conversion_eligible"],
                "main": combined["main"][i], "aux": combined["aux"][i], "trunc": combined["trunc"][i],
                "total": combined["main"][i] + w * combined["aux"][i] + combined["trunc"][i],
                "in_G": i in combined["accepted"], "K": combined["K"],
                "solution": item["text"], "completion_tokens": trunc[i].length, "ends_with_eos": trunc[i].ends_with_eos,
                "truncated": trunc[i].truncated, "trunc_anomaly": trunc[i].anomaly,
                "answer_check": checks[i], f"verifier_{self.role}": vers[i],
            }
            if self.secondary is not None:
                rec[f"verifier_{self.secondary_role}"] = secs[i]
            out.append(rec)
        return out, glog

    def _write_logs(self, step: int, results: list[dict[str, Any]], group_logs: list[dict[str, Any]]) -> None:
        # one scoring pass per optimizer step: a step redone after --resume replaces its earlier files
        write_jsonl(self.run_dir / "rollouts" / f"step_{step:06d}.jsonl", results)
        write_jsonl(self.run_dir / "rollouts" / f"groups_{step:06d}.jsonl", group_logs)

    def metrics(self, results: list[dict[str, Any]], group_logs: list[dict[str, Any]], elapsed: float) -> dict[str, float]:
        r_, n = self.role, len(results)
        verdicts = Counter(r["answer_check"]["verdict"] for r in results)
        judged = verdicts["correct"] + verdicts["incorrect"]
        ver = [r[f"verifier_{r_}"] for r in results if r[f"verifier_{r_}"]]
        ver_labels = [x for v in ver for x in v["labels"]]
        k = [gl["K"] for gl in group_logs]
        in_g = [r for r in results if r["in_G"]]
        fresh = [r["answer_check"] for r in results if not r["answer_check"].get("cached")]
        m = {
            "answer/null_rate": verdicts[None] / n,
            "answer/correct_rate": verdicts["correct"] / n,
            "answer/incorrect_rate": verdicts["incorrect"] / n,
            "answer/incorrect_rate_judgeable": verdicts["incorrect"] / judged if judged else 0.0,
            "answer/cache_hit_rate": 1 - len(fresh) / n,
            "answer/retry_rate": (sum(c["attempts"] - 1 for c in fresh) / len(fresh)) if fresh else 0.0,
            "answer/latency_s": (sum(c["latency_s"] for c in fresh) / len(fresh)) if fresh else 0.0,
            f"verifier_{r_}/accept_rate_incorrect": (sum(1 for v in ver if accepted(v["labels"])) / len(ver)) if ver else 0.0,
            f"verifier_{r_}/invalid_sample_rate": (sum(1 for x in ver_labels if x == "invalid") / len(ver_labels)) if ver_labels else 0.0,
            f"verifier_{r_}/sample_disagreement_rate": (sum(1 for v in ver if len(set(v["labels"])) > 1) / len(ver)) if ver else 0.0,
            f"target/success_rate_{r_}": len(in_g) / n,
            "groups/K_mean": sum(k) / len(k),
            "groups/K_ge2_rate": sum(1 for x in k if x >= 2) / len(k),
            "groups/K0_rate": sum(1 for x in k if x == 0) / len(k),
            "aux/active_rate": sum(1 for r in results if r["in_G"] and r["K"] >= 2) / n,
            "aux/raw_mean_active": (sum(r["aux"] for r in in_g if r["K"] >= 2) / max(1, sum(1 for r in in_g if r["K"] >= 2))),
            "truncation/rate": sum(1 for r in results if r["truncated"]) / n,
            "truncation/anomaly_count": float(sum(1 for r in results if r["trunc_anomaly"])),
            "reward/total_mean": sum(r["total"] for r in results) / n,
            "timing/reward_scoring_s": elapsed,
        }
        for stage in STAGE_IDS:
            sub = [r for r in results if r["newman_stage"] == stage]
            if sub:
                m[f"target_by_stage/{stage}/success_rate_{r_}"] = sum(1 for r in sub if r["in_G"]) / len(sub)
        if self.secondary is not None:
            s_ = self.secondary_role
            both = [(r[f"verifier_{r_}"], r[f"verifier_{s_}"]) for r in results if r[f"verifier_{r_}"] and r[f"verifier_{s_}"]]
            m[f"verifier_{s_}/accept_rate_incorrect"] = sum(1 for _, s in both if accepted(s["labels"])) / len(both) if both else 0.0
            m[f"verifier_{r_}{s_}/disagreement_rate_incorrect"] = (
                sum(1 for p, s in both if accepted(p["labels"]) != accepted(s["labels"])) / len(both) if both else 0.0)
        if self.mode == "diversity":
            sims = [max(v for key, v in gl["bleu_matrix"].items() if key.startswith(f"{i}|"))
                    for gl in group_logs if gl.get("bleu_matrix") for i in gl["accepted"]]
            m["diversity/max_bleu_mean"] = sum(sims) / len(sims) if sims else 0.0
            m["diversity/duplicate_rate"] = sum(1 for s in sims if s >= 0.999) / len(sims) if sims else 0.0
        else:
            pairs = [p for gl in group_logs for p in gl.get("pairs", [])]
            m["student_likeness/pairs"] = float(len(pairs))
            m["student_likeness/tie_rate"] = sum(1 for p in pairs if p["winner"] == "tie") / len(pairs) if pairs else 0.0
            m["student_likeness/A_win_rate"] = sum(1 for p in pairs if p["winner"] == "A") / len(pairs) if pairs else 0.0
        return m
