import pytest

from failure_classifier import classify_failures


def make_attempt(status="REVIEW", number=1):
    return {
        "attempt": number,
        "status": status,
    }


def test_correct_human_label():
    result = classify_failures(
        [make_attempt("PASS")],
        {1: "CORRECT"},
    )

    assert result[0]["classification"] == "CORRECT"
    assert result[0]["classification_source"] == "human"


def test_incorrect_human_label():
    result = classify_failures(
        [make_attempt()],
        {1: "INCORRECT"},
    )

    assert result[0]["classification"] == "INCORRECT"


def test_formatting_mismatch():
    result = classify_failures(
        [make_attempt("PASS")],
        {1: "FORMATTING_MISMATCH"},
    )

    assert result[0]["classification"] == "FORMATTING_MISMATCH"
    assert result[0]["score_status"] == "PASS"


def test_unreviewed_response():
    result = classify_failures([make_attempt("PASS")])

    assert result[0]["classification"] == "NEEDS_REVIEW"
    assert result[0]["classification_source"] == "unreviewed"


def test_request_error():
    result = classify_failures(
        [make_attempt("ERROR")],
    )

    assert result[0]["classification"] == "REQUEST_ERROR"
    assert result[0]["classification_source"] == "automatic"


def test_unknown_human_label():
    with pytest.raises(
        ValueError,
        match="Unknown classification label",
    ):
        classify_failures(
            [make_attempt()],
            {1: "PERFECT"},
        )


def test_unknown_scoring_status():
    with pytest.raises(
        ValueError,
        match="Unknown scoring status",
    ):
        classify_failures([make_attempt("UNKNOWN")])


def test_needs_review_cannot_be_human_label():
    with pytest.raises(
        ValueError,
        match="Unknown classification label",
    ):
        classify_failures(
            [make_attempt()],
            {1: "NEEDS_REVIEW"},
        )
