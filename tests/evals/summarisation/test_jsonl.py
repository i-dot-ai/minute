from __future__ import annotations

import json

from evals.summarisation.src.jsonl import write_jsonl


def test_write_jsonl_single_record(tmp_path):
    output_path = tmp_path / "output.jsonl"
    records = [{"id": 1, "text": "hello"}]

    write_jsonl(output_path, records)

    assert output_path.exists()
    lines = output_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    assert json.loads(lines[0]) == {"id": 1, "text": "hello"}


def test_write_jsonl_multiple_records(tmp_path):
    output_path = tmp_path / "output.jsonl"
    records = [
        {"id": 1, "text": "first"},
        {"id": 2, "text": "second"},
        {"id": 3, "text": "third"},
    ]

    write_jsonl(output_path, records)

    lines = output_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3
    assert json.loads(lines[0]) == {"id": 1, "text": "first"}
    assert json.loads(lines[1]) == {"id": 2, "text": "second"}
    assert json.loads(lines[2]) == {"id": 3, "text": "third"}


def test_write_jsonl_creates_parent_directory(tmp_path):
    output_path = tmp_path / "nested" / "dir" / "output.jsonl"
    records = [{"id": 1}]

    write_jsonl(output_path, records)

    assert output_path.exists()
    assert output_path.parent.exists()


def test_write_jsonl_appends_to_existing_file(tmp_path):
    output_path = tmp_path / "output.jsonl"
    output_path.write_bytes(b'{"id": 0}\n')

    records = [{"id": 1}, {"id": 2}]
    write_jsonl(output_path, records)

    lines = output_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3
    assert json.loads(lines[0]) == {"id": 0}
    assert json.loads(lines[1]) == {"id": 1}
    assert json.loads(lines[2]) == {"id": 2}


def test_write_jsonl_empty_records(tmp_path):
    output_path = tmp_path / "output.jsonl"

    write_jsonl(output_path, [])

    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == ""


def test_write_jsonl_complex_data(tmp_path):
    output_path = tmp_path / "output.jsonl"
    records = [
        {
            "id": 1,
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "bool": True,
            "null": None,
        }
    ]

    write_jsonl(output_path, records)

    lines = output_path.read_text(encoding="utf-8").strip().split("\n")
    parsed = json.loads(lines[0])
    assert parsed["nested"]["key"] == "value"
    assert parsed["list"] == [1, 2, 3]
    assert parsed["bool"] is True
    assert parsed["null"] is None


def test_write_jsonl_unicode_content(tmp_path):
    output_path = tmp_path / "output.jsonl"
    records = [{"text": "Hello 世界 café"}]

    write_jsonl(output_path, records)

    lines = output_path.read_text(encoding="utf-8").strip().split("\n")
    parsed = json.loads(lines[0])
    assert parsed["text"] == "Hello 世界 café"
