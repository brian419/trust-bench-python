import sys
import json
from eval import validate_dataset, compare_answers, calculate_accuracy
from ollama_client import generate_response
from urllib.error import HTTPError, URLError


def main():
    filename = "eval-read-live.json"

    try:    
        with open(filename, "r") as file:
            data = json.load(file)

    except FileNotFoundError as e:
        print("Error:", e)
        sys.exit(1)

    except json.JSONDecodeError as e:
        print("Error:", e)
        sys.exit(1)

    validation_errors = validate_dataset(data, require_response=False)

    if validation_errors:
        for error in validation_errors:
            print(error)
        sys.exit(1)
    else:
        print("Live dataset validation passed!")

    model = "gemma3:1b"

    passed_count = 0
    failed_count = 0
    error_count = 0

    for item in data:
        print("Test ID:", item["id"])

        try:    
            generated = generate_response(
                item["question"],
                model
            )

        except HTTPError as e:
            print("Result: ERROR")
            print("HTTP error:", e.code)
            error_count += 1
            continue

        except URLError as e:
            print("Result: ERROR")

            if isinstance(e.reason, TimeoutError):
                print("Request timed out")
            else:        
                print("Network error:", e.reason)

            error_count += 1
            continue

        except TimeoutError:
            print("Result: ERROR")
            print("Request timed out")
            error_count += 1
            continue

        print("Expected:", item["expected"])
        print("Generated:", generated)

        answers_match = compare_answers(item["expected"], generated)

        if answers_match:
            print("Result: PASS")
            passed_count += 1
        else:
            print("Result: FAIL")
            failed_count += 1


    accuracy = calculate_accuracy(passed_count, failed_count)

    print("Passed:", passed_count)
    print("Failed:", failed_count)
    print("Errors:", error_count)

    if accuracy is None:
        print("Accuracy: N/A")
    else:
        print("Accuracy:", round(accuracy, 2))

if __name__ == "__main__":
    main()
