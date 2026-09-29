"""TRL adapter: one scoring pass per rollout batch, exposed as three reward functions.

TRL (1.14) calls every reward function on every rank with that rank's slice of the batch and then
gathers the rewards; advantages are computed over consecutive blocks of `num_generations`. Group-level
rewards (BLEU / pairwise judge inside G) need the whole group, so the first reward function gathers
all ranks' completions, rank 0 scores them (network calls run concurrently on a background event loop),
and the per-rollout results are broadcast back. The other two reward functions read the cached result.

reward functions (TRL reward_weights = [1, auxiliary_weight, 1]):
  main                 b_i
  aux_<mode>           raw auxiliary score in [0, 1] (0 outside G or when K < 2)
  format_truncation    -truncation_penalty when the completion hit the limit without EOS
"""

from __future__ import annotations

import asyncio
import re
import threading
import time
import traceback
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .clients import AnswerChecker, PairwiseJudge, RewardExecutionError, VerifierClient
from .common import hash_obj, read_jsonl, read_template, resolve, write_jsonl
from .rewards import (
    combine_group,
    diversity_scores,
    make_bleu,
    normalized_win_scores,
    pair_schedule,
    truncation_info,
)


class GroupIntegrityError(RuntimeError):
    pass


def _dist():
    import torch.distributed as dist

    return dist if dist.is_available() and dist.is_initialized() else None


def _norm_answer(text: str | None) -> str:
    if text is None:
        return ""
    t = re.sub(r"\\[()\[\]]", "", str(text))
    t = re.sub(r"\\mathrm\{~?([^}]*)\}", r"\1", t)
    t = t.replace("\\,", "").replace("~", "")
    return re.sub(r"\s+", "", t).lower().strip("$")


def distractor_match(extracted: str | None, priv: Mapping[str, Any]) -> str:
    """Diagnostic only (never a reward gate): which option set the extracted answer equals after light normalisation."""
    if extracted is None:
        return "unjudgeable"
    ans = _norm_answer(extracted)
    for key, name in (("TargetDistractors", "target"), ("OtherLabeledDistractors", "other_labeled"), ("UnlabeledDistractors", "unlabeled")):
        for item in priv.get(key) or []:
            text = item.get("text") if isinstance(item, Mapping) else item
            if ans and ans == _norm_answer(text):
                return name
    return "none"


def policy_eos_ids(tokenizer: Any, model_name_or_path: str) -> set[int]:
    ids: set[int] = set()
    if tokenizer.eos_token_id is not None:
        ids.add(int(tokenizer.eos_token_id))
    try:
        from transformers import GenerationConfig

        gen = GenerationConfig.from_pretrained(model_name_or_path)
        eos = gen.eos_token_id
        ids.update([eos] if isinstance(eos, int) else list(eos or []))
    except Exception:  # noqa: BLE001 - model without generation_config.json
        pass
    return ids


