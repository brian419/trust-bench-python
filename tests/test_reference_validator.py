from reference_validator import validate_reference_dataset


def test_valid_reference_dataset():
    data = [
        {
            "id": "fact_001",
            "question": "What is the chemical symbol for gold?",
            "expected": "Au",
            "reference": {"url": "https://example.com", "verified_date": "2026-10-21"},
        }
    ]

    assert validate_reference_dataset(data) == []


def test_missing_reference():
    data = [
        {
            "id": "fact_001",
            "question": "What is the chemical symbol for gold?",
            "expected": "Au",
        }
    ]

    assert validate_reference_dataset(data) == ["ERROR: Missing field of 'reference'."]


def test_invalid_verification_date():
    data = [
        {
            "id": "fact_001",
            "question": "What is the chemical symbol for gold?",
            "expected": "Au",
            "reference": {"url": "https://example.com", "verified_date": "2026-02-30"},
        }
    ]

    assert validate_reference_dataset(data) == ["ERROR: Invalid verification date."]


def test_missing_expected_answer():
    data = [
        {
            "id": "fact_001",
            "question": "What is the chemical symbol for gold?",
            "reference": {"url": "https://example.com", "verified_date": "2026-10-21"},
        }
    ]

    errors = validate_reference_dataset(data)

    assert "Error: Test case #1: Missing required field 'expected'." in errors
