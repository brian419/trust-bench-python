from answer_scorer import score_answer
from eval import compare_answers


def score_consistency_responses(
    attempts: list[dict],
    expected: str,
    accepted_answers: list[str] | None = None,
) -> list[dict]:
    results = []

    for attempt in attempts:
        if attempt["status"] == "ERROR":
            results.append(
                {
                    "attempt": attempt["attempt"],
                    "status": "ERROR",
                    "reason": "Model request failed",
                }
            )
            continue

        if attempt["status"] != "SUCCESS":
            raise ValueError("Unknown attempt status.")

        generated = attempt["generated"]

        if not isinstance(generated, str):
            raise ValueError("Generated response must be a string.")

        scoring = score_answer(
            expected,
            generated,
            accepted_answers,
        )

        results.append(
            {
                "attempt": attempt["attempt"],
                "generated": generated,
                "exact_match": compare_answers(expected, generated),
                "status": scoring["status"],
                "reason": scoring["reason"],
            }
        )

    return results
