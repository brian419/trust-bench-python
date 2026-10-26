VALID_LABELS = {
    "CORRECT",
    "INCORRECT",
    "FORMATTING_MISMATCH",
    "UNSUPPORTED",
    "AMBIGUOUS",
}


def classify_failures(
    scored_attempts: list[dict],
    human_labels: dict[int, str] | None = None,
) -> list[dict]:
    if human_labels is None:
        human_labels = {}

    if not isinstance(human_labels, dict):
        raise ValueError("Human labels must be a dictionary.")

    results = []

    for attempt in scored_attempts:
        attempt_number = attempt["attempt"]
        score_status = attempt["status"]

        if score_status == "ERROR":
            classification = "REQUEST_ERROR"
            source = "automatic"
        elif score_status in {"PASS", "REVIEW"}:
            classification = human_labels.get(
                attempt_number,
                "NEEDS_REVIEW",
            )
            source = "human" if attempt_number in human_labels else "unreviewed"

            if attempt_number in human_labels and classification not in VALID_LABELS:
                raise ValueError("Unknown classification label.")

        else:
            raise ValueError("Unknown scoring status.")

        results.append(
            {
                "attempt": attempt_number,
                "score_status": score_status,
                "classification": classification,
                "classification_source": source,
            }
        )

    return results
