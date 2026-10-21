from eval import compare_answers


def score_answer(expected: str, generated: str, accepted_answers: list[str] | None = None) -> dict:
    if compare_answers(expected, generated):
        return {
            "status": "PASS",
            "reason": "Exact match"
        }

    if accepted_answers:
        for alternative in accepted_answers:
            if compare_answers(alternative, generated):
                return {
                    "status": "PASS",
                    "reason": "Accepted alternative"
                }

    return {
        "status": "REVIEW",
        "reason": "No accepted answer matched; manual review required"
    }
