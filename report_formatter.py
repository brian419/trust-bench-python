"""Format TrustBench evaluation summaries as readable text."""

from report_summary import build_live_report_summary


def format_live_report(report: dict) -> str:
    """Convert a saved live-evaluation report into readable text."""

    data = build_live_report_summary(report)

    metadata = data["metadata"]
    summary = data["summary"]
    examples = data["examples"]

    accuracy = (
        f"{summary['accuracy']:.2f}%" if summary["accuracy"] is not None else "N/A"
    )

    lines = [
        "TrustBench Evaluation Report",
        "============================",
        f"Model: {metadata['model'] or 'Unknown'}",
        f"Dataset: {metadata['dataset'] or 'Unknown'}",
        f"Timestamp: {metadata['timestamp'] or 'Unknown'}",
        "",
        "Evaluation Summary",
        "------------------",
        f"Total cases: {summary['total_cases']}",
        f"Scored cases: {summary['scored_cases']}",
        f"Passed: {summary['passed']}",
        f"Failed: {summary['failed']}",
        f"Request errors: {summary['errors']}",
        f"Exact-match accuracy: {accuracy}",
        "",
        "Failed Answers",
        "--------------",
    ]

    if examples["failures"]:
        for item in examples["failures"]:
            lines.extend(
                [
                    f"Case: {item['id'] or 'Unknown'}",
                    f"Question: {item['question'] or 'Unknown'}",
                    f"Expected: {item['expected'] if item['expected'] is not None else 'Unknown'}",
                    f"Generated: {item['generated'] if item['generated'] is not None else 'Unknown'}",
                    "",
                ]
            )
    else:
        lines.append("No failed answers recorded.")
        lines.append("")

    lines.extend(
        [
            "Request Errors",
            "--------------",
        ]
    )

    if examples["errors"]:
        for item in examples["errors"]:
            lines.extend(
                [
                    f"Case: {item['id'] or 'Unknown'}",
                    f"Question: {item['question'] or 'Unknown'}",
                    f"Error: {item['error'] or 'Unknown'}",
                    "",
                ]
            )
    else:
        lines.append("No request errors recorded.")
        lines.append("")

    lines.extend(
        [
            "Interpretation and Limitations",
            "------------------------------",
            "Accuracy measures normalized exact-answer matches",
            "among successfully scored responses (PASS and FAIL).",
            "Request errors are excluded from the accuracy denominator.",
            "A failed exact match does not necessarily mean the answer",
            "is factually incorrect.",
            "This report does not establish general model reliability,",
            "factuality, fairness, or safety.",
        ]
    )

    return "\n".join(lines) + "\n"
