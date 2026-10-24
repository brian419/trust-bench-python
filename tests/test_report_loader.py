import json

import pytest

from report_loader import load_report


def test_load_valid_report(tmp_path):
    report = {
        "metadata": {
            "model": "gemma3:1b",
        },
        "results": [],
    }

    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    assert load_report(path) == report


def test_reject_report_that_is_not_object(tmp_path):
    path = tmp_path / "report.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON object"):
        load_report(path)


def test_reject_missing_metadata(tmp_path):
    path = tmp_path / "report.json"
    path.write_text('{"results": []}', encoding="utf-8")

    with pytest.raises(ValueError, match="metadata object"):
        load_report(path)


def test_reject_missing_results(tmp_path):
    path = tmp_path / "report.json"
    path.write_text('{"metadata": {}}', encoding="utf-8")

    with pytest.raises(ValueError, match="results list"):
        load_report(path)


def test_malformed_json_raises_decode_error(tmp_path):
    path = tmp_path / "report.json"
    path.write_text('{"metadata": ', encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_report(path)


def test_missing_file_raises_file_not_found(tmp_path):
    path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_report(path)


def test_legacy_report_without_provenance_is_loadable(tmp_path):
    report = {
        "metadata": {
            "model": "gemma3:1b",
            "timestamp": "2026-10-20T12:00:00+00:00",
        },
        "results": [],
    }

    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    assert load_report(path) == report
