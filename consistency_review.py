from consistency_scoring import score_consistency_responses
from failure_classifier import classify_failures


def review_prompt(
    prompt_result: dict,
    expected: str,
    accepted_answers: list[str] | None = None,
    human_labels: dict[int, str] | None = None,
) -> dict:
    attempts = prompt_result["attempts"]

    attempt_numbers = [attempt["attempt"] for attempt in attempts]

    if len(attempt_numbers) != len(set(attempt_numbers)):
        raise ValueError("Duplicate attempt numbers.")

    if human_labels is not None:
        if not isinstance(human_labels, dict):
            raise ValueError("Human labels must be a dictionary.")

        unknown_numbers = set(human_labels) - set(attempt_numbers)

        if unknown_numbers:
            raise ValueError("Human label references an unknown attempt.")

        error_numbers = {
            attempt["attempt"] for attempt in attempts if attempt["status"] == "ERROR"
        }

        if set(human_labels) & error_numbers:
            raise ValueError("Cannot assign a human label to a request error.")

    scored = score_consistency_responses(
        attempts,
        expected,
        accepted_answers,
    )

    classified = classify_failures(scored, human_labels)

    classifications = {item["attempt"]: item for item in classified}

    reviewed_attempts = []

    for scored_attempt in scored:
        number = scored_attempt["attempt"]

        reviewed_attempts.append(
            {
                **scored_attempt,
                "classification": classifications[number]["classification"],
                "classification_source": classifications[number][
                    "classification_source"
                ],
            }
        )

    return {
        "prompt": prompt_result["prompt"],
        "expected": expected,
        "accepted_answers": (
            accepted_answers.copy() if accepted_answers is not None else []
        ),
        "consistency": prompt_result["consistency"].copy(),
        "reviewed_attempts": reviewed_attempts,
    }
