"""Eedi GRPO reward with a verifiable distractor term (user decisions 2026-10-02).

Per rollout:
  1. Eedi answer judge, unchanged (gpt-5-nano, reasoning low): extracted answer + verdict against the correct answer.
  2. Literal guard: an extracted answer that equals the correct answer after tutee_rl's light normalisation is
     correct; one that equals a target distractor is incorrect and matched. Other equivalences are gpt-5-nano's.
  3. Incorrect answers only: gpt-5-nano distractor check against the condition's target distractors
     (prompts/distractor_match_*.txt), unless the literal guard already matched.
  4. Reward verifier (2 samples) on every incorrect answer.
main reward:
  correct, or no clear final answer (null)                                -0.75
  incorrect and equal to a target distractor                               1.0   (no verifier needed)
  incorrect, no target distractor, reward verifier 2/2 `aligned`          0.5
  incorrect, no target distractor, verifier not passed                    0.0
Truncation -0.5 and 0.5 x student-likeness inside G = {main > 0}, as in the Eedi run.
OpenAI refusals (HTTP 400 invalid_prompt, as in the Newman run): the request is sent up to
openai_client.flagged_attempts times, then the answer check is a null verdict (-0.75), the distractor check no match
and a student-likeness pair a tie; each case goes to rollouts/flagged.jsonl. Other errors keep tutee_rl's policy.
"""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from typing import Any, Callable, Mapping

from tutee_rl.clients import RewardExecutionError
from tutee_rl.common import append_jsonl, read_template, resolve
from tutee_rl.orchestrator import RewardOrchestrator, _norm_answer, distractor_match
from tutee_rl.rewards import normalized_win_scores, pair_schedule, truncation_info, truncation_reward, verifier_accepts

from .clients import DistractorMatcher, MockDistractorMatcher

CASES = ("correct", "null", "distractor", "verifier_pass", "incorrect_rejected")
FLAGGED_CODE = "invalid_prompt"


def is_flagged(exc: BaseException | None) -> bool:
    while exc is not None:
        if getattr(exc, "code", None) == FLAGGED_CODE or (type(exc).__name__ == "BadRequestError" and FLAGGED_CODE in str(exc)):
            return True
        exc = exc.__cause__
    return False


def guard_correct(check: Mapping[str, Any], priv: Mapping[str, Any]) -> dict[str, Any]:
    """Literal correct answer -> correct, whatever the judge said (its verdict stays in judge_verdict)."""
    out = {**check, "judge_verdict": check.get("verdict"), "guard": None}
    ans = check.get("extracted_answer")
    if ans is not None and _norm_answer(ans) and _norm_answer(ans) == _norm_answer(priv["CorrectAnswerText"]) and check["verdict"] != "correct":
        out.update(verdict="correct", guard="literal correct answer")
    return out


def literal_target(extracted: str | None, priv: Mapping[str, Any]) -> str | None:
    if extracted is None or not _norm_answer(extracted):
        return None
    hits = [t["option"] for t in priv["TargetDistractors"] if _norm_answer(extracted) == _norm_answer(t["text"])]
    return hits[0] if hits else None


def main_reward(verdict: str | None, matched: str | None, labels, rw: Mapping[str, Any]) -> tuple[float, str]:
    if verdict is None:
        return float(rw["null_verdict_main_reward"]), "null"
    if verdict == "correct":
        return -float(rw["lambda_correct_penalty"]), "correct"
    if verdict != "incorrect":
        raise ValueError(f"unexpected verdict {verdict!r}")
    if matched:
        return float(rw["distractor_match_reward"]), "distractor"
    if labels is None:
        raise ValueError("an incorrect answer needs verifier labels")
    if verifier_accepts(labels):
        return float(rw["verifier_pass_reward"]), "verifier_pass"
    return 0.0, "incorrect_rejected"


