import pytest
import subprocess
import sys
import json
from eval import compare_answers, calculate_accuracy, validate_dataset


def test_identical_answers():
    assert compare_answers("Paris", "Paris")

def test_wrong_answers():
    assert not compare_answers("Paris", "London")

def test_case_insensitive():
    assert compare_answers("Paris", "PARIS")

def test_whitespace_normalization():
    assert compare_answers("Tokyo", " Tokyo ")


# calculate_accuracy

def test_all_passed():
    assert round(calculate_accuracy(3,0),2) == 100.00

def test_all_failed():
    assert round(calculate_accuracy(0,3),2) == 0.00

def test_half_passed():
    assert round(calculate_accuracy(1,1),2) == 50.00

def test_mixed_result():
    assert round(calculate_accuracy(2,1),2) == 66.67

def test_no_tests():
    assert calculate_accuracy(0,0) is None


# validation test
def test_valid_empty_dataset():
    assert validate_dataset([]) == []

def test_invalid_top_level():
    assert validate_dataset({}) == [
        "Error: JSON must contain a list of test cases."
    ]

def test_invalid_item_type():
    assert validate_dataset(["ids"]) == [
        "Error: Test case #1 must be a dictionary."
    ]
    

@pytest.mark.parametrize("missing_field", [
    "id",
    "question",
    "expected",
    "response"
])
def test_missing_required_field(missing_field):
    item = {
        "id": "test_001",
        "question": "What is the capital of France?",
        "expected": "Paris",
        "response": "Paris"
    }

    item.pop(missing_field)

    data = [item]

    assert validate_dataset(data) == [
        f"Error: Test case #1: Missing required field '{missing_field}'."
    ]


@pytest.mark.parametrize("invalid_field", [
    "id",
    "question",
    "expected",
    "response"
])
def test_incorrect_field_type(invalid_field):
    item = {
        "id": "test_001",
        "question": "What is 6 multiplied by 2?",
        "expected": "12",
        "response": "12"
    }
    
    item[invalid_field] = 12

    data = [item]

    assert validate_dataset(data) == [
        f"Error: Test case #1: Field '{invalid_field}' must be a string."
    ]


def test_multiple_validation_errors():
    data = [
        {
            "id": "test_001",
            "question": "What is the capital of France?",
            "expected": "Paris"
        },
        {
            "id": "test_002",
            "question": "What is 6 multiplied by 2?",
            "expected": "12",
            "response": 12
        }
    ]

    assert validate_dataset(data) == [
        "Error: Test case #1: Missing required field 'response'.",
        "Error: Test case #2: Field 'response' must be a string."
    ]

def test_valid_dataset():

    data = [
        {
            "id": "test_001",
            "question": "What is the capital of France?",
            "expected": "Paris",
            "response": "  PARIS  "
        }
        
    ]

    assert validate_dataset(data) == []


def test_cli_valid_dataset(tmp_path):
    data = [{
        "id": "test_001",
        "question": "What is the capital of France?",
        "expected": "Paris",
        "response": "  PARIS  "
    }]

    valid_file = tmp_path / "valid.json"
    valid_file.write_text(json.dumps(data))

    result = subprocess.run(
        [sys.executable, "eval.py", str(valid_file)],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "Accuracy: 100.0" in result.stdout
    assert "Test ID: test_001 ; PASS: The answers match!" in result.stdout
    assert "Passed 1 test" in result.stdout
    assert "Failed 0 tests" in result.stdout


def test_cli_invalid_dataset(tmp_path):
    data = [{
        "id": "test_001",
        "question": "What is 2 + 2?",
        "expected": "4"
    }]

    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text(json.dumps(data))

    result = subprocess.run(
        [sys.executable, "eval.py", str(invalid_file)],
        capture_output=True,
        text=True
    )

    assert result.returncode == 1
    assert "Validation failed: 1 error(s) found." in result.stdout
    assert "Missing required field 'response'." in result.stdout
    assert "Accuracy:" not in result.stdout


def test_cli_malformed_dataset(tmp_path):
    malformed_file = tmp_path / "malformed.json"

    malformed_file.write_text(
        '{"id": "test_001" "question": "Hello"}'
    )

    result = subprocess.run(
        [sys.executable, "eval.py", str(malformed_file)],
        capture_output=True,
        text=True
    )

    assert result.returncode == 1
    assert "Expecting ',' delimiter" in result.stdout


def test_cli_missing_file(tmp_path):
    missing_file = tmp_path / "missing.json"

    result = subprocess.run(
        [sys.executable, "eval.py", str(missing_file)],
        capture_output=True,
        text=True
    )

    assert result.returncode == 1
    assert "No such file or directory" in result.stdout
