"""Infrastructure smoke test only: stand-ins for the three model calls.

Deterministic from a hash of the solution text, with a small random latency. They let the TRL + vLLM +
DeepSpeed + gather/broadcast path run before the real data, API key and verifier checkpoint are in place.
train.py only allows them for runs named smoke_*; their rewards mean nothing.
"""

from __future__ import annotations

import asyncio
import hashlib
import random
from typing import Any


def _h(text: str, salt: str) -> int:
    return int(hashlib.sha256((salt + "\x00" + text).encode("utf-8")).hexdigest()[:8], 16) % 100


class MockAnswerChecker:
    prompt_version = "mock"

    def settings(self) -> dict[str, Any]:
        return {"model": "MOCK"}

    async def check(self, problem: str, answer_contract: str, reference: str, solution: str) -> dict[str, Any]:
        await asyncio.sleep(random.uniform(0.2, 1.0))
        h = _h(solution, "answer")
        verdict = None if h < 10 else ("correct" if h < 30 else "incorrect")
        return {"extracted_answer": None if verdict is None else "mock", "verdict": verdict, "reason": "mock",
                "raw_text": "", "model": "MOCK", "prompt_version": "mock", "response_id": None, "request_id": None,
                "usage": None, "latency_s": 0.0, "attempts": 1, "failures": [], "cached": False}


class MockVerifier:
    def sampling(self) -> dict[str, Any]:
        return {"mock": True}

    async def judge(self, question: str, solution: str, description: str) -> dict[str, Any]:
        await asyncio.sleep(random.uniform(0.05, 0.3))
        labels = ["aligned" if _h(solution, f"v{k}") < 60 else "not_aligned" for k in range(2)]
        return {"raw": labels, "labels": labels, "finish_reasons": ["stop", "stop"], "prompt_tokens": 0, "latency_s": 0.0, "attempts": 1}


class MockJudge:
    prompt_version = "mock"

    def decoding_record(self) -> dict[str, Any]:
        return {"backend": "mock"}

    async def compare(self, question: str, solution_a: str, solution_b: str) -> dict[str, Any]:
        await asyncio.sleep(random.uniform(0.2, 1.0))
        h = _h(solution_a + "\x01" + solution_b, "judge")
        winner = "A" if h < 45 else ("B" if h < 90 else "tie")
        return {"winner": winner, "raw_text": "", "response_id": None, "request_id": None, "usage": None, "latency_s": 0.0, "attempts": 1}
