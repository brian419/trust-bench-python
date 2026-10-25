from hashlib import sha256
from json import dumps

from pytest import raises

from consistency_report_reader import load_verified_report


def write_report(tmp_path, content):
    report_path = tmp_path / "consistency.json"
    raw_data = dumps(content).encode("utf-8")
    report_path.write_bytes(raw_data)

    expected_hash = sha256(raw_data).hexdigest()

    return report_path, expected_hash


def test_valid_report(tmp_path):
    original = {
        "metadata": {"model": "gemma3:1b"},
        "results": [],
    }

    report_path, expected_hash = write_report(tmp_path, original)

    loaded = load_verified_report(report_path, expected_hash)

    assert loaded == original


def test_modified_report_rejected(tmp_path):
    original = {
        "metadata": {"model": "gemma3:1b"},
        "results": [],
    }

    report_path, expected_hash = write_report(tmp_path, original)

    report_path.write_text(
        '{"metadata": {"model": "different"}, "results": []}',
        encoding="utf-8",
    )

    with raises(ValueError, match="SHA-256 mismatch"):
        load_verified_report(report_path, expected_hash)


def test_invalid_report_structure(tmp_path):
    report_path, expected_hash = write_report(
        tmp_path,
        {"metadata": {}, "results": "not a list"},
    )

    with raises(ValueError, match="results must be a list"):
        load_verified_report(report_path, expected_hash)
