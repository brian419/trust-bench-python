from unittest.mock import patch
from urllib.error import URLError

import pytest

from consistency_runner import run_consistency_experiment


def test_repeated_responses():
    with patch(
        "consistency_runner.generate_response",
        side_effect=["Paris", "London", "Paris"],
    ) as mock_generate:
        results = run_consistency_experiment(["What is the capital of France?"])

    assert mock_generate.call_count == 3
    assert len(results) == 1

    attempts = results[0]["attempts"]

    assert len(attempts) == 3
    assert attempts[0]["generated"] == "Paris"
    assert attempts[1]["generated"] == "London"

    assert results[0]["consistency"]["unique_responses"] == 2
    assert results[0]["consistency"]["disagreement_count"] == 1


def test_request_error():
    with patch(
        "consistency_runner.generate_response",
        side_effect=[
            "Paris",
            URLError("Connection refused"),
            "Paris",
        ],
    ):
        results = run_consistency_experiment(["France?"])

    attempts = results[0]["attempts"]

    assert attempts[1]["status"] == "ERROR"
    assert attempts[1]["generated"] is None

    assert results[0]["consistency"]["total_responses"] == 2
    assert results[0]["consistency"]["consistent"] is True


@pytest.mark.parametrize(
    "prompts, repetitions",
    [
        ([], 3),
        (["One", "Two", "Three", "Four"], 3),
        ([""], 3),
        (["Valid"], 0),
        (["Valid"], 4),
        (["Valid"], True),
    ],
)
def test_invalid_experiment(prompts, repetitions):
    with (
        patch("consistency_runner.generate_response") as mock_generate,
        pytest.raises(ValueError),
    ):
        run_consistency_experiment(prompts, repetitions)

    mock_generate.assert_not_called()


def test_invalid_model():
    with (
        patch("consistency_runner.generate_response") as mock_generate,
        pytest.raises(ValueError, match="Model must"),
    ):
        run_consistency_experiment(
            ["What is the capital of France?"],
            model="",
        )

    mock_generate.assert_not_called()


def test_invalid_model_response():
    with (
        patch(
            "consistency_runner.generate_response",
            return_value=None,
        ),
        pytest.raises(TypeError, match="Model response"),
    ):
        run_consistency_experiment(["What is the capital of France?"])


def test_generation_options_forwarded():
    options = {"temperature": 0.7, "seed": 42}

    with patch(
        "consistency_runner.generate_response",
        side_effect=["Paris", "Paris"],
    ) as mock_generate:
        results = run_consistency_experiment(
            ["What is the capital of France?"],
            repetitions=2,
            options=options,
        )

    assert mock_generate.call_count == 2
    assert results[0]["options"] == options
    assert results[0]["consistency"]["consistent"] is True

    mock_generate.assert_any_call(
        "What is the capital of France?",
        "gemma3:1b",
        options=options,
    )


def test_invalid_generation_options():
    with (
        patch("consistency_runner.generate_response") as mock_generate,
        pytest.raises(ValueError, match="Options must"),
    ):
        run_consistency_experiment(
            ["What is the capital of France?"],
            options="temperature=0.7",
        )

    mock_generate.assert_not_called()
