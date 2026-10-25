"""Generate summaries from existing TrustBench evaluation reports."""


def summarize_live_report(report: dict) -> dict:
    """Count outcomes in a saved live-evaluation report."""

    if not isinstance(report, dict):
        raise ValueError("Report must be an object.")

    results = report.get("results")

    if not isinstance(results, list):
        raise ValueError("Report must contain a results list.")

    counts = {
        "PASS": 0,
        "FAIL": 0,
        "ERROR": 0,
    }

    for result in results:
        if not isinstance(result, dict):
            raise ValueError("Each result must be an object.")

        status = result.get("status")

        if not isinstance(status, str) or status not in counts:
            raise ValueError(f"Unknown result status: {status}")

        counts[status] += 1

    scored = counts["PASS"] + counts["FAIL"]

    accuracy = round(counts["PASS"] / scored * 100, 2) if scored > 0 else None

    return {
        "total_cases": len(results),
        "passed": counts["PASS"],
        "failed": counts["FAIL"],
        "errors": counts["ERROR"],
        "scored_cases": scored,
        "accuracy": accuracy,
    }


def extract_failure_examples(report: dict) -> dict:
    """Separate incorrect answers from model request errors."""

    if not isinstance(report, dict):
        raise ValueError("Report must be an object.")

    results = report.get("results")

    if not isinstance(results, list):
        raise ValueError("Report must contain a results list.")

    failures = []
    errors = []

    for result in results:
        if not isinstance(result, dict):
            raise ValueError("Each result must be an object.")

        status = result.get("status")

        if not isinstance(status, str) or status not in {"PASS", "FAIL", "ERROR"}:
            raise ValueError(f"Unknown result status: {status}")

        if status == "FAIL":
            failures.append(
                {
                    "id": result.get("id"),
                    "question": result.get("question"),
                    "expected": result.get("expected"),
                    "generated": result.get("generated"),
                }
            )

        elif status == "ERROR":
            errors.append(
                {
                    "id": result.get("id"),
                    "question": result.get("question"),
                    "error": result.get("error"),
                }
            )

    return {
        "failures": failures,
        "errors": errors,
    }


def build_live_report_summary(report: dict) -> dict:
    """Build a structured summary of a saved live-evaluation report."""

    summary = summarize_live_report(report)
    examples = extract_failure_examples(report)

    metadata = report.get("metadata", {})

    if not isinstance(metadata, dict):
        raise ValueError("Report metadata must be an object.")

    return {
        "metadata": {
            "model": metadata.get("model"),
            "dataset": metadata.get("dataset"),
            "timestamp": metadata.get("timestamp"),
        },
        "summary": summary,
        "examples": examples,
    }
