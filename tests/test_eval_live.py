import json
import pytest
import hashlib
import platform
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from eval_live import main
from pathlib import Path


def test_live_evaluation_all_pass(tmp_path, monkeypatch, capsys):
    data = [
        {
            "id": "test_001",
            "question": "What is the capital of France?",
            "expected": "Paris",
        },
        {"id": "test_002", "question": "What is 6 multiplied by 2?", "expected": "12"},
    ]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    with patch(
        "eval_live.generate_response", side_effect=["Paris", "12"]
    ) as mock_generate:
        report = main()

    results = report["results"]

    output = capsys.readouterr().out

    assert "Passed: 2" in output
    assert "Failed: 0" in output
    assert "Errors: 0" in output
    assert "Accuracy: 100.0" in output
    assert mock_generate.call_count == 2

    assert len(results) == 2

    assert results[0]["id"] == "test_001"
    assert results[0]["generated"] == "Paris"
    assert results[0]["status"] == "PASS"

    assert results[1]["id"] == "test_002"
    assert results[1]["generated"] == "12"
    assert results[1]["status"] == "PASS"

    assert report["metadata"]["model"] == "gemma3:1b"
    assert report["metadata"]["dataset"] == "eval-read-live.json"

    assert report["summary"]["passed"] == 2
    assert report["summary"]["failed"] == 0
    assert report["summary"]["errors"] == 0
    assert report["summary"]["accuracy"] == 100.0

    for result in results:
        assert "duration_seconds" in result
        assert isinstance(result["duration_seconds"], float)
        assert result["duration_seconds"] >= 0

    reports_dir = tmp_path / "reports"
    report_files = list(reports_dir.glob("evaluation-*.json"))

    assert len(report_files) == 1

    with report_files[0].open("r", encoding="utf-8") as file:
        saved_report = json.load(file)

    assert saved_report == report


def test_live_evaluation_mixed_results(tmp_path, monkeypatch, capsys):
    data = [
        {
            "id": "test_001",
            "question": "What is the capital of France?",
            "expected": "Paris",
        },
        {"id": "test_002", "question": "What is 6 multiplied by 2?", "expected": "12"},
    ]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    with patch(
        "eval_live.generate_response", side_effect=["London", "12"]
    ) as mock_generate:
        report = main()

    results = report["results"]

    output = capsys.readouterr().out

    assert "Passed: 1" in output
    assert "Failed: 1" in output
    assert "Errors: 0" in output
    assert "Accuracy: 50.0" in output
    assert mock_generate.call_count == 2

    assert len(results) == 2

    assert results[0]["id"] == "test_001"
    assert results[0]["expected"] == "Paris"
    assert results[0]["generated"] == "London"
    assert results[0]["status"] == "FAIL"

    assert results[1]["id"] == "test_002"
    assert results[1]["generated"] == "12"
    assert results[1]["status"] == "PASS"


def test_live_evaluation_connection_error(tmp_path, monkeypatch, capsys):
    data = [
        {
            "id": "test_001",
            "question": "What is the capital of France?",
            "expected": "Paris",
        },
        {"id": "test_002", "question": "What is 6 multiplied by 2?", "expected": "12"},
    ]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    with patch(
        "eval_live.generate_response",
        side_effect=[URLError("Connection refused"), "12"],
    ) as mock_generate:
        report = main()

    results = report["results"]

    output = capsys.readouterr().out

    assert "Result: ERROR" in output
    assert "Network error: Connection refused" in output
    assert "Passed: 1" in output
    assert "Failed: 0" in output
    assert "Errors: 1" in output
    assert "Accuracy: 100.0" in output
    assert mock_generate.call_count == 2

    assert len(results) == 2

    assert results[0]["id"] == "test_001"
    assert results[0]["generated"] is None
    assert results[0]["status"] == "ERROR"
    assert results[0]["error"] == "Network error: Connection refused"

    assert results[1]["id"] == "test_002"
    assert results[1]["generated"] == "12"
    assert results[1]["status"] == "PASS"

    assert "duration_seconds" in results[0]
    assert isinstance(results[0]["duration_seconds"], float)
    assert results[0]["duration_seconds"] >= 0


def test_live_evaluation_all_errors(tmp_path, monkeypatch, capsys):
    data = [
        {
            "id": "test_001",
            "question": "What is the capital of France?",
            "expected": "Paris",
        },
        {"id": "test_002", "question": "What is 6 multiplied by 2?", "expected": "12"},
    ]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    with patch(
        "eval_live.generate_response",
        side_effect=[URLError("Connection refused"), URLError("Connection refused")],
    ) as mock_generate:
        main()

    output = capsys.readouterr().out

    assert "Passed: 0" in output
    assert "Failed: 0" in output
    assert "Errors: 2" in output
    assert "Accuracy: N/A" in output
    assert output.count("Result: ERROR") == 2
    assert mock_generate.call_count == 2


