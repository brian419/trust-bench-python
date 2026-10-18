import json

with open("eval-read.json", "r") as file:
    data = json.load(file)

# print(data[0]["expected"])
# print(data[0]["response"])

# if data[0]["expected"] == data[0]["response"]:
#     print("PASS: The answers match!")
# else: print("FAIL: The answers don't match!")

passed_count = 0
failed_count = 0
accuracy_percentage = 0

for item in data:
    # print(item["id"])
    if (item["expected"].lower().strip() == item["response"].lower().strip()):
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


## what we have done so far:
# Iterates through the test cases.
# Compares the expected response with the actual response.
# Records which tests passed and failed.
# Prints the overall accuracy percentage.
# Answer normalization; 


## what we need to do now:
# milestone 2 - automated testing with pytest

