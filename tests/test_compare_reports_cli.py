import json
import sys
import pytest
from compare_reports import compare_report_files, main


def make_report(results):
    return {
        "metadata": {
            "model": "gemma3:1b",
            "provenance": {
                "dataset_sha256": "a" * 64,
                "primary_scoring": "normalized-exact-v1",
                "alternative_scoring": None,
                "model_options": None,
                "model_version": None,
            },
        },
        "results": results,
    }


def test_compare_report_files(tmp_path):
    previous_path = tmp_path / "previous.json"
    current_path = tmp_path / "current.json"

    previous = make_report(
        [
            {"id": "fact_001", "status": "FAIL"},
            {"id": "fact_002", "status": "PASS"},
        ]
    )

    current = make_report(
        [
            {"id": "fact_001", "status": "PASS"},
            {"id": "fact_002", "status": "FAIL"},
        ]
    )

    previous_path.write_text(
        json.dumps(previous),
        encoding="utf-8",
    )
    current_path.write_text(
        json.dumps(current),
        encoding="utf-8",
    )

    result = compare_report_files(
        str(previous_path),
        str(current_path),
    )

    assert result["summary"]["improvements"] == 1
    assert result["summary"]["regressions"] == 1
    assert result["compatibility"]["status"] == "PARTIAL_MATCH"


def test_cli_prints_comparison_summary(tmp_path, monkeypatch, capsys):
    previous_path = tmp_path / "previous.json"
    current_path = tmp_path / "current.json"

    previous = make_report(
        [
            {"id": "fact_001", "status": "FAIL"},
            {"id": "fact_002", "status": "PASS"},
        ]
    )

    current = make_report(
        [
            {"id": "fact_001", "status": "PASS"},
            {"id": "fact_002", "status": "FAIL"},
        ]
    )

    previous_path.write_text(json.dumps(previous), encoding="utf-8")
    current_path.write_text(json.dumps(current), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["compare_reports.py", str(previous_path), str(current_path)],
    )

    main()

    output = capsys.readouterr().out

    assert "TrustBench Report Comparison" in output
    assert "Total unique cases: 2" in output
    assert "Improvements: 1" in output
    assert "Regressions: 1" in output


def test_cli_prints_empty_comparison(tmp_path, monkeypatch, capsys):
    previous_path = tmp_path / "previous.json"
    current_path = tmp_path / "current.json"

    report = make_report([])

    previous_path.write_text(json.dumps(report), encoding="utf-8")
    current_path.write_text(json.dumps(report), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["compare_reports.py", str(previous_path), str(current_path)],
    )

    main()

    output = capsys.readouterr().out

    assert "Total unique cases: 0" in output
    assert "Improvements: 0" in output
    assert "Regressions: 0" in output


def test_cli_prints_compatibility_warnings(tmp_path, monkeypatch, capsys):
    previous_path = tmp_path / "previous.json"
    current_path = tmp_path / "current.json"

    report = make_report(
        [
            {"id": "fact_001", "status": "PASS"},
        ]
    )

    previous_path.write_text(json.dumps(report), encoding="utf-8")
    current_path.write_text(json.dumps(report), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["compare_reports.py", str(previous_path), str(current_path)],
    )

    main()

    output = capsys.readouterr().out

    assert "Compatibility: PARTIAL_MATCH" in output
    assert "Compatibility warnings:" in output
    assert "Generation options are not fully recorded." in output
    assert "One or both model versions are unknown." in output


def test_cli_prints_individual_case_changes(tmp_path, monkeypatch, capsys):
    previous_path = tmp_path / "previous.json"
    current_path = tmp_path / "current.json"

    previous = make_report(
        [
            {"id": "fact_001", "status": "FAIL"},
            {"id": "fact_002", "status": "PASS"},
            {"id": "fact_003", "status": "PASS"},
        ]
    )

    current = make_report(
        [
            {"id": "fact_001", "status": "PASS"},
            {"id": "fact_002", "status": "FAIL"},
            {"id": "fact_003", "status": "PASS"},
        ]
    )

    previous_path.write_text(json.dumps(previous), encoding="utf-8")
    current_path.write_text(json.dumps(current), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["compare_reports.py", str(previous_path), str(current_path)],
    )

    main()

    output = capsys.readouterr().out

    assert "Case changes:" in output
    assert "fact_001: FAIL -> PASS (IMPROVEMENT)" in output
    assert "fact_002: PASS -> FAIL (REGRESSION)" in output
    assert "fact_003:" not in output


def test_cli_rejects_missing_file(tmp_path, monkeypatch, capsys):
    missing_path = tmp_path / "missing.json"
    current_path = tmp_path / "current.json"

    current_path.write_text(
        json.dumps(make_report([])),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["compare_reports.py", str(missing_path), str(current_path)],
    )

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2

    output = capsys.readouterr().err
    assert "Report file not found:" in output
    assert "Traceback" not in output


def test_cli_rejects_invalid_json(tmp_path, monkeypatch, capsys):
    previous_path = tmp_path / "previous.json"
    current_path = tmp_path / "current.json"

    previous_path.write_text("{invalid-json", encoding="utf-8")
    current_path.write_text(
        json.dumps(make_report([])),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["compare_reports.py", str(previous_path), str(current_path)],
    )

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2

    output = capsys.readouterr().err
    assert "Invalid JSON report:" in output
    assert "Traceback" not in output


def test_cli_rejects_incompatible_reports(tmp_path, monkeypatch, capsys):
    previous_path = tmp_path / "previous.json"
    current_path = tmp_path / "current.json"

    previous = make_report(
        [
            {"id": "fact_001", "status": "PASS"},
        ]
    )

    current = make_report(
        [
            {"id": "fact_001", "status": "PASS"},
        ]
    )

    current["metadata"]["provenance"]["dataset_sha256"] = "b" * 64

    previous_path.write_text(json.dumps(previous), encoding="utf-8")
    current_path.write_text(json.dumps(current), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["compare_reports.py", str(previous_path), str(current_path)],
    )

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2

    output = capsys.readouterr().err
    assert "Reports cannot be compared:" in output
    assert "Traceback" not in output


def test_cli_rejects_malformed_report(tmp_path, monkeypatch, capsys):
    previous_path = tmp_path / "previous.json"
    current_path = tmp_path / "current.json"

    previous_path.write_text(
        json.dumps({"metadata": {}, "results": "invalid"}),
        encoding="utf-8",
    )

    current_path.write_text(
        json.dumps(make_report([])),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["compare_reports.py", str(previous_path), str(current_path)],
    )

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2

    output = capsys.readouterr().err
    assert "Report must contain a results list." in output
    assert "Traceback" not in output