def test_live_evaluation_invalid_dataset(tmp_path, monkeypatch, capsys):
    data = [{"id": "test_001", "question": "What is the capital of France?"}]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    with patch("eval_live.generate_response") as mock_generate:
        with pytest.raises(SystemExit) as error:
            main()

    output = capsys.readouterr().out

    assert error.value.code == 1
    assert "Missing required field 'expected'." in output
    mock_generate.assert_not_called()


def test_live_evaluation_http_error(tmp_path, monkeypatch, capsys):
    data = [
        {
            "id": "test_001",
            "question": "What is the capital of France?",
            "expected": "Paris",
        },
        {"id": "test_002", "question": "What is 6 multiplied by 2?", "expected": "12"},
    ]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    fake_error = HTTPError(
        url="http://localhost:11434/api/generate",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None,
    )

    with patch(
        "eval_live.generate_response", side_effect=[fake_error, "12"]
    ) as mock_generate:
        report = main()

    results = report["results"]

    output = capsys.readouterr().out

    assert "HTTP error: 404" in output
    assert "Passed: 1" in output
    assert "Failed: 0" in output
    assert "Errors: 1" in output
    assert "Accuracy: 100.0" in output
    assert mock_generate.call_count == 2

    assert len(results) == 2

    assert results[0]["id"] == "test_001"
    assert results[0]["generated"] is None
    assert results[0]["status"] == "ERROR"
    assert results[0]["error"] == "HTTP error: 404"

    assert results[1]["id"] == "test_002"
    assert results[1]["generated"] == "12"
    assert results[1]["status"] == "PASS"

    assert "duration_seconds" in results[0]
    assert isinstance(results[0]["duration_seconds"], float)
    assert results[0]["duration_seconds"] >= 0


def test_live_evaluation_timeout(tmp_path, monkeypatch, capsys):
    data = [
        {
            "id": "test_001",
            "question": "What is the capital of France?",
            "expected": "Paris",
        },
        {"id": "test_002", "question": "What is 6 multiplied by 2?", "expected": "12"},
    ]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    with patch(
        "eval_live.generate_response", side_effect=[TimeoutError("Timed out"), "12"]
    ) as mock_generate:
        report = main()

    results = report["results"]

    output = capsys.readouterr().out

    assert "Request timed out" in output
    assert "Passed: 1" in output
    assert "Failed: 0" in output
    assert "Errors: 1" in output
    assert "Accuracy: 100.0" in output
    assert mock_generate.call_count == 2

    assert len(results) == 2

    assert results[0]["id"] == "test_001"
    assert results[0]["generated"] is None
    assert results[0]["status"] == "ERROR"
    assert results[0]["error"] == "Request timed out"

    assert results[1]["id"] == "test_002"
    assert results[1]["generated"] == "12"
    assert results[1]["status"] == "PASS"

    assert "duration_seconds" in results[0]
    assert isinstance(results[0]["duration_seconds"], float)
    assert results[0]["duration_seconds"] >= 0


def test_live_evaluation_missing_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    with patch("eval_live.generate_response") as mock_generate:
        with pytest.raises(SystemExit) as error:
            main()

    output = capsys.readouterr().out

    assert error.value.code == 1
    assert "No such file or directory" in output
    mock_generate.assert_not_called()


def test_live_evaluation_malformed_json(tmp_path, monkeypatch, capsys):
    dataset_file = tmp_path / "eval-read-live.json"

    dataset_file.write_text('{"id": "test_001" "question": "Hello"}')

    monkeypatch.chdir(tmp_path)

    with patch("eval_live.generate_response") as mock_generate:
        with pytest.raises(SystemExit) as error:
            main()

    output = capsys.readouterr().out

    assert error.value.code == 1
    assert "Expecting ',' delimiter" in output
    mock_generate.assert_not_called()


def test_live_evaluation_wrapped_timeout(tmp_path, monkeypatch, capsys):
    data = [
        {
            "id": "test_001",
            "question": "What is the capital of France?",
            "expected": "Paris",
        },
        {"id": "test_002", "question": "What is 6 multiplied by 2?", "expected": "12"},
    ]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    wrapped_timeout = URLError(TimeoutError("timed out"))

    with patch(
        "eval_live.generate_response", side_effect=[wrapped_timeout, "12"]
    ) as mock_generate:
        report = main()

    results = report["results"]

    output = capsys.readouterr().out

    assert "Request timed out" in output
    assert "Passed: 1" in output
    assert "Failed: 0" in output
    assert "Errors: 1" in output
    assert "Accuracy: 100.0" in output
    assert mock_generate.call_count == 2

    assert len(results) == 2

    assert results[0]["id"] == "test_001"
    assert results[0]["generated"] is None
    assert results[0]["status"] == "ERROR"
    assert results[0]["error"] == "Request timed out"

    assert results[1]["id"] == "test_002"
    assert results[1]["generated"] == "12"
    assert results[1]["status"] == "PASS"

    assert "duration_seconds" in results[0]
    assert isinstance(results[0]["duration_seconds"], float)
    assert results[0]["duration_seconds"] >= 0


