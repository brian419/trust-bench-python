from argparse import ArgumentParser
from datetime import datetime, timezone
from json import dump, JSONDecodeError, loads
from pathlib import Path
from sys import exit
from time import perf_counter
from urllib.error import HTTPError, URLError
from uuid import uuid4

from answer_scorer import score_answer
from eval import calculate_accuracy, compare_answers, validate_dataset
from ollama_client import generate_response, MalformedResponseError
from provenance import (
    ALTERNATIVE_SCORING_ID,
    bytes_sha256,
    EXACT_SCORING_ID,
    python_runtime_version,
)
from reference_validator import validate_reference_dataset


def main(
    filename="eval-read-live.json",
    model="gemma3:1b",
    report_dir: str | Path | None = None,
):
    is_reference_dataset = Path(filename).name == "eval-read-reference.json"

    try:
        with open(filename, "rb") as file:
            dataset_bytes = file.read()

        data = loads(dataset_bytes)
        dataset_hash = bytes_sha256(dataset_bytes)

    except FileNotFoundError as e:
        print("Error:", e)
        exit(1)

    except JSONDecodeError as e:
        print("Error:", e)
        exit(1)

    if is_reference_dataset:
        validation_errors = validate_reference_dataset(data)
    else:
        validation_errors = validate_dataset(data, require_response=False)

    if validation_errors:
        for error in validation_errors:
            print(error)
        exit(1)
    else:
        print("Live dataset validation passed!")

    run_timestamp = datetime.now(timezone.utc).isoformat()

    print("Run timestamp:", run_timestamp)

    metadata = {
        "model": model,
        "dataset": filename,
        "timestamp": run_timestamp,
        "provenance": {
            "dataset_sha256": dataset_hash,
            "primary_scoring": EXACT_SCORING_ID,
            "alternative_scoring": (
                ALTERNATIVE_SCORING_ID if is_reference_dataset else None
            ),
            "model_options": None,
            "model_version": None,
            "python_version": python_runtime_version(),
        },
    }

    print("Run metadata:", metadata)

    passed_count = 0
    failed_count = 0
    error_count = 0
    results = []

    for item in data:
        print("Test ID:", item["id"])

        request_start = perf_counter()
        result = None

        try:
            generated = generate_response(item["question"], model)

        except HTTPError as e:
            print("Result: ERROR")
            print("HTTP error:", e.code)
            error_count += 1

            result = {
                "id": item["id"],
                "question": item["question"],
                "expected": item["expected"],
                "generated": None,
                "status": "ERROR",
                "error": f"HTTP error: {e.code}",
            }

            results.append(result)

            continue

        except URLError as e:
            print("Result: ERROR")

            if isinstance(e.reason, TimeoutError):
                error_message = "Request timed out"
            else:
                error_message = f"Network error: {e.reason}"

            print(error_message)
            error_count += 1

            result = {
                "id": item["id"],
                "question": item["question"],
                "expected": item["expected"],
                "generated": None,
                "status": "ERROR",
                "error": error_message,
            }

            results.append(result)

            continue

        except TimeoutError:
            print("Result: ERROR")
            print("Request timed out")
            error_count += 1

            result = {
                "id": item["id"],
                "question": item["question"],
                "expected": item["expected"],
                "generated": None,
                "status": "ERROR",
                "error": "Request timed out",
            }

            results.append(result)

            continue

        except MalformedResponseError as e:
            print("Result: ERROR")
            print(str(e))
            error_count += 1

            result = {
                "id": item["id"],
                "question": item["question"],
                "expected": item["expected"],
                "generated": None,
                "status": "ERROR",
                "error": str(e),
            }

            results.append(result)
            continue

        finally:
            request_duration = perf_counter() - request_start
            print("Request duration:", round(request_duration, 3), "seconds")

            if result is not None:
                result["duration_seconds"] = round(request_duration, 3)

        print("Expected:", item["expected"])
        print("Generated:", generated)

        answers_match = compare_answers(item["expected"], generated)

        if answers_match:
            print("Result: PASS")
            passed_count += 1
        else:
            print("Result: FAIL")
            failed_count += 1

        result = {
            "id": item["id"],
            "question": item["question"],
            "expected": item["expected"],
            "generated": generated,
            "status": "PASS" if answers_match else "FAIL",
            "duration_seconds": round(request_duration, 3),
        }

        results.append(result)

    print("Collected results:", results)

    for item, result in zip(data, results):
        if "reference" in item:
            result["reference"] = item["reference"]

        if is_reference_dataset:
            if result["status"] == "ERROR":
                result["alternative_scoring"] = {
                    "status": "ERROR",
                    "reason": "Model request failed",
                }
            else:
                result["alternative_scoring"] = score_answer(
                    item["expected"],
                    result["generated"],
                    item.get("accepted_answers", []),
                )

    accuracy = calculate_accuracy(passed_count, failed_count)

    summary = {
        "passed": passed_count,
        "failed": failed_count,
        "errors": error_count,
        "accuracy": accuracy,
    }

    report = {"metadata": metadata, "summary": summary, "results": results}

    reports_dir = Path("reports") if report_dir is None else Path(report_dir)
    report_filename = f"evaluation-{uuid4().hex}.json"
    report_path = reports_dir / report_filename

    try:
        reports_dir.mkdir(parents=True, exist_ok=True)

        with report_path.open("x", encoding="utf-8") as file:
            dump(report, file, indent=4)

    except OSError as e:
        print("Error saving report:", e)
        exit(1)

    print("Report saved to:", report_path)

    print("Passed:", passed_count)
    print("Failed:", failed_count)
    print("Errors:", error_count)

    if accuracy is None:
        print("Accuracy: N/A")
    else:
        print("Accuracy:", round(accuracy, 2))

    print("Report:", report)
    return report


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Evaluate answers using a local Ollama model."
    )
    parser.add_argument(
        "--dataset",
        default="eval-read-live.json",
        help="JSON dataset to evaluate.",
    )
    parser.add_argument(
        "--model",
        default="gemma3:1b",
        help="Installed Ollama model to use.",
    )

    args = parser.parse_args()
    main(filename=args.dataset, model=args.model)
