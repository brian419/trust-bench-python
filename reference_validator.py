from datetime import datetime
from eval import validate_dataset


def validate_reference_dataset(data: object) -> list[str]:

    errors = validate_dataset(data, require_response=False)

    if not isinstance(data, list):
        return errors

    for item in data:
        if not isinstance(item, dict):
            continue

        if "reference" not in item:
            errors.append("ERROR: Missing field of 'reference'.")
            continue

        reference = item["reference"]

        if isinstance(reference, dict):
            if "url" not in reference:
                errors.append("ERROR: Missing 'url' field.")
            elif not isinstance(reference["url"], str):
                errors.append("ERROR: The 'url' field must be a string.")
            elif not reference["url"].strip():
                errors.append("ERROR: The 'url' field cannot be empty")
            if "verified_date" not in reference:
                errors.append("ERROR: Missing 'verified_date' field.")
            elif not isinstance(reference["verified_date"], str):
                errors.append("ERROR: The 'verified_date' field must be a string.")
            elif not reference["verified_date"].strip():
                errors.append("ERROR: The 'verified_date' field cannot be empty")
            else:
                try:
                    parsed_date = datetime.strptime(
                        reference["verified_date"], "%Y-%m-%d"
                    )
                    if parsed_date.strftime("%Y-%m-%d") != reference["verified_date"]:
                        errors.append("ERROR: Date must use YYYY-MM-DD format.")

                except ValueError:
                    errors.append("ERROR: Invalid verification date.")
        else:
            errors.append("ERROR: The field 'reference' must be a dictionary.")

    return errors


temp_data_with_reference = [
    {
        "id": "fact_001",
        "question": "What is the chemical symbol for gold? Answer with only the symbol.",
        "expected": "Au",
        "reference": {
            "url": "https://periodic-table.rsc.org/",
            "verified_date": "2026-10-21",
        },
    }
]

temp_data_without_reference = [
    {
        "id": "fact_001",
        "question": "What is the chemical symbol for gold? Answer with only the symbol.",
        "expected": "Au",
    }
]


if __name__ == "__main__":
    response_for_valid = validate_reference_dataset(temp_data_with_reference)
    response_for_invalid = validate_reference_dataset(temp_data_without_reference)
    response_for_wrong_type = validate_reference_dataset(
        ["This is a string, not a dictionary"]
    )

    print("VALID:", response_for_valid)
    print("INVALID:", response_for_invalid)
    print("WRONG TYPE:", response_for_wrong_type)

    print("STARTING REFERENCE:", validate_reference_dataset([{"reference": "hello"}]))

    print(
        "MISSING URL:",
        validate_reference_dataset([{"reference": {"verified_date": "2026-10-21"}}]),
    )

    print(
        "MISSING DATE:",
        validate_reference_dataset([{"reference": {"url": "https://example.com"}}]),
    )

    print(
        "INVALID FIELD TYPES:",
        validate_reference_dataset(
            [{"reference": {"url": 123, "verified_date": None}}]
        ),
    )

    print(
        "EMPTY FIELDS:",
        validate_reference_dataset(
            [{"reference": {"url": "    ", "verified_date": ""}}]
        ),
    )

    print(
        "INVALID DATE:",
        validate_reference_dataset(
            [
                {
                    "reference": {
                        "url": "https://example.com",
                        "verified_date": "2026-02-30",
                    }
                }
            ]
        ),
    )

    print(
        "WRONG DATE FORMAT:",
        validate_reference_dataset(
            [
                {
                    "reference": {
                        "url": "https://example.com",
                        "verified_date": "10/21/2026",
                    }
                }
            ]
        ),
    )