def test_multiple_reports_preserved(tmp_path, monkeypatch):
    data = [
        {
            "id": "test_001",
            "question": "What is the capital of France?",
            "expected": "Paris",
        }
    ]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    with patch("eval_live.generate_response", return_value="Paris"):
        first_report = main()
        second_report = main()

    report_files = list((tmp_path / "reports").glob("evaluation-*.json"))

    assert len(report_files) == 2

    saved_reports = []
    for report_file in report_files:
        with report_file.open("r", encoding="utf-8") as file:
            saved_reports.append(json.load(file))

    assert first_report in saved_reports
    assert second_report in saved_reports


def test_request_durations_not_overwritten(tmp_path, monkeypatch):
    data = [
        {"id": "test_001", "question": "First?", "expected": "A"},
        {"id": "test_002", "question": "Second?", "expected": "B"},
    ]

    (tmp_path / "eval-read-live.json").write_text(json.dumps(data))
    monkeypatch.chdir(tmp_path)

    with patch("eval_live.generate_response", side_effect=["A", "B"]):
        with patch("eval_live.time.perf_counter", side_effect=[10.0, 12.0, 20.0, 23.0]):
            report = main()

    assert report["results"][0]["duration_seconds"] == 2.0
    assert report["results"][1]["duration_seconds"] == 3.0


def test_report_save_failure(tmp_path, monkeypatch, capsys):
    data = [
        {
            "id": "test_001",
            "question": "What is the capital of France?",
            "expected": "Paris",
        }
    ]

    (tmp_path / "eval-read-live.json").write_text(json.dumps(data))
    monkeypatch.chdir(tmp_path)

    (tmp_path / "reports").write_text("Not a dictionary")

    with patch("eval_live.generate_response", return_value="Paris"):
        with pytest.raises(SystemExit) as error:
            main()
    output = capsys.readouterr().out

    assert error.value.code == 1
    assert "Error saving report:" in output


def test_reference_metadata_preserved(tmp_path, monkeypatch):
    data = [
        {
            "id": "fact_001",
            "question": "What is the chemical symbol for gold?",
            "expected": "Au",
            "reference": {"url": "https://example.com", "verified_date": "2026-10-21"},
        }
    ]

    dataset_file = tmp_path / "eval-read-reference.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    with patch("eval_live.generate_response", return_value="Au"):
        report = main("eval-read-reference.json")

    assert report["results"][0]["status"] == "PASS"
    assert report["results"][0]["reference"] == data[0]["reference"]


def test_reference_metadata_preserved_on_error(tmp_path, monkeypatch):
    data = [
        {
            "id": "fact_001",
            "question": "What is the chemical symbol for gold?",
            "expected": "Au",
            "reference": {"url": "https://example.com", "verified_date": "2026-10-21"},
        }
    ]

    dataset_file = tmp_path / "eval-read-reference.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    with patch(
        "eval_live.generate_response", side_effect=URLError("Connection refused")
    ):
        report = main("eval-read-reference.json")

    result = report["results"][0]

    assert result["status"] == "ERROR"
    assert result["generated"] is None
    assert result["reference"] == data[0]["reference"]
    assert report["summary"]["errors"] == 1


def test_live_alternative_scoring(tmp_path, monkeypatch):
    data = [
        {
            "id": "fact_001",
            "question": "What city is also called NYC?",
            "expected": "New York City",
            "accepted_answers": ["NYC"],
            "reference": {"url": "https://example.com", "verified_date": "2026-10-21"},
        }
    ]

    (tmp_path / "eval-read-reference.json").write_text(json.dumps(data))
    monkeypatch.chdir(tmp_path)

    with patch("eval_live.generate_response", return_value="NYC"):
        report = main("eval-read-reference.json")

    result = report["results"][0]

    assert result["status"] == "FAIL"
    assert result["alternative_scoring"]["status"] == "PASS"
    assert result["alternative_scoring"]["reason"] == "Accepted alternative"
    assert report["summary"]["accuracy"] == 0.0


