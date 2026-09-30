"""Input contracts and what the clients actually send (verifier prompt ids, reasoning effort low)."""

from __future__ import annotations

import asyncio
import json

from newman.common import load_config, read_template, resolve
from newman.taxonomy import Taxonomy
from newman.verifier_format import (
    build_messages,
    load_student_template,
    load_verifier_prompt,
    parse_prediction,
    student_messages,
    verifier_messages,
)

TAX = Taxonomy.load(resolve("configs/taxonomy.yaml"))
PROMPT = load_verifier_prompt("prompts/verifier_system.txt", "prompts/verifier_user.txt")


def test_verifier_message_carries_the_target_condition_only():
    rec = {"question": "Q {solution} \\(x\\)", "solution": "S", "target_error_id": "eic.operator_error", "target": "not_aligned",
           "anchor_error_id": "eic.calculation_error"}
    msgs = build_messages(PROMPT, TAX, rec, with_target=True)
    user = msgs[1]["content"]
    c = TAX.condition("eic.operator_error")
    assert user.startswith("Question:\nQ {solution} \\(x\\)\n\nIncorrect solution:\nS\n")      # single-pass substitution
    assert f"Problem-solving stage (Newman's Error Analysis):\n{TAX.framework}\nSpecified stage: {c['stage_name']}\n{c['stage_definition']}" in user
    assert "one of four" not in user   # user 2026-10-01: no "one of the four stages" sentence
    assert f"Error type:\n{c['error_name']}\n{c['error_definition']}" in user
    assert user.endswith(c["error_definition"])
    assert "Calculation Error" not in user                                                   # the anchor's own label never leaks
    assert msgs[2] == {"role": "assistant", "content": "not_aligned"}
    assert msgs[0]["content"].endswith("Respond with exactly one of: aligned, not_aligned.")


def test_missing_definition_line_is_left_out():
    rec = {"question": "Q", "solution": "S", "target_error_id": "stepwise.misunderstanding_of_a_question", "target": "aligned"}
    user = build_messages(PROMPT, TAX, rec, with_target=False)[1]["content"]
    assert user.endswith("Error type:\nMisunderstanding of a question") and "None" not in user
    template = load_student_template("prompts/student.txt")
    system = student_messages(template, TAX, {"source_error_id": "stepwise.calculation_error_easily_solved_by_a_calculator",
                                              "question": "Q"})[0]["content"]
    assert system.endswith("Error type: Calculation error easily solved by a calculator") and "Error-type definition" not in system


def test_exact_match_parser():
    assert parse_prediction(" aligned\n") == "aligned"
    assert parse_prediction("not_aligned") == "not_aligned"
    assert parse_prediction("aligned.") == "invalid"
    assert parse_prediction("The answer is aligned") == "invalid"


def test_student_input():
    template = load_student_template("prompts/student.txt")
    msgs = student_messages(template, TAX, {"source_error_id": "mathclean.logic_error", "question": "How many apples?"})
    assert msgs[1] == {"role": "user", "content": "How many apples?"}
    assert "Specified stage: Transformation\n" in msgs[0]["content"] and TAX.framework in msgs[0]["content"]
    assert "At the specified problem-solving stage, write an incorrect solution" in msgs[0]["content"]
    assert "Error type: Logic error\nError-type definition: Logic errors included" in msgs[0]["content"]
    assert "{" not in msgs[0]["content"]


class FakeTokenizer:
    eos_token_id = 0

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        return "".join(f"<{m['role']}>{m['content']}" for m in messages) + ("<assistant>" if add_generation_prompt else "")

    def __call__(self, text, add_special_tokens=False):
        return {"input_ids": [ord(ch) for ch in text]}


class FakeCompletions:
    def __init__(self):
        self.calls = []

    async def create(self, **kw):
        self.calls.append(kw)

        class C:
            def __init__(self, i, t):
                self.index, self.text, self.finish_reason = i, t, "stop"

        class R:
            choices = [C(1, "not_aligned"), C(0, "aligned")]
        return R()


def test_verifier_client_sends_the_newman_prompt_and_parses_both_samples():
    from newman.clients import NewmanVerifierClient

    cfg = load_config("configs/rl_common.yaml")["verifier"]
    fake = type("Client", (), {"completions": FakeCompletions()})()
    client = NewmanVerifierClient(cfg, PROMPT, TAX, FakeTokenizer(), [0], 1.0, fake)
    out = asyncio.run(client.judge("What is 2+2?", "2+2=5", "eic.calculation_error"))
    assert out["labels"] == ["aligned", "not_aligned"]
    call = fake.completions.calls[0]
    text = "".join(chr(i) for i in call["prompt"])
    assert TAX.condition("eic.calculation_error")["error_definition"] in text
    assert call["n"] == 2 and call["temperature"] == 0.6 and call["extra_body"]["repetition_penalty"] == 1.0


class FakeRaw:
    headers = {"x-request-id": "req"}

    def __init__(self, text):
        self.text = text

    def parse(self):
        class R:
            id, status, incomplete_details, usage = "resp", "completed", None, None
        r = R()
        r.output_text = self.text
        return r


class FakeResponses:
    def __init__(self, text):
        self.payloads, self.text = [], text
        self.with_raw_response = self

    async def create(self, timeout=None, **payload):
        self.payloads.append(payload)
        return FakeRaw(self.text)


def test_both_gpt5_nano_roles_send_reasoning_effort_low():
    from tutee_rl.clients import AnswerChecker, PairwiseJudge

    cfg = load_config("configs/student_likeness.yaml")
    p = cfg["prompts"]
    answers = type("C", (), {})()
    answers.responses = FakeResponses(json.dumps({"extracted_answer": "5", "verdict": "incorrect", "reason": "r"}))
    checker = AnswerChecker(cfg["answer_check"], read_template(p["answer_judge_system"]), read_template(p["answer_judge_user"]), answers)
    res = asyncio.run(checker.check("Q", "NUMBER", "4", "S"))
    assert res["verdict"] == "incorrect"
    assert answers.responses.payloads[0]["reasoning"] == {"effort": "low"}
    assert answers.responses.payloads[0]["model"] == "gpt-5-nano" and "temperature" not in answers.responses.payloads[0]

    judge_client = type("C", (), {})()
    judge_client.responses = FakeResponses(json.dumps({"winner": "tie"}))
    examples = json.loads(resolve(cfg["student_likeness"]["examples"]).read_text())["examples"]
    judge = PairwiseJudge(cfg["student_likeness"], read_template(p["student_likeness_system"]), read_template(p["student_likeness_user"]),
                          examples, judge_client)
    assert asyncio.run(judge.compare("Q", "A text", "B text"))["winner"] == "tie"
    assert judge_client.responses.payloads[0]["reasoning"] == {"effort": "low"}
    assert "temperature" not in judge_client.responses.payloads[0]
