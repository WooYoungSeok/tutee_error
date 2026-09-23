"""Output schema validation, including the null / status edge cases."""

import json

from errdesc.validate import evidence_found_in_solution, parse_output


def test_valid_output():
    result = parse_output(
        json.dumps({"description": "Mixes up total and part in ratio",
                    "evidence_quote": "3 x 4 = 12", "status": "ok"})
    )
    assert result["processing_status"] == "ok"
    assert result["parsed"]["status"] == "ok"


def test_real_null_description_is_valid():
    result = parse_output(
        '{"description": null, "evidence_quote": "x", "status": "ambiguous"}'
    )
    assert result["processing_status"] == "ok"
    assert result["parsed"]["description"] is None


def test_string_null_is_rejected():
    result = parse_output('{"description": "null", "evidence_quote": "x", "status": "ok"}')
    assert result["processing_status"] == "schema_invalid"
    assert "null" in result["error"]


def test_piped_status_string_is_rejected():
    result = parse_output(
        '{"description": "d", "evidence_quote": "x", "status": "ok | ambiguous | label_conflict"}'
    )
    assert result["processing_status"] == "schema_invalid"


def test_unknown_status_is_rejected():
    result = parse_output('{"description": "d", "evidence_quote": "x", "status": "fine"}')
    assert result["processing_status"] == "schema_invalid"


def test_missing_key_is_rejected():
    result = parse_output('{"description": "d", "status": "ok"}')
    assert result["processing_status"] == "schema_invalid"
    assert "evidence_quote" in result["error"]


def test_malformed_json():
    result = parse_output("not json at all")
    assert result["processing_status"] == "json_parse_error"
    assert result["parsed"] is None


def test_fenced_json_is_recovered_and_flagged():
    result = parse_output(
        '```json\n{"description": "d", "evidence_quote": "x", "status": "ok"}\n```'
    )
    assert result["processing_status"] == "ok"
    assert result["repaired"] is True


def test_empty_response():
    assert parse_output("")["processing_status"] == "empty_response"
    assert parse_output(None)["processing_status"] == "empty_response"


def test_extra_keys_are_recorded_but_allowed():
    result = parse_output(
        '{"description": "d", "evidence_quote": "x", "status": "ok", "confidence": 0.9}'
    )
    assert result["processing_status"] == "ok"
    assert result["extra_keys"] == ["confidence"]


def test_evidence_lookup_is_whitespace_tolerant():
    assert evidence_found_in_solution("3 x 4 = 12", "so  3 x 4 = 12\nthen ...")
    assert not evidence_found_in_solution("5 x 4 = 20", "so 3 x 4 = 12")
    assert not evidence_found_in_solution("", "anything")
