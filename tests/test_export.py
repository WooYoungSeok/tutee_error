"""Export: labels land on the right raw rows, raw rows are never modified."""

import json

import pytest

from errdesc.export import (
    LABEL_FIELD,
    ExportError,
    attach,
    attach_by_identity,
    labels_by_source_file,
    payload_counts,
    read_rows,
    row_key,
    write_rows,
)

INDEX = [
    {"dataset": "ds", "source_file": "data/raw/ds/f.jsonl", "source_id": "f.jsonl#0",
     "sample_id": "ds:a", "eligible": True, "exclusion_reason": ""},
    {"dataset": "ds", "source_file": "data/raw/ds/f.jsonl", "source_id": "f.jsonl#1",
     "sample_id": "ds:b", "eligible": False, "exclusion_reason": "non_error_label"},
    {"dataset": "ds", "source_file": "data/raw/ds/f.jsonl", "source_id": "f.jsonl#2",
     "sample_id": "ds:a", "eligible": True, "exclusion_reason": ""},
    {"dataset": "ds", "source_file": "data/raw/ds/f.jsonl", "source_id": "f.jsonl#3",
     "sample_id": "ds:c", "eligible": True, "exclusion_reason": ""},
]
RESULTS = {
    "ds:a": {"processing_status": "ok", "description": "Adds instead of subtracting",
             "status": "ok", "evidence_quote": "3 + 2"},
    "ds:c": {"processing_status": "json_parse_error", "description": None,
             "status": None, "evidence_quote": None},
}


def test_labels_follow_the_record_index():
    labels = labels_by_source_file(INDEX, RESULTS, "run1")["data/raw/ds/f.jsonl"]
    assert labels[0] == {
        "labeled": True, "description": "Adds instead of subtracting", "status": "ok",
        "evidence_quote": "3 + 2", "sample_id": "ds:a", "run_id": "run1",
    }
    assert labels[2] == labels[0]  # duplicate rows share one request
    assert labels[1] == {"labeled": False, "reason": "non_error_label"}
    assert labels[3]["labeled"] is False
    assert labels[3]["reason"] == "not_generated:json_parse_error"


def test_jsonl_roundtrip_skips_blank_lines_like_the_adapters(tmp_path):
    raw = tmp_path / "f.jsonl"
    rows = [{"q": "a"}, {"q": "b"}, {"q": "c"}, {"q": "d"}]
    raw.write_text("\n".join(json.dumps(r) for r in rows[:2]) + "\n\n" +
                   "\n".join(json.dumps(r) for r in rows[2:]) + "\n", encoding="utf-8")
    before = raw.read_bytes()
    read, fmt = read_rows(raw)
    assert read == rows
    labels = labels_by_source_file(INDEX, RESULTS, "run1")["data/raw/ds/f.jsonl"]
    out = attach(read, labels, "f.jsonl")
    assert read == rows  # input rows untouched
    target = tmp_path / "out" / "f.jsonl"
    write_rows(target, out, fmt)
    assert raw.read_bytes() == before
    written, _ = read_rows(target)
    assert [r["q"] for r in written] == ["a", "b", "c", "d"]
    assert written[2][LABEL_FIELD]["sample_id"] == "ds:a"
    assert payload_counts(written) == {
        "labeled:ok": 2, "not_labeled:non_error_label": 1,
        "not_labeled:not_generated:json_parse_error": 1,
    }


def test_json_list_keeps_indent_and_non_ascii(tmp_path):
    raw = tmp_path / "f.json"
    raw.write_text(json.dumps([{"q": "°C"}], ensure_ascii=False, indent=4), encoding="utf-8")
    rows, fmt = read_rows(raw)
    assert fmt == {"kind": "json", "ascii": False, "final_newline": False, "indent": 4}
    write_rows(tmp_path / "o.json", attach(rows, {0: {"labeled": False, "reason": "x"}}, "f"), fmt)
    text = (tmp_path / "o.json").read_text(encoding="utf-8")
    assert text.startswith("[\n    {") and "°C" in text


def test_row_count_mismatch_is_an_error():
    with pytest.raises(ExportError):
        attach([{"q": "a"}, {"q": "b"}], {0: {"labeled": False, "reason": "x"}}, "f")


def test_existing_label_key_is_never_overwritten():
    with pytest.raises(ExportError):
        attach([{LABEL_FIELD: "keep"}], {0: {"labeled": False, "reason": "x"}}, "f")


def test_copies_are_labeled_through_identical_rows():
    source = [{"id": 1, "p": "x"}, {"id": 2, "p": "y"}]
    labeled = attach(source, {0: {"labeled": True, "status": "ok"}, 1: {"labeled": False, "reason": "r"}}, "s")
    by_row = {row_key(r): r[LABEL_FIELD] for r in labeled}
    copies = attach_by_identity([{"p": "y", "id": 2}], by_row, "copy")
    assert copies[0][LABEL_FIELD] == {"labeled": False, "reason": "r"}
    with pytest.raises(ExportError):
        attach_by_identity([{"id": 3}], by_row, "copy")
