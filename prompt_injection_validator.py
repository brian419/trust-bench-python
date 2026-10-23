def validate_injection_dataset(data: object) -> list[str]:
    """Validate a dataset of synthetic prompt-injection scenarios."""

    errors = []

    if not isinstance(data, list):
        return ["ERROR: Dataset must be a list."]

    if not data:
        return ["ERROR: Dataset cannot be empty."]

    required_fields = (
        "id",
        "trusted_instruction",
        "untrusted_text",
        "expected",
        "attack_goal",
        "attack_target"
    )

    seen_ids = set()

    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            errors.append(f"ERROR: Scenario #{index} must be a dictionary.")
            continue

        for field in required_fields:
            if field not in item:
                errors.append(
                    f"ERROR: Scenario #{index} missing required field '{field}'."
                )
                continue

            value = item[field]

            if not isinstance(value, str):
                errors.append(
                    f"ERROR: Scenario #{index} field '{field}' must be a string."
                )
            elif not value.strip():
                errors.append(
                    f"ERROR: Scenario #{index} field '{field}' cannot be empty."
                )

        scenario_id = item.get("id")

        if isinstance(scenario_id, str) and scenario_id.strip():
            if scenario_id in seen_ids:
                errors.append(
                    f"ERROR: Scenario #{index} has duplicate ID '{scenario_id}'."
                )
            else:
                seen_ids.add(scenario_id)

    return errors
