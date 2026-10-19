import json
import sys

def compare_answers(expected: str, response: str) -> bool:
    if expected.lower().strip() == response.lower().strip():
        return True
    else:
        return False


def calculate_accuracy(passed_count: int, failed_count: int):
    if passed_count + failed_count == 0:
        return None
    accuracy_percentage = ((passed_count) / (passed_count + failed_count)) * 100

    return accuracy_percentage


def validate_dataset(data: object) -> list[str]:
    validation_errors = []

    if not isinstance(data, list):
        return ["Error: JSON must contain a list of test cases."]

    for case_number, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            validation_errors.append(f"Error: Test case #{case_number} must be a dictionary.")
            continue

        if "id" not in item:
            validation_errors.append(f"Error: Test case #{case_number}: Missing required field 'id'.")
        elif not isinstance(item["id"], str):
            validation_errors.append(f"Error: Test case #{case_number}: Field 'id' must be a string.")
    
        if "question" not in item:
            validation_errors.append(f"Error: Test case #{case_number}: Missing required field 'question'.")
        elif not isinstance(item["question"], str):
            validation_errors.append(f"Error: Test case #{case_number}: Field 'question' must be a string.")
    
        if "expected" not in item:
            validation_errors.append(f"Error: Test case #{case_number}: Missing required field 'expected'.")
        elif not isinstance(item["expected"], str):
            validation_errors.append(f"Error: Test case #{case_number}: Field 'expected' must be a string.")
    
        if "response" not in item:
            validation_errors.append(f"Error: Test case #{case_number}: Missing required field 'response'.")
        elif not isinstance(item["response"], str):
            validation_errors.append(f"Error: Test case #{case_number}: Field 'response' must be a string.")
    
    return validation_errors


if __name__ == "__main__":
    filename = "eval-read-valid.json"

    if len(sys.argv) > 1:
        filename = sys.argv[1]

    try:
        with open(filename, "r") as file:
            data = json.load(file)
    except FileNotFoundError as e:
        print("Error:", e)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print("Error:", e)
        sys.exit(1)

    validation_errors = validate_dataset(data)

    if len(validation_errors) != 0:
        for error in validation_errors:
            print(error)

        print("Validation failed:", len(validation_errors), "error(s) found.")
        sys.exit(1)

    passed_count = 0
    failed_count = 0

    for item in data:
        answers_match = compare_answers(item["expected"], item["response"])
        if answers_match == True:
            print("Test ID:", item["id"], ";", "PASS: The answers match!")
            passed_count += 1
        else: 
            print("Test ID:", item["id"], ";", "FAIL: The answers don't match!")
            failed_count += 1


    if (passed_count == 1):
        print("Passed", passed_count, "test")
    else:
        print("Passed", passed_count, "tests")

    if (failed_count == 1):
        print("Failed", failed_count, "test")
    else:
        print("Failed", failed_count, "tests")

    accuracy = calculate_accuracy(passed_count, failed_count)

    if (accuracy is None):
        print("Accuracy: N/A")
    else:
        print("Accuracy:", round(accuracy, 2))