class DistractorRewardOrchestrator(RewardOrchestrator):
    async def _init_clients(self) -> None:
        await super()._init_clients()  # Eedi answer judge, verifier, student-likeness judge (or their mocks)
        cfg = self.cfg
        if cfg.get("smoke", {}).get("mock_reward_clients"):
            self.matcher = MockDistractorMatcher()
            return
        p = cfg["prompts"]
        self.matcher = DistractorMatcher(cfg["answer_check"], read_template(p["distractor_match_system"]),
                                         read_template(p["distractor_match_user"]), self.openai)

    def describe(self) -> dict[str, Any]:
        out = super().describe()
        rw = self.cfg["rewards"]
        out["reward_variant"] = {
            "name": "distractor (user 2026-10-02)", "correct": -float(rw["lambda_correct_penalty"]),
            "null": float(rw["null_verdict_main_reward"]), "distractor_match": float(rw["distractor_match_reward"]),
            "verifier_pass_without_match": float(rw["verifier_pass_reward"]), "G": "main reward > 0",
            "literal_guard": "tutee_rl _norm_answer equality with the correct answer / a target distractor",
            "flagged_attempts": int(self.cfg["openai_client"]["flagged_attempts"])}
        if self.is_main:
            out["distractor_match"] = {**self.matcher.settings(), "prompt_version": self.matcher.prompt_version,
                                       "prompts": [str(resolve(self.cfg["prompts"][k])) for k in ("distractor_match_system", "distractor_match_user")]}
        return out

    async def _hedged(self, call: Callable[[], Any]):
        """User request 2026-10-03 (speed): if a call has not answered after openai_client.hedge_after_s, send the
        same request once more and use whichever answers first (the other is cancelled). Same prompt, input and
        settings; only the long tail of single slow calls (one 58 s call held a whole step in the smoke) is cut."""
        delay = self.cfg["openai_client"].get("hedge_after_s")
        if not delay:
            return await call()
        first = asyncio.ensure_future(call())
        done, _ = await asyncio.wait({first}, timeout=float(delay))
        if done:
            return first.result()
        self.hedged_calls = getattr(self, "hedged_calls", 0) + 1
        second = asyncio.ensure_future(call())
        pending, error = {first, second}, None
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                if task.exception() is None:
                    for other in pending:
                        other.cancel()
                    return task.result()
                error = error or task.exception()
        raise error

    async def _flag_safe(self, role: str, call: Callable[[], Any], fallback: Mapping[str, Any], context: Mapping[str, Any]):
        attempts = int(self.cfg["openai_client"]["flagged_attempts"])
        error = ""
        for _ in range(attempts):
            try:
                return await self._hedged(call)
            except RewardExecutionError as exc:
                if not is_flagged(exc):
                    raise
                error = str(exc)[:500]
        if self.is_main:
            append_jsonl(self.run_dir / "rollouts" / "flagged.jsonl",
                         [{"role": role, "attempts": attempts, "error": error, "at": time.strftime("%Y-%m-%dT%H:%M:%S"), **context}])
        return {**fallback, "flagged": True, "attempts": attempts, "latency_s": 0.0, "cached": False, "failures": [error]}

    async def _score_group(self, block, step):
        pid = block[0]["pair_id"]
        row, priv = self.rows[pid], self.privileged[pid]
        problem, condition = row["problem"], row["target_misconception_description"]
        contract, targets = str(priv["AnswerContract"]), priv["TargetDistractors"]

        async def one(i, item):
            ctx = {"step": step, "PairId": pid, "group_pos": i, "text": item["text"]}
            check = await self._flag_safe(
                "answer_check", lambda: self.answer.check(problem, contract, str(priv["CorrectAnswerText"]), item["text"]),
                {"extracted_answer": None, "verdict": None, "reason": "request flagged by OpenAI (invalid_prompt); unjudgeable",
                 "raw_text": None, "model": self.cfg["answer_check"]["model"], "response_id": None, "request_id": None, "usage": None}, ctx)
            check = guard_correct(check, priv)
            match = None
            if check["verdict"] == "incorrect":
                letter = literal_target(check["extracted_answer"], priv)
                if letter:
                    match = {"matched_option": letter, "guard": "literal target distractor", "cached": False}
                else:
                    match = await self._flag_safe(
                        "distractor_match", lambda: self.matcher.match(problem, contract, check["extracted_answer"], targets),
                        {"matched_option": None, "reason": "request flagged by OpenAI (invalid_prompt); no match",
                         "matched_option_dropped": None, "raw_text": None, "response_id": None, "request_id": None, "usage": None},
                        {**ctx, "extracted_answer": check["extracted_answer"]})
            ver = await self.verifier.judge(problem, item["text"], condition) if check["verdict"] == "incorrect" else None
            return check, match, ver

        scored = await asyncio.gather(*[one(i, item) for i, item in enumerate(block)])
        rw = self.cfg["rewards"]
        mains, cases = zip(*[main_reward(c["verdict"], (m or {}).get("matched_option"), v["labels"] if v else None, rw)
                             for c, m, v in scored])
        trunc = [truncation_info(item["ids"], self.eos_ids, self.max_completion) for item in block]
        texts = [item["text"] for item in block]

        accepted = [i for i in range(len(block)) if mains[i] > 0]
        glog: dict[str, Any] = {"step": step, "PairId": pid, "K": len(accepted), "accepted": accepted, "cases": dict(Counter(cases))}
        aux_scores: dict[int, float] = {}
        if len(accepted) >= 2:
            schedule = pair_schedule(accepted, self.seed, step, pid)
            calls = await asyncio.gather(*[self._flag_safe(
                "student_likeness", lambda a=a, b=b: self.judge.compare(problem, texts[a], texts[b]),
                {"winner": "tie", "raw_text": None, "response_id": None, "request_id": None, "usage": None},
                {"step": step, "PairId": pid, "pair": [a, b], "texts": [texts[a], texts[b]]}) for a, b in schedule])
            aux_scores = normalized_win_scores(accepted, [(a, b, c["winner"]) for (a, b), c in zip(schedule, calls)])
            glog["pairs"] = [{"A": a, "B": b, "winner": c["winner"],
                              "winner_index": a if c["winner"] == "A" else b if c["winner"] == "B" else None,
                              "raw_text": c["raw_text"], "response_id": c["response_id"], "request_id": c["request_id"],
                              "usage": c["usage"], "latency_s": c["latency_s"], "attempts": c["attempts"],
                              **({"flagged": True} if c.get("flagged") else {})}
                             for (a, b), c in zip(schedule, calls)]
        glog["aux_scores"] = {str(k): v for k, v in aux_scores.items()}
        w = float(rw["auxiliary_weight"])
        out = []
        for i, item in enumerate(block):
            check, match, ver = scored[i]
            aux = float(aux_scores.get(i, 0.0))
            tr = truncation_reward(trunc[i], float(rw["format"]["truncation_penalty"]))
            out.append({
                "rank": item["rank"], "local_idx": item["local_idx"], "step": step, "PairId": pid, "group_pos": i,
                "main": mains[i], "aux": aux, "trunc": tr, "total": mains[i] + w * aux + tr, "reward_case": cases[i],
                "in_G": i in accepted, "K": len(accepted),
                "solution": item["text"], "completion_tokens": trunc[i].length, "ends_with_eos": trunc[i].ends_with_eos,
                "truncated": trunc[i].truncated, "trunc_anomaly": trunc[i].anomaly,
                "answer_check": check, "distractor_check": match, "verifier": ver,
                "matched_option": (match or {}).get("matched_option"),
                "distractor_match": distractor_match(check["extracted_answer"], priv),  # Eedi string diagnostic
            })
        return out, glog

    def _metrics(self, results, group_logs, elapsed):
        m = super()._metrics(results, group_logs, elapsed)
        n = len(results)
        inc = [r for r in results if r["answer_check"]["verdict"] == "incorrect"]
        cases = Counter(r["reward_case"] for r in results)
        for c in CASES:
            m[f"reward_case/{c}_rate"] = cases[c] / n
        m["distractor/match_rate"] = cases["distractor"] / n
        m["distractor/match_rate_incorrect"] = cases["distractor"] / len(inc) if inc else 0.0
        matched = [r for r in inc if r["matched_option"]]
        m["distractor/verifier_accept_rate_matched"] = (
            sum(1 for r in matched if r["verifier"] and verifier_accepts(r["verifier"]["labels"])) / len(matched) if matched else 0.0)
        m["guard/correct_override_rate"] = sum(1 for r in results if r["answer_check"].get("guard")) / n
        m["guard/literal_target_rate_incorrect"] = (
            sum(1 for r in inc if (r["distractor_check"] or {}).get("guard")) / len(inc) if inc else 0.0)
        m["openai/flagged_answer_checks"] = float(sum(1 for r in results if r["answer_check"].get("flagged")))
        m["openai/flagged_distractor_checks"] = float(sum(1 for r in inc if (r["distractor_check"] or {}).get("flagged")))
        m["openai/flagged_likeness_pairs"] = float(sum(1 for gl in group_logs for p in gl.get("pairs", []) if p.get("flagged")))
        m["openai/hedged_calls"], self.hedged_calls = float(getattr(self, "hedged_calls", 0)), 0
        return m