class RewardOrchestrator:
    def __init__(self, cfg: Mapping[str, Any], policy_tokenizer: Any, run_dir: Path, is_main: bool):
        self.cfg = cfg
        self.mode = cfg["rewards"]["auxiliary_reward"]
        self.num_generations = int(cfg["generation"]["num_generations"])
        self.max_completion = int(cfg["generation"]["max_completion_tokens"])
        self.tokenizer = policy_tokenizer
        self.eos_ids = policy_eos_ids(policy_tokenizer, cfg["policy"]["model"])
        self.run_dir = Path(run_dir)
        self.is_main = is_main
        self.seed = int(cfg["seed"])
        self._last: tuple[str, list[dict[str, Any]]] | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        if is_main:
            self._init_main()

    # --- setup (rank 0 only) -------------------------------------------------

    def _init_main(self) -> None:
        cfg = self.cfg
        prepared = resolve(cfg["paths"]["prepared_dir"])
        self.privileged = {r["PairId"]: r for r in read_jsonl(prepared / "privileged.jsonl")}
        self.rows = {}
        for split in ("train", "test"):
            path = prepared / f"{split}.jsonl"
            if path.exists():
                self.rows.update({r["PairId"]: r for r in read_jsonl(path)})
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, name="reward-loop", daemon=True).start()
        self._run(self._init_clients())
        self.bleu = make_bleu(**{k: cfg["diversity"][k] for k in ("smooth_method", "effective_order", "tokenize", "lowercase")})

    async def _init_clients(self) -> None:
        cfg = self.cfg
        if cfg.get("smoke", {}).get("mock_reward_clients"):
            from .mock import MockAnswerChecker, MockJudge, MockVerifier

            self.answer, self.verifier = MockAnswerChecker(), MockVerifier()
            self.judge = MockJudge() if self.mode == "student_likeness" else None
            return

        from openai import AsyncOpenAI
        from transformers import AutoTokenizer, GenerationConfig

        p = cfg["prompts"]
        ac = cfg["answer_check"]
        self.openai = AsyncOpenAI(max_retries=0, timeout=float(ac["request_timeout_s"]))
        self.answer = AnswerChecker(ac, read_template(p["answer_judge_system"]), read_template(p["answer_judge_user"]), self.openai)

        vcfg = cfg["verifier"]
        vtok = AutoTokenizer.from_pretrained(vcfg["checkpoint"], trust_remote_code=True)
        stop = {int(vtok.eos_token_id)} if vtok.eos_token_id is not None else set()
        try:
            vgen = GenerationConfig.from_pretrained(vcfg["checkpoint"])
        except Exception:  # noqa: BLE001 - checkpoint without generation_config.json (HF generate uses 1.0)
            vgen = None
        if vgen is not None:
            eos = vgen.eos_token_id
            stop.update([eos] if isinstance(eos, int) else list(eos or []))
        rep = vcfg.get("repetition_penalty", "from_generation_config")
        if rep == "from_generation_config":
            rep = float(getattr(vgen, "repetition_penalty", None) or 1.0)
        vprompt = {"system": resolve(p["verifier_system"]).read_text(encoding="utf-8"),
                   "user": resolve(p["verifier_user"]).read_text(encoding="utf-8"), "ablation": "none"}
        self.verifier_client_http = AsyncOpenAI(base_url=vcfg["base_url"], api_key="EMPTY", max_retries=0)
        self.verifier = VerifierClient(vcfg, vprompt, vtok, sorted(stop), float(rep), self.verifier_client_http)

        self.judge = None
        if self.mode == "student_likeness":
            import json

            sl = cfg["student_likeness"]
            examples = json.loads(resolve(sl["examples"]).read_text(encoding="utf-8"))["examples"]
            client = self.openai if sl["backend"] == "openai" else AsyncOpenAI(base_url=sl["base_url"], api_key="EMPTY", max_retries=0)
            self.judge = PairwiseJudge(sl, read_template(p["student_likeness_system"]), read_template(p["student_likeness_user"]), examples, client)

    def _run(self, coro):
        assert self.loop is not None
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()

    def describe(self) -> dict[str, Any]:
        """Settings recorded in the run metadata."""
        out: dict[str, Any] = {"mode": self.mode, "policy_eos_ids": sorted(self.eos_ids)}
        if self.is_main:
            out["answer_check"] = {**self.answer.settings(), "prompt_version": self.answer.prompt_version}
            out["verifier"] = {"checkpoint": self.cfg["verifier"]["checkpoint"], "sampling": self.verifier.sampling()}
            out["mock_reward_clients"] = bool(self.cfg.get("smoke", {}).get("mock_reward_clients"))
            out["bleu_signature"] = str(self.bleu.get_signature())
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
    def _fingerprint(completion_ids: Sequence[Sequence[int]], pair_ids: Sequence[str]) -> str:
        return hash_obj({"ids": [list(map(int, x)) for x in completion_ids], "pairs": list(pair_ids)})

    def _cached(self, completion_ids, kwargs) -> list[dict[str, Any]]:
        fp = self._fingerprint(completion_ids, kwargs["PairId"])
        if self._last is None or self._last[0] != fp:
            raise RuntimeError("reward cache miss: `main` must run first on the same batch")
        return self._last[1]

    def _score(self, completion_ids, kwargs) -> list[dict[str, Any]]:
        pair_ids = list(kwargs["PairId"])
        state = kwargs.get("trainer_state")
        step = int(getattr(state, "global_step", 0) or 0)
        log_metric = kwargs.get("log_metric")
        dist = _dist()
        rank = dist.get_rank() if dist else 0

        texts = self.tokenizer.batch_decode(completion_ids, skip_special_tokens=True)
        local = [{"rank": rank, "local_idx": i, "pair_id": pair_ids[i], "ids": list(map(int, completion_ids[i])), "text": texts[i].strip()}
                 for i in range(len(pair_ids))]
        if dist:
            gathered: list[Any] = [None] * dist.get_world_size()
            dist.all_gather_object(gathered, local)
            items = [x for part in gathered for x in part]
        else:
            items = local

        payload: list[Any] = [None]
        if self.is_main:
            try:
                results, metrics = self._score_global(items, step)
                payload = [{"ok": True, "results": results, "metrics": metrics}]
            except Exception as exc:  # noqa: BLE001 - every rank must learn about the failure
                traceback.print_exc()
                payload = [{"ok": False, "error": f"{type(exc).__name__}: {exc}"}]
        if dist:
            dist.broadcast_object_list(payload, src=0)
        outcome = payload[0]
        if not outcome["ok"]:
            raise RewardExecutionError(f"reward scoring aborted this rollout batch: {outcome['error']}")
        mine = [r for r in outcome["results"] if r["rank"] == rank]
        mine.sort(key=lambda r: r["local_idx"])
        if len(mine) != len(local):
            raise GroupIntegrityError("broadcast results do not match the local batch")
        if self.is_main and log_metric is not None:
            for name, value in outcome["metrics"].items():
                log_metric(name, value)
        self._last = (self._fingerprint(completion_ids, pair_ids), mine)
        return mine

    # --- scoring (rank 0) ----------------------------------------------------

    def _score_global(self, items: list[dict[str, Any]], step: int) -> tuple[list[dict[str, Any]], dict[str, float]]:
        g = self.num_generations
        if len(items) % g:
            raise GroupIntegrityError(f"{len(items)} completions is not a multiple of num_generations={g}")
        groups = [items[i:i + g] for i in range(0, len(items), g)]
        seen: set[str] = set()
        for block in groups:
            pids = {x["pair_id"] for x in block}
            if len(pids) != 1:
                raise GroupIntegrityError(f"a block of {g} consecutive completions mixes PairIds {sorted(pids)}")
            pid = next(iter(pids))
            if pid in seen:
                raise GroupIntegrityError(f"PairId {pid} appears in two groups of one batch")
            if pid not in self.privileged or pid not in self.rows:
                raise GroupIntegrityError(f"PairId {pid} has no prepared row / privileged annotation")
            seen.add(pid)
        started = time.monotonic()
        scored = self._run(self._score_groups(groups, step))
        elapsed = time.monotonic() - started
        results = [r for group_rows, _ in scored for r in group_rows]
        group_logs = [glog for _, glog in scored]
        self._write_logs(step, results, group_logs)
        return [self._public(r) for r in results], self._metrics(results, group_logs, elapsed)

    async def _score_groups(self, groups: list[list[dict[str, Any]]], step: int) -> list[tuple[list[dict[str, Any]], dict[str, Any]]]:
        return await asyncio.gather(*[self._score_group(block, step) for block in groups])

    async def _score_group(self, block: list[dict[str, Any]], step: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        pid = block[0]["pair_id"]
        row, priv = self.rows[pid], self.privileged[pid]
        problem, condition = row["problem"], row["target_misconception_description"]

        async def one(item):
            check = await self.answer.check(problem, str(priv["AnswerContract"]), str(priv["CorrectAnswerText"]), item["text"])
            verdict = None if check["verdict"] is None else check["verdict"]
            ver = await self.verifier.judge(problem, item["text"], condition) if verdict == "incorrect" else None
            return check, ver

        pairs_out = await asyncio.gather(*[one(item) for item in block])
        checks = [c for c, _ in pairs_out]
        vers = [v for _, v in pairs_out]
        verdicts = [c["verdict"] for c in checks]
        labels = [v["labels"] if v else None for v in vers]
        trunc = [truncation_info(item["ids"], self.eos_ids, self.max_completion) for item in block]
        texts = [item["text"] for item in block]

        accepted_now = [i for i in range(len(block)) if verdicts[i] == "incorrect" and labels[i] and all(x == "aligned" for x in labels[i])]
        glog: dict[str, Any] = {"step": step, "PairId": pid, "K": len(accepted_now), "accepted": accepted_now}
        aux_scores: dict[int, float] = {}
        if len(accepted_now) >= 2:
            if self.mode == "diversity":
                aux_scores, detail = diversity_scores(texts, accepted_now, self.bleu)
                glog.update(detail)
            else:
                schedule = pair_schedule(accepted_now, self.seed, step, pid)
                calls = await asyncio.gather(*[self.judge.compare(problem, texts[a], texts[b]) for a, b in schedule])
                outcomes = [(a, b, c["winner"]) for (a, b), c in zip(schedule, calls)]
                aux_scores = normalized_win_scores(accepted_now, outcomes)
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
            out.append({
                "rank": item["rank"], "local_idx": item["local_idx"], "step": step, "PairId": pid, "group_pos": i,
                "main": combined["main"][i], "aux": combined["aux"][i], "trunc": combined["trunc"][i],
                "total": combined["main"][i] + w * combined["aux"][i] + combined["trunc"][i],
                "in_G": i in combined["accepted"], "K": combined["K"],
                "solution": item["text"], "completion_tokens": trunc[i].length, "ends_with_eos": trunc[i].ends_with_eos,
                "truncated": trunc[i].truncated, "trunc_anomaly": trunc[i].anomaly,
                "answer_check": checks[i], "verifier": vers[i],
                "distractor_match": distractor_match(checks[i]["extracted_answer"], priv),
            })
        return out, glog

    @staticmethod
    def _public(r: dict[str, Any]) -> dict[str, Any]:
        return {k: r[k] for k in ("rank", "local_idx", "main", "aux", "trunc")}

    def _write_logs(self, step: int, results: list[dict[str, Any]], group_logs: list[dict[str, Any]]) -> None:
        # one scoring pass per optimizer step: a step redone after --resume replaces its earlier files
        write_jsonl(self.run_dir / "rollouts" / f"step_{step:06d}.jsonl", results)
        write_jsonl(self.run_dir / "rollouts" / f"groups_{step:06d}.jsonl", group_logs)

    def _metrics(self, results: list[dict[str, Any]], group_logs: list[dict[str, Any]], elapsed: float) -> dict[str, float]:
        n = len(results)
        verdicts = Counter(r["answer_check"]["verdict"] for r in results)
        judged = verdicts["correct"] + verdicts["incorrect"]
        ver = [r["verifier"] for r in results if r["verifier"]]
        ver_labels = [x for v in ver for x in v["labels"]]
        k = [gl["K"] for gl in group_logs]
        in_g = [r for r in results if r["in_G"]]
        match = Counter(r["distractor_match"] for r in results if r["answer_check"]["verdict"] == "incorrect")
        n_inc = max(1, verdicts["incorrect"])
        fresh = [r["answer_check"] for r in results if not r["answer_check"].get("cached")]
        m = {
            "answer/null_rate": verdicts[None] / n,
            "answer/correct_rate": verdicts["correct"] / n,
            "answer/incorrect_rate": verdicts["incorrect"] / n,
            "answer/incorrect_rate_judgeable": verdicts["incorrect"] / judged if judged else 0.0,
            "answer/cache_hit_rate": 1 - len(fresh) / n,
            "answer/retry_rate": (sum(c["attempts"] - 1 for c in fresh) / len(fresh)) if fresh else 0.0,
            "answer/latency_s": (sum(c["latency_s"] for c in fresh) / len(fresh)) if fresh else 0.0,
            "verifier/accept_rate_incorrect": (sum(1 for v in ver if all(x == "aligned" for x in v["labels"])) / len(ver)) if ver else 0.0,
            "verifier/invalid_sample_rate": (sum(1 for x in ver_labels if x == "invalid") / len(ver_labels)) if ver_labels else 0.0,
            "verifier/sample_disagreement_rate": (sum(1 for v in ver if len(set(v["labels"])) > 1) / len(ver)) if ver else 0.0,
            "target/success_rate": len(in_g) / n,
            "groups/K_mean": sum(k) / len(k),
            "groups/K_ge2_rate": sum(1 for x in k if x >= 2) / len(k),
            "groups/K0_rate": sum(1 for x in k if x == 0) / len(k),
            "aux/active_rate": sum(1 for r in results if r["in_G"] and r["K"] >= 2) / n,
            "aux/raw_mean_active": (sum(r["aux"] for r in in_g if r["K"] >= 2) / max(1, sum(1 for r in in_g if r["K"] >= 2))),
            "truncation/rate": sum(1 for r in results if r["truncated"]) / n,
            "truncation/anomaly_count": float(sum(1 for r in results if r["trunc_anomaly"])),
            "distractor/target_match_rate_incorrect": match["target"] / n_inc,
            "distractor/other_labeled_match_rate_incorrect": match["other_labeled"] / n_inc,
            "distractor/unlabeled_match_rate_incorrect": match["unlabeled"] / n_inc,
            "distractor/no_match_rate_incorrect": match["none"] / n_inc,
            "reward/total_mean": sum(r["total"] for r in results) / n,
            "timing/reward_scoring_s": elapsed,
        }
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
