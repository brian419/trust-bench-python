from pytest import raises

from consistency_review import review_prompt


def make_prompt_result():
    return {
        "prompt": "What is the SI base unit of mass?",
        "attempts": [
            {
                "attempt": 1,
                "status": "SUCCESS",
                "generated": "gram",
            },
            {
                "attempt": 2,
                "status": "SUCCESS",
                "generated": "kilogram",
            },
        ],
        "consistency": {
            "total_responses": 2,
            "unique_responses": 2,
            "disagreement_count": 1,
            "consistent": False,
        },
    }


def test_reviewed_prompt():
    result = review_prompt(
        make_prompt_result(),
        expected="kilogram",
        human_labels={
            1: "INCORRECT",
            2: "CORRECT",
        },
    )

    assert result["reviewed_attempts"][0]["status"] == "REVIEW"
    assert result["reviewed_attempts"][0]["classification"] == "INCORRECT"

    assert result["reviewed_attempts"][1]["status"] == "PASS"
    assert result["reviewed_attempts"][1]["classification"] == "CORRECT"

    assert result["consistency"]["disagreement_count"] == 1


def test_missing_human_labels():
    result = review_prompt(
        make_prompt_result(),
        expected="kilogram",
    )

    assert all(
        item["classification"] == "NEEDS_REVIEW" for item in result["reviewed_attempts"]
    )


def test_unknown_attempt_label():
    with raises(ValueError, match="unknown attempt"):
        review_prompt(
            make_prompt_result(),
            expected="kilogram",
            human_labels={3: "INCORRECT"},
        )


def test_duplicate_attempt_numbers():
    data = make_prompt_result()
    data["attempts"][1]["attempt"] = 1

    with raises(ValueError, match="Duplicate attempt"):
        review_prompt(data, expected="kilogram")


def test_cannot_label_request_error():
    data = make_prompt_result()

    data["attempts"][0] = {
        "attempt": 1,
        "status": "ERROR",
        "generated": None,
        "error": "Connection refused",
    }

    with raises(ValueError, match="request error"):
        review_prompt(
            data,
            expected="kilogram",
            human_labels={1: "INCORRECT"},
        )


def test_request_error_classified_automatically():
    data = make_prompt_result()

    data["attempts"][0] = {
        "attempt": 1,
        "status": "ERROR",
        "generated": None,
        "error": "Connection refused",
    }

    result = review_prompt(data, expected="kilogram")

    assert result["reviewed_attempts"][0]["status"] == "ERROR"
    assert result["reviewed_attempts"][0]["classification"] == "REQUEST_ERROR"
    assert result["reviewed_attempts"][0]["classification_source"] == "automatic"
