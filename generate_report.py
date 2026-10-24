"""Generate readable TrustBench reports from saved evaluations."""

import argparse
import json
from pathlib import Path
from report_loader import load_report
from report_formatter import format_live_report


def generate_text_report(filename: str) -> str:
    """Load and format a saved live-evaluation report."""

    report = load_report(filename)

    metadata = report["metadata"]
    results = report["results"]

    # Older live reports may not contain provenance metadata.
    # Recognize them by their original live-evaluation structure.
    required_metadata = ("model", "dataset", "timestamp")

    if not all(
        isinstance(metadata.get(field), str) and metadata[field].strip()
        for field in required_metadata
    ):
        raise ValueError(
            "Text report generation requires a recognized live-evaluation report."
        )

    # Verify the complete result structure before formatting.
    required_result_fields = (
        "id",
        "question",
        "expected",
        "status",
    )

    for result in results:
        if not isinstance(result, dict):
            raise ValueError("Each report result must be an object.")

        if not all(field in result for field in required_result_fields):
            raise ValueError("Live-evaluation results contain missing required fields.")

        for field in ("id", "question", "expected"):
            if not isinstance(result[field], str) or not result[field].strip():
                raise ValueError(
                    f"Live-evaluation result field '{field}' "
                    "must be a non-empty string."
                )

        status = result["status"]

        if status in {"PASS", "FAIL"}:
            if not isinstance(result.get("generated"), str):
                raise ValueError(
                    "Scored live-evaluation results must contain "
                    "a string generated response."
                )

        if result["status"] not in {"PASS", "FAIL", "ERROR"}:
            raise ValueError(f"Unknown result status: {result['status']}")

    return format_live_report(report)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a readable TrustBench evaluation report."
    )

    parser.add_argument(
        "report",
        help="Path to an existing JSON evaluation report.",
    )

    parser.add_argument(
        "--output",
        help="Save the formatted report to a UTF-8 text file.",
    )

    args = parser.parse_args()

    try:
        output = generate_text_report(args.report)
    except FileNotFoundError as error:
        parser.error(f"Report file not found: {error.filename}")
    except json.JSONDecodeError as error:
        parser.error(
            f"Invalid JSON report: {error.msg} "
            f"(line {error.lineno}, column {error.colno})"
        )
    except UnicodeError:
        parser.error("Report file is not valid UTF-8 text.")
    except ValueError as error:
        parser.error(str(error))

    if args.output:
        try:
            output_path = Path(args.output)

            if output_path.exists():
                parser.error(f"Output file already exists: {output_path}")

            with output_path.open("x", encoding="utf-8") as file:
                file.write(output)

        except FileExistsError:
            parser.error(f"Output file already exists: {args.output}")
        except OSError as error:
            parser.error(f"Could not save report: {error}")

        print(f"Report saved to: {output_path}")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
