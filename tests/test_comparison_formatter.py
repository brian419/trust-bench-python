from unittest.mock import patch

from comparison_formatter import format_comparison, generate_comparison_text


def make_comparison():
    return {
        "summary": {
            "total_cases": 3,
            "unchanged": 1,
            "improvements": 1,
            "regressions": 1,
            "recovered": 0,
            "new_errors": 0,
            "added": 0,
            "removed": 0,
        },
        "compatibility": {
            "status": "PARTIAL_MATCH",
            "warnings": ["Model version was not recorded."],
        },
        "comparisons": [
            {
                "id": "fact_001",
                "previous_status": "FAIL",
                "current_status": "PASS",
                "change": "IMPROVEMENT",
            },
            {
                "id": "fact_002",
                "previous_status": "PASS",
                "current_status": "FAIL",
                "change": "REGRESSION",
            },
            {
                "id": "fact_003",
                "previous_status": "PASS",
                "current_status": "PASS",
                "change": "UNCHANGED",
            },
        ],
    }


def test_format_comparison():
    output = format_comparison(make_comparison())

    assert "TrustBench Report Comparison" in output
    assert "Total unique cases: 3" in output
    assert "Improvements: 1" in output
    assert "Regressions: 1" in output
    assert "Compatibility: PARTIAL_MATCH" in output
    assert "Model version was not recorded." in output
    assert "fact_001: FAIL -> PASS (IMPROVEMENT)" in output
    assert "fact_002: PASS -> FAIL (REGRESSION)" in output
    assert "fact_003: PASS -> PASS" not in output


def test_format_comparison_without_changes():
    result = make_comparison()

    result["comparisons"] = []
    result["compatibility"]["warnings"] = []

    output = format_comparison(result)

    assert "No status changes recorded." in output
    assert "Compatibility Warnings" not in output


def test_generate_comparison_text():
    comparison = make_comparison()

    with patch(
        "comparison_formatter.compare_report_files",
        return_value=comparison,
    ) as compare:
        output = generate_comparison_text(
            "previous.json",
            "current.json",
        )

    compare.assert_called_once_with(
        "previous.json",
        "current.json",
    )

    assert "Improvements: 1" in output
    assert "Regressions: 1" in output
