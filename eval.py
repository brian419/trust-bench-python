import json


def compare_answers(expected: str, response: str) -> bool:
    if expected.lower().strip() == response.lower().strip():
        return True
    else:
        return False


if __name__ == "__main__":

    with open("eval-read.json", "r") as file:
        data = json.load(file)

    passed_count = 0
    failed_count = 0
    accuracy_percentage = 0
        
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

    if (passed_count + failed_count > 0):
        accuracy_percentage = ((passed_count) / (passed_count + failed_count)) * 100
        print("Accuracy:", round(accuracy_percentage, 2))
    else:
        print("Accuracy: N/A")
