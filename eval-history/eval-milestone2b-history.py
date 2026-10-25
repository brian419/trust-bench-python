from json import load


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


if __name__ == "__main__":

    with open("eval-read.json", "r") as file:
        data = load(file)

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
