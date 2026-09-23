"""Runner behaviour without network: resume, retries, truncation, fatal errors."""

import json

import pytest

from errdesc.mock import MockClient, make_mock_call
from errdesc.runner import FatalAPIError, GenerationSettings, build_request, classify_error, run_batch, run_one

TEMPLATE = "Q:{question}\nR:{incorrect_solution}\nA:{source_error_label}"
PROMPT_HASH = "p" * 64

RECORDS = [
    {
        "sample_id": f"ds:{i:04d}",
        "dataset": "ds",
        "split": "dev",
        "question": f"question {i}",
        "incorrect_solution": f"solution {i}",
        "source_error_label": "some label",
    }
    for i in range(4)
]

SETTINGS = GenerationSettings(model="test-model", concurrency=1, max_retries=3)


def test_request_contains_only_the_three_inputs():
    payload = build_request("rendered prompt", SETTINGS)
    assert payload["model"] == "test-model"
    assert payload["input"][0]["content"][0]["text"] == "rendered prompt"
    assert "temperature" not in payload  # unset parameters are not sent
    assert "reasoning" not in payload
    assert "text" not in payload


def test_optional_parameters_are_only_sent_when_set():
    settings = GenerationSettings(
        model="m", temperature=0.2, reasoning_effort="low", response_format_json=True
    )
    payload = build_request("x", settings)
    assert payload["temperature"] == 0.2
    assert payload["reasoning"] == {"effort": "low"}
    assert payload["text"] == {"format": {"type": "json_object"}}


def test_mock_run_writes_raw_rows(tmp_path):
    raw = tmp_path / "raw.jsonl"
    results = run_batch(
        MockClient(), RECORDS, TEMPLATE, PROMPT_HASH, "v1", SETTINGS, raw, call=make_mock_call()
    )
    assert len(results) == 4
    assert all(r["processing_status"] == "ok" for r in results)
    lines = raw.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 4
    stored = json.loads(lines[0])
    assert stored["parsed"]["status"] == "ok"
    assert stored["response_id"].startswith("resp_mock")


def test_resume_skips_completed_requests(tmp_path):
    raw = tmp_path / "raw.jsonl"
    calls = []

    def counting_call(prompt_text, index):
        calls.append(index)
        return {}

    run_batch(
        MockClient(), RECORDS, TEMPLATE, PROMPT_HASH, "v1", SETTINGS, raw,
        call=make_mock_call(counting_call),
    )
    assert len(calls) == 4

    calls.clear()
    results = run_batch(
        MockClient(), RECORDS, TEMPLATE, PROMPT_HASH, "v1", SETTINGS, raw,
        call=make_mock_call(counting_call),
    )
    assert calls == []  # nothing re-sent
    assert all(r["reused_from_previous_run"] for r in results)
    assert len(raw.read_text(encoding="utf-8").strip().splitlines()) == 4


def test_changed_settings_start_a_new_request(tmp_path):
    raw = tmp_path / "raw.jsonl"
    calls = []
    run_batch(
        MockClient(), RECORDS[:1], TEMPLATE, PROMPT_HASH, "v1", SETTINGS, raw,
        call=make_mock_call(lambda text, i: calls.append(i)),
    )
    other = GenerationSettings(model="other-model", concurrency=1)
    run_batch(
        MockClient(), RECORDS[:1], TEMPLATE, PROMPT_HASH, "v1", other, raw,
        call=make_mock_call(lambda text, i: calls.append(i)),
    )
    assert len(calls) == 2


def test_changed_prompt_hash_starts_a_new_request(tmp_path):
    raw = tmp_path / "raw.jsonl"
    calls = []
    run_batch(
        MockClient(), RECORDS[:1], TEMPLATE, PROMPT_HASH, "v1", SETTINGS, raw,
        call=make_mock_call(lambda text, i: calls.append(i)),
    )
    run_batch(
        MockClient(), RECORDS[:1], TEMPLATE, "q" * 64, "v2", SETTINGS, raw,
        call=make_mock_call(lambda text, i: calls.append(i)),
    )
    assert len(calls) == 2


