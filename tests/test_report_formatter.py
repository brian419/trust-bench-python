from report_formatter import format_live_report


def test_format_live_report():
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

    output = format_live_report(report)

    assert "TrustBench Evaluation Report" in output
    assert "Model: gemma3:1b" in output
    assert "Total cases: 2" in output
    assert "Exact-match accuracy: 0.00%" in output
    assert "Case: fact_001" in output
    assert "Generated: 5" in output
    assert "Case: fact_002" in output
    assert "Error: Connection failed" in output
    assert "Interpretation and Limitations" in output


def test_format_empty_report():
    report = {
        "metadata": {},
        "results": [],
    }

    output = format_live_report(report)

    assert "Model: Unknown" in output
    assert "Total cases: 0" in output
    assert "Exact-match accuracy: N/A" in output
    assert "No failed answers recorded." in output
    assert "No request errors recorded." in output
