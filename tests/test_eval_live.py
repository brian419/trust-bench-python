import json
import pytest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from eval_live import main

def test_live_evaluation_all_pass(tmp_path, monkeypatch, capsys):
    data = [
        {
            "id": "test_001",
            "question": "What is the capital of France?",
            "expected": "Paris"
        },
        {
            "id": "test_002",
            "question": "What is 6 multiplied by 2?",
            "expected": "12"
        }
    ]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    with patch("eval_live.generate_response", side_effect=["Paris", "12"]) as mock_generate:
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
            "expected": "Paris"
        },
        {
            "id": "test_002",
            "question": "What is 6 multiplied by 2?",
            "expected": "12"
        }
    ]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    with patch("eval_live.generate_response", side_effect=["London", "12"]) as mock_generate:
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
            "expected": "Paris"
        },
        {
            "id": "test_002",
            "question": "What is 6 multiplied by 2?",
            "expected": "12"
        }
    ]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    with patch(
        "eval_live.generate_response",
        side_effect=[URLError("Connection refused"), "12"]
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
            "expected": "Paris"
        },
        {
            "id": "test_002",
            "question": "What is 6 multiplied by 2?",
            "expected": "12"
        }
    ]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    with patch(
        "eval_live.generate_response",
        side_effect=[
            URLError("Connection refused"),
            URLError("Connection refused")
        ]
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
    data = [{
        "id": "test_001",
        "question": "What is the capital of France?"
    }]

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
            "expected": "Paris"
        },
        {
            "id": "test_002",
            "question": "What is 6 multiplied by 2?",
            "expected": "12"
        }
    ]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    fake_error = HTTPError(
        url="http://localhost:11434/api/generate",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None
    )

    with patch(
        "eval_live.generate_response",
        side_effect=[fake_error, "12"]
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
            "expected": "Paris"
        },
        {
            "id": "test_002",
            "question": "What is 6 multiplied by 2?",
            "expected": "12"
        }
    ]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    with patch(
        "eval_live.generate_response",
        side_effect=[TimeoutError("Timed out"), "12"]
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

    dataset_file.write_text(
        '{"id": "test_001" "question": "Hello"}'
    )

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
            "expected": "Paris"
        },
        {
            "id": "test_002",
            "question": "What is 6 multiplied by 2?",
            "expected": "12"
        }
    ]

    dataset_file = tmp_path / "eval-read-live.json"
    dataset_file.write_text(json.dumps(data))

    monkeypatch.chdir(tmp_path)

    wrapped_timeout = URLError(TimeoutError("timed out"))

    with patch(
        "eval_live.generate_response",
        side_effect=[wrapped_timeout, "12"]
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
            "expected": "Paris"
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
        {"id": "test_002", "question": "Second?", "expected": "B"}
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
            "expected": "Paris"
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
