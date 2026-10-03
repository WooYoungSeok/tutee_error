"""Verifiable distractor reward without any verifier (user decisions 2026-10-03).

Per rollout:
  1. gpt-5-nano (reasoning low) extracts the final answer only, no grading (prompts/answer_extract_*.txt).
  2. Literal guard (tutee_rl _norm_answer): equal to the correct answer -> no match; equal to a target distractor -> match.
  3. Otherwise a non-null answer goes to the approved distractor check (prompts/distractor_match_*.txt), target
     distractors of the condition only.
main reward: target distractor matched +1.0; anything else (correct, another wrong answer, no clear answer) -0.75.
Auxiliary terms inside G = {matched} when |G| >= 2: 0.5 x pairwise student-likeness (gpt-5-nano, low) and
0.25 x BLEU diversity (Eedi settings). Truncation -0.5 as before. No reward verifier is called or served.
OpenAI invalid_prompt refusals: 3 tries, then extraction null / no match / tie (rollouts/flagged.jsonl).
"""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from typing import Any

from tutee_rl.common import read_template, resolve
from tutee_rl.orchestrator import _norm_answer, distractor_match
from tutee_rl.rewards import diversity_scores, normalized_win_scores, pair_schedule, truncation_info, truncation_reward

from .clients import AnswerExtractor, MockAnswerExtractor
from .orchestrator import DistractorRewardOrchestrator, literal_target

CASES = ("distractor", "no_match", "literal_correct", "null")


