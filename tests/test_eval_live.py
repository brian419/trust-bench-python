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
        main()

    output = capsys.readouterr().out

    assert "Passed: 2" in output
    assert "Failed: 0" in output
    assert "Errors: 0" in output
    assert "Accuracy: 100.0" in output
    assert mock_generate.call_count == 2


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
        main()

    output = capsys.readouterr().out

    assert "Passed: 1" in output
    assert "Failed: 1" in output
    assert "Errors: 0" in output
    assert "Accuracy: 50.0" in output
    assert mock_generate.call_count == 2


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
        main()

    output = capsys.readouterr().out

    assert "Result: ERROR" in output
    assert "Network error: Connection refused" in output
    assert "Passed: 1" in output
    assert "Failed: 0" in output
    assert "Errors: 1" in output
    assert "Accuracy: 100.0" in output
    assert mock_generate.call_count == 2


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
        main()

    output = capsys.readouterr().out

    assert "HTTP error: 404" in output
    assert "Passed: 1" in output
    assert "Failed: 0" in output
    assert "Errors: 1" in output
    assert "Accuracy: 100.0" in output
    assert mock_generate.call_count == 2


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
        main()

    output = capsys.readouterr().out

    assert "Request timed out" in output
    assert "Passed: 1" in output
    assert "Failed: 0" in output
    assert "Errors: 1" in output
    assert "Accuracy: 100.0" in output
    assert mock_generate.call_count == 2


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
        main()

    output = capsys.readouterr().out

    assert "Request timed out" in output
    assert "Passed: 1" in output
    assert "Failed: 0" in output
    assert "Errors: 1" in output
    assert "Accuracy: 100.0" in output
    assert mock_generate.call_count == 2
