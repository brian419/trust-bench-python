"""Format TrustBench report comparisons as readable text."""

from compare_reports import compare_report_files


def format_comparison(result: dict) -> str:
    """Convert a structured report comparison to readable text."""

    summary = result["summary"]
    compatibility = result["compatibility"]

    lines = [
        "TrustBench Report Comparison",
        "============================",
        "",
        "Comparison Summary",
        "------------------",
        f"Total unique cases: {summary['total_cases']}",
        f"Unchanged: {summary['unchanged']}",
        f"Improvements: {summary['improvements']}",
        f"Regressions: {summary['regressions']}",
        f"Recovered requests: {summary['recovered']}",
        f"New errors: {summary['new_errors']}",
        f"Added cases: {summary['added']}",
        f"Removed cases: {summary['removed']}",
        "",
        f"Compatibility: {compatibility['status']}",
    ]

    warnings = compatibility.get("warnings", [])

    if warnings:
        lines.extend(
            [
                "",
                "Compatibility Warnings",
                "----------------------",
            ]
        )

        for warning in warnings:
            lines.append(f"- {warning}")

    changes = [item for item in result["comparisons"] if item["change"] != "UNCHANGED"]

    lines.extend(
        [
            "",
            "Case Changes",
            "------------",
        ]
    )

    if changes:
        for item in changes:
            previous = item["previous_status"] or "N/A"
            current = item["current_status"] or "N/A"

            lines.append(f"{item['id']}: {previous} -> {current} ({item['change']})")
    else:
        lines.append("No status changes recorded.")

    lines.extend(
        [
            "",
            "Interpretation and Limitations",
            "------------------------------",
            "Improvements and regressions describe exact-match status changes.",
            "Recovered requests are not necessarily accuracy improvements.",
            "Compatibility checks rely on recorded provenance metadata.",
            "A partial match does not establish deterministic reproducibility.",
        ]
    )

    return "\n".join(lines) + "\n"


def generate_comparison_text(
    previous_path: str,
    current_path: str,
) -> str:
    """Compare two saved reports and return readable text."""

    result = compare_report_files(previous_path, current_path)
    return format_comparison(result)
