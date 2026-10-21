from consistency_analyzer import analyze_consistency


def test_identical_responses():
    responses = ["Paris", "paris", " PARIS "]

    result = analyze_consistency(responses)

    assert result["total_responses"] == 3
    assert result["unique_responses"] == 1
    assert result["disagreement_count"] == 0
    assert result["consistent"] is True


def test_different_responses():
    responses = ["kilogram", "gram", "kilogram"]

    result = analyze_consistency(responses)

    assert result["total_responses"] == 3
    assert result["unique_responses"] == 2
    assert result["disagreement_count"] == 1
    assert result["consistent"] is False


def test_empty_responses():
    result = analyze_consistency([])

    assert result["total_responses"] == 0
    assert result["unique_responses"] == 0
    assert result["disagreement_count"] == 0
    assert result["consistent"] is None
