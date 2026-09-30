"""The served verifier (A for the RL reward, B for test evaluation) with the Newman input contract.

tutee_rl's VerifierClient is reused for everything but the prompt: one request with n samples (no fixed seed,
so the samples are independent draws), token-id prompts rendered with the verifier's own chat template (the
server cannot add a second BOS), stop ids, the retry/abort policy, and exact-match parsing. No response is cached,
so A and B never share results and the n samples are never copies of one response.
`judge(question, solution, error_id)` takes the target error-type id; the stage follows from it.
"""

from __future__ import annotations

import asyncio
from typing import Any, Mapping

from tutee_rl.clients import VerifierClient

from . import verifier_format
from .taxonomy import Taxonomy


class NewmanVerifierClient(VerifierClient):
    def __init__(self, cfg: Mapping[str, Any], prompt: Mapping[str, str], taxonomy: Taxonomy, tokenizer: Any,
                 stop_token_ids: list[int], repetition_penalty: float, client: Any):
        # The parent constructor loads the descriptive-verifier contract; set its attributes with the Newman one.
        self.vc = verifier_format  # parse_prediction: exact `aligned` / `not_aligned`, else `invalid`
        self.cfg = cfg
        self.prompt = prompt
        self.taxonomy = taxonomy
        self.tokenizer = tokenizer
        self.stop_token_ids = stop_token_ids
        self.repetition_penalty = float(repetition_penalty)
        self.client = client
        self.sem = asyncio.Semaphore(int(cfg["concurrency"]))

    def prompt_ids(self, question: str, solution: str, error_id: str) -> list[int]:
        messages = verifier_format.verifier_messages(self.prompt, self.taxonomy, question, solution, error_id)
        text = verifier_format.generation_prompt(self.tokenizer, messages)
        return self.tokenizer(text, add_special_tokens=False)["input_ids"]


def verifier_stop_and_penalty(checkpoint: str, cfg: Mapping[str, Any]) -> tuple[Any, list[int], float]:
    """Tokenizer, stop ids (tokenizer eos + generation_config eos, as HF generate stops) and repetition penalty."""
    from transformers import AutoTokenizer, GenerationConfig

    tok = AutoTokenizer.from_pretrained(checkpoint, trust_remote_code=True)
    stop = {int(tok.eos_token_id)} if tok.eos_token_id is not None else set()
    try:
        gen = GenerationConfig.from_pretrained(checkpoint)
        eos = gen.eos_token_id
        stop.update([eos] if isinstance(eos, int) else list(eos or []))
    except Exception:  # noqa: BLE001 - checkpoint without generation_config.json
        pass
    rep = cfg.get("repetition_penalty", 1.0)
    if rep == "from_generation_config":
        raise ValueError("verifier.repetition_penalty is fixed by the plan (8.2: 1.0); set a number")
    return tok, sorted(stop), float(rep)


def make_verifier(cfg: Mapping[str, Any], prompt: Mapping[str, str], taxonomy: Taxonomy) -> NewmanVerifierClient:
    from openai import AsyncOpenAI

    tok, stop, rep = verifier_stop_and_penalty(cfg["checkpoint"], cfg)
    http = AsyncOpenAI(base_url=cfg["base_url"], api_key="EMPTY", max_retries=0)
    return NewmanVerifierClient(cfg, prompt, taxonomy, tok, stop, rep, http)
