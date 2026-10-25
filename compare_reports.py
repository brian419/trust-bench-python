"""Command-line interface for comparing TrustBench reports."""

from argparse import ArgumentParser
from json import JSONDecodeError

from report_comparison import compare_live_reports
from report_loader import load_report


def compare_report_files(previous_path: str, current_path: str) -> dict:
    """Load two report files and compare their live-evaluation results."""

    previous = load_report(previous_path)
    current = load_report(current_path)

    return compare_live_reports(previous, current)


def main() -> None:
    parser = ArgumentParser(
        description="Compare two TrustBench live-evaluation reports."
    )

    parser.add_argument(
        "previous",
        help="Path to the previous JSON report.",
    )

    parser.add_argument(
        "current",
        help="Path to the current JSON report.",
    )

    args = parser.parse_args()

    try:
        result = compare_report_files(args.previous, args.current)
    except FileNotFoundError as error:
        parser.error(f"Report file not found: {error.filename}")
    except JSONDecodeError as error:
        parser.error(
            f"Invalid JSON report: {error.msg} "
            f"(line {error.lineno}, column {error.colno})"
        )
    except UnicodeError:
        parser.error("Report file is not valid UTF-8 text.")
    except ValueError as error:
        parser.error(str(error))

    summary = result["summary"]

    print("TrustBench Report Comparison")
    print("----------------------------")
    print(f"Total unique cases: {summary['total_cases']}")
    print(f"Unchanged: {summary['unchanged']}")
    print(f"Improvements: {summary['improvements']}")
    print(f"Regressions: {summary['regressions']}")
    print(f"Recovered requests: {summary['recovered']}")
    print(f"New errors: {summary['new_errors']}")
    print(f"Added cases: {summary['added']}")
    print(f"Removed cases: {summary['removed']}")

    print()
    print(f"Compatibility: {result['compatibility']['status']}")

    warnings = result["compatibility"].get("warnings", [])

    if warnings:
        print()
        print("Compatibility warnings:")

        for warning in warnings:
            print(f"- {warning}")

    changed_cases = [
        item for item in result["comparisons"] if item["change"] != "UNCHANGED"
    ]

    if changed_cases:
        print()
        print("Case changes:")

        for item in changed_cases:
            previous = item["previous_status"] or "N/A"
            current = item["current_status"] or "N/A"

            print(f"- {item['id']}: {previous} -> {current} ({item['change']})")


if __name__ == "__main__":
    main()
