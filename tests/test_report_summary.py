import pytest

from report_summary import (
    summarize_live_report,
    extract_failure_examples,
    build_live_report_summary,
)


def test_summarize_live_report():
    report = {
        "results": [
            {"id": "fact_001", "status": "PASS"},
            {"id": "fact_002", "status": "PASS"},
            {"id": "fact_003", "status": "FAIL"},
            {"id": "fact_004", "status": "ERROR"},
        ]
    }

    summary = summarize_live_report(report)

    assert summary == {
        "total_cases": 4,
        "passed": 2,
        "failed": 1,
        "errors": 1,
        "scored_cases": 3,
        "accuracy": 66.67,
    }


def test_summarize_empty_report():
    report = {"results": []}

    summary = summarize_live_report(report)

    assert summary["total_cases"] == 0
    assert summary["accuracy"] is None


def test_summarize_all_errors():
    report = {
        "results": [
            {"id": "fact_001", "status": "ERROR"},
            {"id": "fact_002", "status": "ERROR"},
        ]
    }

    summary = summarize_live_report(report)

    assert summary["errors"] == 2
    assert summary["scored_cases"] == 0
    assert summary["accuracy"] is None


def test_reject_invalid_results():
    report = {"results": "invalid"}

    with pytest.raises(ValueError, match="results list"):
        summarize_live_report(report)


def test_reject_unknown_status():
    report = {
        "results": [
            {"id": "fact_001", "status": "UNKNOWN"},
        ]
    }

    with pytest.raises(ValueError, match="Unknown result status"):
        summarize_live_report(report)


def test_extract_failure_examples():
    report = {
        "results": [
            {
                "id": "fact_001",
                "question": "What is 2 + 2?",
                "expected": "4",
                "generated": "5",
                "status": "FAIL",
            },
            {
                "id": "fact_002",
                "question": "What is the capital of France?",
                "expected": "Paris",
                "generated": "Paris",
                "status": "PASS",
            },
            {
                "id": "fact_003",
                "question": "What is 3 + 3?",
                "status": "ERROR",
                "error": "Connection failed",
            },
        ]
    }

    examples = extract_failure_examples(report)

    assert examples["failures"] == [
        {
            "id": "fact_001",
            "question": "What is 2 + 2?",
            "expected": "4",
            "generated": "5",
        }
    ]

    assert examples["errors"] == [
        {
            "id": "fact_003",
            "question": "What is 3 + 3?",
            "error": "Connection failed",
        }
    ]


def test_extract_no_failures():
    report = {
        "results": [
            {"id": "fact_001", "status": "PASS"},
        ]
    }

    examples = extract_failure_examples(report)

    assert examples == {
        "failures": [],
        "errors": [],
    }


def test_extract_failure_examples_empty_report():
    examples = extract_failure_examples({"results": []})

    assert examples["failures"] == []
    assert examples["errors"] == []


def test_extract_failure_examples_rejects_invalid_status():
    report = {
        "results": [
            {"id": "fact_001", "status": "UNKNOWN"},
        ]
    }

    with pytest.raises(ValueError, match="Unknown result status"):
        extract_failure_examples(report)


def test_build_live_report_summary():
    report = {
        "metadata": {
            "model": "gemma3:1b",
            "dataset": "eval-read-reference.json",
            "timestamp": "2026-10-24T18:00:00+00:00",
        },
        "results": [
            {
                "id": "fact_001",
                "question": "What is 2 + 2?",
                "expected": "4",
                "generated": "5",
                "status": "FAIL",
            },
            {
                "id": "fact_002",
                "question": "What is 3 + 3?",
                "status": "ERROR",
                "error": "Connection failed",
            },
        ],
    }

    result = build_live_report_summary(report)

    assert result["metadata"] == {
        "model": "gemma3:1b",
        "dataset": "eval-read-reference.json",
        "timestamp": "2026-10-24T18:00:00+00:00",
    }

    assert result["summary"]["failed"] == 1
    assert result["summary"]["errors"] == 1
    assert result["summary"]["accuracy"] == 0.0

    assert result["examples"]["failures"][0]["id"] == "fact_001"
    assert result["examples"]["errors"][0]["id"] == "fact_002"


def test_build_live_report_summary_without_metadata():
    report = {
        "results": [
            {"id": "fact_001", "status": "PASS"},
        ]
    }

    result = build_live_report_summary(report)

    assert result["metadata"]["model"] is None
    assert result["metadata"]["dataset"] is None
    assert result["metadata"]["timestamp"] is None
    assert result["summary"]["passed"] == 1


def test_build_live_report_summary_rejects_invalid_metadata():
    report = {
        "metadata": "invalid",
        "results": [],
    }

    with pytest.raises(ValueError, match="metadata must be an object"):
        build_live_report_summary(report)