class VerifiableDistractorOrchestrator(DistractorRewardOrchestrator):
    async def _init_clients(self) -> None:
        await super()._init_clients()  # student-likeness judge + distractor check (the verifier client is built but never called)
        cfg = self.cfg
        if cfg.get("smoke", {}).get("mock_reward_clients"):
            self.extractor = MockAnswerExtractor()
            return
        p = cfg["prompts"]
        self.extractor = AnswerExtractor(cfg["answer_check"], read_template(p["answer_extract_system"]),
                                         read_template(p["answer_extract_user"]), self.openai)

    def _weights(self) -> tuple[float, float]:
        aux = self.cfg["rewards"]["auxiliary_terms"]
        return float(aux["student_likeness"]), float(aux["diversity"])

    def describe(self) -> dict[str, Any]:
        rw = self.cfg["rewards"]
        wl, wd = self._weights()
        out: dict[str, Any] = {"mode": "student_likeness + diversity", "policy_eos_ids": sorted(self.eos_ids)}
        out["reward_variant"] = {
            "name": "verifiable distractor, no verifier (user 2026-10-03)", "distractor_match": float(rw["distractor_match_reward"]),
            "anything_else": float(rw["non_target_reward"]), "aux_weights": {"student_likeness": wl, "diversity": wd},
            "G": "target distractor matched", "literal_guard": "tutee_rl _norm_answer: correct answer -> no match, target -> match",
            "flagged_attempts": int(self.cfg["openai_client"]["flagged_attempts"]), "verifier": "not used"}
        if self.is_main:
            out["answer_extraction"] = {**self.extractor.settings(), "prompt_version": self.extractor.prompt_version,
                                        "prompts": [str(resolve(self.cfg["prompts"][k])) for k in ("answer_extract_system", "answer_extract_user")]}
            out["distractor_match"] = {**self.matcher.settings(), "prompt_version": self.matcher.prompt_version}
            out["student_likeness"] = {"model": self.cfg["student_likeness"].get("model"), "prompt_version": self.judge.prompt_version,
                                       "decoding": self.judge.decoding_record()}
            out["bleu_signature"] = str(self.bleu.get_signature())
            out["mock_reward_clients"] = bool(self.cfg.get("smoke", {}).get("mock_reward_clients"))
        return out

    def reward_funcs(self):
        def main(prompts, completions, completion_ids, **kwargs):
            return [r["main"] for r in self._score(completion_ids, kwargs)]

        def aux_student_likeness(prompts, completions, completion_ids, **kwargs):
            return [r["aux_l"] for r in self._cached(completion_ids, kwargs)]

        def aux_diversity(prompts, completions, completion_ids, **kwargs):
            return [r["aux_d"] for r in self._cached(completion_ids, kwargs)]

        def format_truncation(prompts, completions, completion_ids, **kwargs):
            return [r["trunc"] for r in self._cached(completion_ids, kwargs)]

        wl, wd = self._weights()
        return [main, aux_student_likeness, aux_diversity, format_truncation], [1.0, wl, wd, 1.0]

    @staticmethod
    def _public(r):
        return {"rank": r["rank"], "local_idx": r["local_idx"], "main": r["main"], "aux": r["aux_l"], "aux_l": r["aux_l"],
                "aux_d": r["aux_d"], "trunc": r["trunc"]}

    async def _score_group(self, block, step):
        pid = block[0]["pair_id"]
        row, priv = self.rows[pid], self.privileged[pid]
        problem = row["problem"]
        contract, targets = str(priv["AnswerContract"]), priv["TargetDistractors"]
        correct = _norm_answer(priv["CorrectAnswerText"])
        rw = self.cfg["rewards"]

        async def one(i, item):
            ctx = {"step": step, "PairId": pid, "group_pos": i, "text": item["text"]}
            ext = await self._flag_safe(
                "answer_extraction", lambda: self.extractor.extract(problem, contract, item["text"]),
                {"extracted_answer": None, "reason": "request flagged by OpenAI (invalid_prompt); no answer", "raw_text": None,
                 "response_id": None, "request_id": None, "usage": None}, ctx)
            ans = ext["extracted_answer"]
            if ans is None:
                return ext, None, "null"
            if _norm_answer(ans) and _norm_answer(ans) == correct:
                return ext, {"matched_option": None, "guard": "literal correct answer", "cached": False}, "literal_correct"
            letter = literal_target(ans, priv)
            if letter:
                return ext, {"matched_option": letter, "guard": "literal target distractor", "cached": False}, "distractor"
            match = await self._flag_safe(
                "distractor_match", lambda: self.matcher.match(problem, contract, ans, targets),
                {"matched_option": None, "reason": "request flagged by OpenAI (invalid_prompt); no match", "matched_option_dropped": None,
                 "raw_text": None, "response_id": None, "request_id": None, "usage": None}, {**ctx, "extracted_answer": ans})
            return ext, match, "distractor" if match.get("matched_option") else "no_match"

        scored = await asyncio.gather(*[one(i, item) for i, item in enumerate(block)])
        mains = [float(rw["distractor_match_reward"]) if case == "distractor" else float(rw["non_target_reward"]) for _, _, case in scored]
        trunc = [truncation_info(item["ids"], self.eos_ids, self.max_completion) for item in block]
        texts = [item["text"] for item in block]
        accepted = [i for i, (_, _, case) in enumerate(scored) if case == "distractor"]
        glog: dict[str, Any] = {"step": step, "PairId": pid, "K": len(accepted), "accepted": accepted,
                                "cases": dict(Counter(case for _, _, case in scored))}
        aux_l: dict[int, float] = {}
        aux_d: dict[int, float] = {}
        if len(accepted) >= 2:
            aux_d, detail = diversity_scores(texts, accepted, self.bleu)
            glog.update(detail)
            schedule = pair_schedule(accepted, self.seed, step, pid)
            calls = await asyncio.gather(*[self._flag_safe(
                "student_likeness", lambda a=a, b=b: self.judge.compare(problem, texts[a], texts[b]),
                {"winner": "tie", "raw_text": None, "response_id": None, "request_id": None, "usage": None},
                {"step": step, "PairId": pid, "pair": [a, b], "texts": [texts[a], texts[b]]}) for a, b in schedule])
            aux_l = normalized_win_scores(accepted, [(a, b, c["winner"]) for (a, b), c in zip(schedule, calls)])
            glog["pairs"] = [{"A": a, "B": b, "winner": c["winner"],
                              "winner_index": a if c["winner"] == "A" else b if c["winner"] == "B" else None,
                              "raw_text": c["raw_text"], "response_id": c["response_id"], "request_id": c["request_id"],
                              "usage": c["usage"], "latency_s": c["latency_s"], "attempts": c["attempts"],
                              **({"flagged": True} if c.get("flagged") else {})}
                             for (a, b), c in zip(schedule, calls)]
        glog["aux_scores"] = {"student_likeness": {str(k): v for k, v in aux_l.items()}, "diversity": {str(k): v for k, v in aux_d.items()}}
        wl, wd = self._weights()
        out = []
        for i, item in enumerate(block):
            ext, match, case = scored[i]
            al, ad = float(aux_l.get(i, 0.0)), float(aux_d.get(i, 0.0))
            tr = truncation_reward(trunc[i], float(rw["format"]["truncation_penalty"]))
            out.append({
                "rank": item["rank"], "local_idx": item["local_idx"], "step": step, "PairId": pid, "group_pos": i,
                "main": mains[i], "aux_l": al, "aux_d": ad, "trunc": tr, "total": mains[i] + wl * al + wd * ad + tr,
                "reward_case": case, "in_G": i in accepted, "K": len(accepted),
                "solution": item["text"], "completion_tokens": trunc[i].length, "ends_with_eos": trunc[i].ends_with_eos,
                "truncated": trunc[i].truncated, "trunc_anomaly": trunc[i].anomaly,
                "answer_extraction": ext, "distractor_check": match, "matched_option": (match or {}).get("matched_option"),
                "string_option_match": distractor_match(ext["extracted_answer"], priv),  # Eedi string diagnostic (correct = none)
            })
        return out, glog

    def _metrics(self, results, group_logs, elapsed):
        n = len(results)
        cases = Counter(r["reward_case"] for r in results)
        k = [gl["K"] for gl in group_logs]
        in_g = [r for r in results if r["in_G"]]
        active = [r for r in in_g if r["K"] >= 2]
        fresh = [r["answer_extraction"] for r in results if not r["answer_extraction"].get("cached")]
        pairs = [p for gl in group_logs for p in gl.get("pairs", [])]
        sims = [max(v for key, v in gl["bleu_matrix"].items() if key.startswith(f"{i}|"))
                for gl in group_logs if gl.get("bleu_matrix") for i in gl["accepted"]]
        wl, wd = self._weights()
        m = {f"reward_case/{c}_rate": cases[c] / n for c in CASES}
        m.update({
            "target/success_rate": len(in_g) / n,
            "distractor/match_rate": cases["distractor"] / n,
            "distractor/match_rate_answered": cases["distractor"] / max(1, n - cases["null"]),
            "answer/null_rate": cases["null"] / n,
            "answer/literal_correct_rate": cases["literal_correct"] / n,
            "answer/retry_rate": (sum(c["attempts"] - 1 for c in fresh) / len(fresh)) if fresh else 0.0,
            "answer/latency_s": (sum(c["latency_s"] for c in fresh) / len(fresh)) if fresh else 0.0,
            "guard/literal_target_rate": sum(1 for r in results if (r["distractor_check"] or {}).get("guard") == "literal target distractor") / n,
            "groups/K_mean": sum(k) / len(k), "groups/K0_rate": sum(1 for x in k if x == 0) / len(k),
            "groups/K_ge2_rate": sum(1 for x in k if x >= 2) / len(k),
            "aux/active_rate": len(active) / n,
            "aux/student_likeness_mean_active": sum(r["aux_l"] for r in active) / len(active) if active else 0.0,
            "aux/diversity_mean_active": sum(r["aux_d"] for r in active) / len(active) if active else 0.0,
            "student_likeness/pairs": float(len(pairs)),
            "student_likeness/tie_rate": sum(1 for p in pairs if p["winner"] == "tie") / len(pairs) if pairs else 0.0,
            "diversity/max_bleu_mean": sum(sims) / len(sims) if sims else 0.0,
            "diversity/duplicate_rate": sum(1 for s in sims if s >= 0.999) / len(sims) if sims else 0.0,
            "truncation/rate": sum(1 for r in results if r["truncated"]) / n,
            "openai/flagged_extractions": float(sum(1 for r in results if r["answer_extraction"].get("flagged"))),
            "openai/flagged_distractor_checks": float(sum(1 for r in results if (r["distractor_check"] or {}).get("flagged"))),
            "openai/flagged_likeness_pairs": float(sum(1 for p in pairs if p.get("flagged"))),
            "openai/hedged_calls": float(getattr(self, "hedged_calls", 0)),
            "reward/main_mean": sum(r["main"] for r in results) / n,
            "reward/aux_student_likeness_weighted_mean": wl * sum(r["aux_l"] for r in results) / n,
            "reward/aux_diversity_weighted_mean": wd * sum(r["aux_d"] for r in results) / n,
            "reward/total_mean": sum(r["total"] for r in results) / n,
            "timing/reward_scoring_s": elapsed,
        })
        self.hedged_calls = 0
        return m
