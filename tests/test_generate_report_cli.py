import json
import sys

import pytest

from generate_report import generate_text_report, main


def make_live_report():
    return {
        "metadata": {
            "model": "gemma3:1b",
            "dataset": "eval-read-reference.json",
            "timestamp": "2026-10-24T18:00:00+00:00",
            "provenance": {
                "dataset_sha256": "a" * 64,
                "primary_scoring": "normalized-exact-v1",
                "alternative_scoring": None,
                "model_options": None,
                "model_version": None,
            },
        },
        "results": [
            {
                "id": "fact_001",
                "question": "What is 2 + 2?",
                "expected": "4",
                "generated": "5",
                "status": "FAIL",
            },
        ],
    }


def test_generate_text_report(tmp_path):
    report_path = tmp_path / "evaluation.json"

    report_path.write_text(
        json.dumps(make_live_report()),
        encoding="utf-8",
    )

    output = generate_text_report(str(report_path))

    assert "TrustBench Evaluation Report" in output
    assert "Model: gemma3:1b" in output
    assert "Total cases: 1" in output
    assert "Failed: 1" in output
    assert "Generated: 5" in output


def test_generate_report_cli_prints_output(tmp_path, monkeypatch, capsys):
    report_path = tmp_path / "evaluation.json"

    report_path.write_text(
        json.dumps(make_live_report()),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["generate_report.py", str(report_path)],
    )

    main()

    output = capsys.readouterr().out

    assert "TrustBench Evaluation Report" in output
    assert "Exact-match accuracy: 0.00%" in output


def test_generate_report_cli_rejects_invalid_json(tmp_path, monkeypatch, capsys):
    report_path = tmp_path / "invalid.json"
    report_path.write_text("{invalid-json", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["generate_report.py", str(report_path)],
    )

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2
    assert "Invalid JSON report:" in capsys.readouterr().err


def test_generate_report_rejects_non_live_report(tmp_path):
    report_path = tmp_path / "consistency.json"

    report = {
        "metadata": {
            "model": "gemma3:1b",
            "repetitions": 3,
            "provenance": {
                "inputs_sha256": "a" * 64,
                "scoring_method": None,
                "prompt_format": "plain-question-v1",
            },
        },
        "results": [],
    }

    report_path.write_text(
        json.dumps(report),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires a recognized live-evaluation"):
        generate_text_report(str(report_path))


def test_generate_report_cli_saves_text_file(tmp_path, monkeypatch, capsys):
    report_path = tmp_path / "evaluation.json"
    output_path = tmp_path / "summary.txt"

    report_path.write_text(
        json.dumps(make_live_report()),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_report.py",
            str(report_path),
            "--output",
            str(output_path),
        ],
    )

    main()

    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")

    assert "TrustBench Evaluation Report" in content
    assert "Model: gemma3:1b" in content
    assert "Generated: 5" in content

    output = capsys.readouterr().out
    assert f"Report saved to: {output_path}" in output


def test_generate_report_cli_refuses_to_overwrite(tmp_path, monkeypatch, capsys):
    report_path = tmp_path / "evaluation.json"
    output_path = tmp_path / "summary.txt"

    report_path.write_text(
        json.dumps(make_live_report()),
        encoding="utf-8",
    )

    output_path.write_text(
        "Original contents",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_report.py",
            str(report_path),
            "--output",
            str(output_path),
        ],
    )

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2

    assert output_path.read_text(encoding="utf-8") == "Original contents"
    assert "Output file already exists:" in capsys.readouterr().err


def test_generate_report_cli_rejects_missing_output_directory(
    tmp_path, monkeypatch, capsys
):
    report_path = tmp_path / "evaluation.json"
    output_path = tmp_path / "missing-directory" / "summary.txt"

    report_path.write_text(
        json.dumps(make_live_report()),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_report.py",
            str(report_path),
            "--output",
            str(output_path),
        ],
    )

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2
    assert not output_path.exists()
    assert "Could not save report:" in capsys.readouterr().err


def test_generate_text_report_supports_legacy_live_report(tmp_path):
    report_path = tmp_path / "legacy.json"

    report = make_live_report()
    del report["metadata"]["provenance"]

    report_path.write_text(
        json.dumps(report),
        encoding="utf-8",
    )

    output = generate_text_report(str(report_path))

    assert "Model: gemma3:1b" in output
    assert "Dataset: eval-read-reference.json" in output
    assert "Total cases: 1" in output
    assert "Failed: 1" in output
    assert "Exact-match accuracy: 0.00%" in output


def test_generate_text_report_rejects_missing_live_metadata(tmp_path):
    report_path = tmp_path / "invalid.json"

    report = make_live_report()
    del report["metadata"]["dataset"]

    report_path.write_text(
        json.dumps(report),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="recognized live-evaluation"):
        generate_text_report(str(report_path))


def test_generate_text_report_rejects_missing_result_fields(tmp_path):
    report_path = tmp_path / "invalid-results.json"

    report = make_live_report()
    del report["results"][0]["expected"]

    report_path.write_text(
        json.dumps(report),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required fields"):
        generate_text_report(str(report_path))


def test_generate_text_report_rejects_invalid_expected_type(tmp_path):
    report_path = tmp_path / "invalid-expected.json"

    report = make_live_report()
    report["results"][0]["expected"] = 4

    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ValueError, match="field 'expected'"):
        generate_text_report(str(report_path))


def test_generate_text_report_rejects_missing_generated_response(tmp_path):
    report_path = tmp_path / "missing-generated.json"

    report = make_live_report()
    del report["results"][0]["generated"]

    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ValueError, match="string generated response"):
        generate_text_report(str(report_path))