def test_alternative_scoring_on_request_error(tmp_path, monkeypatch):
    data = [
        {
            "id": "fact_001",
            "question": "What city is called NYC?",
            "expected": "New York City",
            "accepted_answers": ["NYC"],
            "reference": {"url": "https://example.com", "verified_date": "2026-10-21"},
        }
    ]

    (tmp_path / "eval-read-reference.json").write_text(json.dumps(data))
    monkeypatch.chdir(tmp_path)

    with patch(
        "eval_live.generate_response", side_effect=URLError("Connection refused")
    ):
        report = main("eval-read-reference.json")

    result = report["results"][0]

    assert result["status"] == "ERROR"
    assert result["alternative_scoring"]["status"] == "ERROR"
    assert result["reference"] == data[0]["reference"]
    assert report["summary"]["errors"] == 1


def test_custom_model_forwarded(tmp_path, monkeypatch):
    data = [
        {
            "id": "test_001",
            "question": "What is 2 + 2?",
            "expected": "4",
        }
    ]

    dataset = tmp_path / "eval-read-live.json"
    dataset.write_text(json.dumps(data), encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    with patch(
        "eval_live.generate_response",
        return_value="4",
    ) as mock_generate:
        report = main(model="custom-model")

    mock_generate.assert_called_once_with(
        "What is 2 + 2?",
        "custom-model",
    )
    assert report["metadata"]["model"] == "custom-model"


def test_reference_dataset_in_subdirectory(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parent.parent / "eval-read-reference.json"

    dataset_dir = tmp_path / "datasets"
    dataset_dir.mkdir()

    dataset_path = dataset_dir / "eval-read-reference.json"
    dataset_path.write_bytes(source.read_bytes())

    monkeypatch.chdir(tmp_path)

    with patch(
        "eval_live.generate_response",
        return_value="Incorrect answer",
    ):
        report = main(filename=str(dataset_path))

    assert report["metadata"]["dataset"] == str(dataset_path)
    assert "reference" in report["results"][0]
    assert "alternative_scoring" in report["results"][0]


def test_live_report_contains_dataset_fingerprint(tmp_path, monkeypatch):
    contents = b'[{"id":"test_001","question":"What is 2 + 2?","expected":"4"}]'

    dataset = tmp_path / "eval-read-live.json"
    dataset.write_bytes(contents)
    monkeypatch.chdir(tmp_path)

    with patch("eval_live.generate_response", return_value="4"):
        report = main()

    assert report["metadata"]["provenance"]["dataset_sha256"] == (
        hashlib.sha256(contents).hexdigest()
    )
    assert report["summary"]["passed"] == 1

    report_files = list((tmp_path / "reports").glob("evaluation-*.json"))

    assert len(report_files) == 1

    with report_files[0].open("r", encoding="utf-8") as file:
        saved_report = json.load(file)

    assert saved_report["metadata"]["provenance"]["dataset_sha256"] == (
        hashlib.sha256(contents).hexdigest()
    )
    assert saved_report == report


def test_live_report_records_exact_scoring_identifier(tmp_path, monkeypatch):
    dataset = tmp_path / "eval-read-live.json"
    dataset.write_text(
        '[{"id":"test_001","question":"What is 2 + 2?","expected":"4"}]',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with patch("eval_live.generate_response", return_value="4"):
        report = main()

    provenance = report["metadata"]["provenance"]

    assert provenance["primary_scoring"] == "normalized-exact-v1"
    assert provenance["alternative_scoring"] is None


def test_reference_report_records_both_scoring_identifiers(tmp_path, monkeypatch):
    dataset = tmp_path / "eval-read-reference.json"
    dataset.write_text(
        json.dumps(
            [
                {
                    "id": "fact_001",
                    "question": "What is the chemical symbol for gold?",
                    "expected": "Au",
                    "reference": {
                        "url": "https://example.com",
                        "verified_date": "2026-10-21",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with patch("eval_live.generate_response", return_value="Au"):
        report = main("eval-read-reference.json")

    provenance = report["metadata"]["provenance"]

    assert provenance["primary_scoring"] == "normalized-exact-v1"
    assert provenance["alternative_scoring"] == "accepted-alternatives-v1"
    assert report["results"][0]["alternative_scoring"]["status"] == "PASS"


def test_live_report_does_not_invent_model_configuration(tmp_path, monkeypatch):
    dataset = tmp_path / "eval-read-live.json"
    dataset.write_text(
        json.dumps(
            [
                {
                    "id": "test_001",
                    "question": "What is 2 + 2?",
                    "expected": "4",
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    with patch(
        "eval_live.generate_response",
        return_value="4",
    ) as mock_generate:
        report = main(model="gemma3:1b")

    provenance = report["metadata"]["provenance"]

    assert provenance["model_options"] is None
    assert provenance["model_version"] is None

    mock_generate.assert_called_once_with(
        "What is 2 + 2?",
        "gemma3:1b",
    )

    assert provenance["python_version"] == platform.python_version()
