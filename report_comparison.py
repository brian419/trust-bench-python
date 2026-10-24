"""Compare individual TrustBench evaluation results."""

from report_compatibility import (
    compare_report_compatibility,
    detect_report_type,
)


def classify_status_change(previous: str, current: str) -> str:
    """Classify a change between two live-evaluation statuses."""

    valid_statuses = {"PASS", "FAIL", "ERROR"}

    if previous not in valid_statuses:
        raise ValueError(f"Unknown previous status: {previous}")

    if current not in valid_statuses:
        raise ValueError(f"Unknown current status: {current}")

    if previous == current:
        return "UNCHANGED"

    if previous == "FAIL" and current == "PASS":
        return "IMPROVEMENT"

    if previous == "PASS" and current == "FAIL":
        return "REGRESSION"

    if previous == "ERROR" and current in {"PASS", "FAIL"}:
        return "RECOVERED"

    if previous in {"PASS", "FAIL"} and current == "ERROR":
        return "NEW_ERROR"

    raise ValueError("Unsupported status transition.")


def index_results_by_id(results: list[dict]) -> dict[str, dict]:
    """Index evaluation results by their unique case IDs."""

    if not isinstance(results, list):
        raise ValueError("Results must be a list.")

    indexed = {}

    for result in results:
        if not isinstance(result, dict):
            raise ValueError("Each result must be an object.")

        case_id = result.get("id")

        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("Each result must have a non-empty string ID.")

        if case_id in indexed:
            raise ValueError(f"Duplicate case ID: {case_id}")

        indexed[case_id] = result

    return indexed


def compare_live_results(
    previous_results: list[dict],
    current_results: list[dict],
) -> list[dict]:
    """Compare live-evaluation results using their case IDs."""

    previous_index = index_results_by_id(previous_results)
    current_index = index_results_by_id(current_results)

    valid_statuses = {"PASS", "FAIL", "ERROR"}

    for report_name, indexed in (
        ("previous", previous_index),
        ("current", current_index),
    ):
        for case_id, result in indexed.items():
            status = result.get("status")

            if not isinstance(status, str) or status not in valid_statuses:
                raise ValueError(
                    f"Invalid {report_name} status for case {case_id}: {status}"
                )

    comparisons = []

    all_ids = sorted(set(previous_index) | set(current_index))

    for case_id in all_ids:
        previous = previous_index.get(case_id)
        current = current_index.get(case_id)

        if previous is None:
            comparisons.append(
                {
                    "id": case_id,
                    "previous_status": None,
                    "current_status": current["status"],
                    "change": "ADDED",
                }
            )
            continue

        if current is None:
            comparisons.append(
                {
                    "id": case_id,
                    "previous_status": previous["status"],
                    "current_status": None,
                    "change": "REMOVED",
                }
            )
            continue

        change = classify_status_change(
            previous["status"],
            current["status"],
        )

        comparisons.append(
            {
                "id": case_id,
                "previous_status": previous["status"],
                "current_status": current["status"],
                "change": change,
            }
        )

    return comparisons


def summarize_live_comparison(comparisons: list[dict]) -> dict:
    """Count changes in a live-evaluation comparison."""

    change_types = (
        "UNCHANGED",
        "IMPROVEMENT",
        "REGRESSION",
        "RECOVERED",
        "NEW_ERROR",
        "ADDED",
        "REMOVED",
    )

    counts = {change: 0 for change in change_types}

    for comparison in comparisons:
        change = comparison["change"]

        if change not in counts:
            raise ValueError(f"Unknown comparison change: {change}")

        counts[change] += 1

    return {
        "total_cases": len(comparisons),
        "unchanged": counts["UNCHANGED"],
        "improvements": counts["IMPROVEMENT"],
        "regressions": counts["REGRESSION"],
        "recovered": counts["RECOVERED"],
        "new_errors": counts["NEW_ERROR"],
        "added": counts["ADDED"],
        "removed": counts["REMOVED"],
    }


def compare_live_reports(previous: dict, current: dict) -> dict:
    """Compare two compatible live-evaluation reports."""

    previous_type = detect_report_type(previous)
    current_type = detect_report_type(current)

    if previous_type != "live" or current_type != "live":
        raise ValueError("Live report comparison requires two live-evaluation reports.")

    compatibility = compare_report_compatibility(previous, current)

    if compatibility["status"] != "PARTIAL_MATCH":
        raise ValueError(f"Reports cannot be compared: {compatibility['reason']}")

    for report_name, report in (
        ("previous", previous),
        ("current", current),
    ):
        if not isinstance(report.get("results"), list):
            raise ValueError(f"The {report_name} report must contain a results list.")

    comparisons = compare_live_results(
        previous["results"],
        current["results"],
    )

    return {
        "compatibility": compatibility,
        "summary": summarize_live_comparison(comparisons),
        "comparisons": comparisons,
    }
