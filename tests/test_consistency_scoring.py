from pytest import raises

from consistency_scoring import score_consistency_responses


def test_exact_match():
    attempts = [
        {
            "attempt": 1,
            "status": "SUCCESS",
            "generated": " Canberra ",
        }
    ]

    results = score_consistency_responses(
        attempts,
        expected="Canberra",
    )

    assert results[0]["status"] == "PASS"
    assert results[0]["exact_match"] is True
    assert results[0]["reason"] == "Exact match"


def test_accepted_alternative():
    attempts = [
        {
            "attempt": 1,
            "status": "SUCCESS",
            "generated": "T\n",
        }
    ]

    results = score_consistency_responses(
        attempts,
        expected="Thymine",
        accepted_answers=["T"],
    )

    assert results[0]["status"] == "PASS"
    assert results[0]["exact_match"] is False
    assert results[0]["reason"] == "Accepted alternative"


def test_unmatched_response_requires_review():
    attempts = [
        {
            "attempt": 1,
            "status": "SUCCESS",
            "generated": "gram",
        }
    ]

    results = score_consistency_responses(
        attempts,
        expected="kilogram",
    )

    assert results[0]["status"] == "REVIEW"
    assert results[0]["exact_match"] is False


def test_request_error():
    attempts = [
        {
            "attempt": 1,
            "status": "ERROR",
            "generated": None,
            "error": "Connection refused",
        }
    ]

    results = score_consistency_responses(
        attempts,
        expected="kilogram",
    )

    assert results[0]["status"] == "ERROR"
    assert results[0]["reason"] == "Model request failed"


def test_unknown_status():
    attempts = [
        {
            "attempt": 1,
            "status": "UNKNOWN",
            "generated": "Paris",
        }
    ]

    with raises(ValueError, match="Unknown attempt status"):
        score_consistency_responses(attempts, "Paris")


def test_invalid_generated_response():
    attempts = [
        {
            "attempt": 1,
            "status": "SUCCESS",
            "generated": None,
        }
    ]

    with raises(ValueError, match="Generated response"):
        score_consistency_responses(attempts, "Paris")