def test_truncated_response_is_not_success_and_is_not_cached(tmp_path):
    raw = tmp_path / "raw.jsonl"
    truncating = make_mock_call(
        lambda text, i: {"response_status": "incomplete", "incomplete_reason": "max_output_tokens"}
    )
    results = run_batch(
        MockClient(), RECORDS[:1], TEMPLATE, PROMPT_HASH, "v1", SETTINGS, raw, call=truncating
    )
    assert results[0]["processing_status"] == "truncated"
    assert results[0]["parsed"] is None

    calls = []
    run_batch(
        MockClient(), RECORDS[:1], TEMPLATE, PROMPT_HASH, "v1", SETTINGS, raw,
        call=make_mock_call(lambda text, i: calls.append(i)),
    )
    assert calls == [1]  # retried on the next run, not treated as done


def test_malformed_json_is_recorded_as_processing_status(tmp_path):
    raw = tmp_path / "raw.jsonl"
    results = run_batch(
        MockClient(), RECORDS[:1], TEMPLATE, PROMPT_HASH, "v1", SETTINGS, raw,
        call=make_mock_call(lambda text, i: {"output_text": "I cannot answer."}),
    )
    assert results[0]["processing_status"] == "json_parse_error"
    assert results[0]["raw_output_text"] == "I cannot answer."


def test_model_status_is_kept_separate_from_processing_status(tmp_path):
    raw = tmp_path / "raw.jsonl"
    payload = json.dumps(
        {"description": None, "evidence_quote": "x", "status": "label_conflict"}
    )
    results = run_batch(
        MockClient(), RECORDS[:1], TEMPLATE, PROMPT_HASH, "v1", SETTINGS, raw,
        call=make_mock_call(lambda text, i: {"output_text": payload}),
    )
    assert results[0]["processing_status"] == "ok"
    assert results[0]["parsed"]["status"] == "label_conflict"


class _RateLimit(Exception):
    status_code = 429


class _AuthError(Exception):
    status_code = 401


_AuthError.__name__ = "AuthenticationError"
_RateLimit.__name__ = "RateLimitError"


def test_transient_errors_are_retried(tmp_path, monkeypatch):
    monkeypatch.setattr("errdesc.runner.time.sleep", lambda *_: None)
    raw = tmp_path / "raw.jsonl"
    attempts = {"n": 0}

    def flaky(text, index):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise _RateLimit("slow down")
        return {}

    results = run_batch(
        MockClient(), RECORDS[:1], TEMPLATE, PROMPT_HASH, "v1", SETTINGS, raw,
        call=make_mock_call(flaky),
    )
    assert results[0]["processing_status"] == "ok"
    assert len(results[0]["attempts"]) == 2
    assert results[0]["attempts"][0]["error_kind"] == "RateLimitError"


def test_auth_errors_fail_immediately(tmp_path):
    raw = tmp_path / "raw.jsonl"

    def failing(text, index):
        raise _AuthError("bad key")

    with pytest.raises(FatalAPIError):
        run_batch(
            MockClient(), RECORDS[:1], TEMPLATE, PROMPT_HASH, "v1", SETTINGS, raw,
            call=make_mock_call(failing),
        )


def test_error_classification():
    assert classify_error(_RateLimit("x")) == (True, "RateLimitError")
    assert classify_error(_AuthError("x"))[0] is False


def test_persistent_failure_is_recorded_not_raised(tmp_path, monkeypatch):
    monkeypatch.setattr("errdesc.runner.time.sleep", lambda *_: None)
    raw = tmp_path / "raw.jsonl"

    def always_rate_limited(text, index):
        raise _RateLimit("still slow")

    results = run_batch(
        MockClient(), RECORDS[:1], TEMPLATE, PROMPT_HASH, "v1", SETTINGS, raw,
        call=make_mock_call(always_rate_limited),
    )
    assert results[0]["processing_status"] == "api_error"
    assert len(results[0]["attempts"]) == SETTINGS.max_retries


def test_run_one_records_attempt_metadata():
    row = run_one(
        MockClient(), RECORDS[0], TEMPLATE, PROMPT_HASH, "v1", SETTINGS, call=make_mock_call()
    )
    assert row["prompt_hash"] == PROMPT_HASH
    assert row["input_hash"] and row["request_key"]
    assert row["usage"]["output_tokens"] == 40
    assert row["attempts"][0]["request_id"].startswith("req_mock")
    assert row["generation"]["model"] == "test-model"
