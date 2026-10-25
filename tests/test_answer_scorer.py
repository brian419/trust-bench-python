from json import load
from pathlib import Path

from pytest import mark

from answer_scorer import score_answer
from eval import compare_answers


@mark.parametrize(
    "expected, generated, alternatives, expected_status, expected_reason",
    [
        ("Paris", " paris ", [], "PASS", "Exact match"),
        ("New York City", "NYC", ["NYC", "New York"], "PASS", "Accepted alternative"),
        ("8", "eight", ["eight"], "PASS", "Accepted alternative"),
        (
            "Paris",
            "London",
            [],
            "REVIEW",
            "No accepted answer matched; manual review required",
        ),
        (
            "Paris",
            "The capital is Paris.",
            [],
            "REVIEW",
            "No accepted answer matched; manual review required",
        ),
        ("Jupiter", "Jupiter", None, "PASS", "Exact match"),
    ],
)
def test_score_answer(
    expected, generated, alternatives, expected_status, expected_reason
):
    result = score_answer(expected, generated, alternatives)

    assert result["status"] == expected_status
    assert result["reason"] == expected_reason


def test_scoring_examples():
    dataset_path = Path(__file__).resolve().parent.parent / "scoring-examples.json"

    with dataset_path.open("r", encoding="utf-8") as file:
        examples = load(file)

    assert len(examples) == 8

    for example in examples:
        baseline_pass = compare_answers(example["expected"], example["generated"])

        improved_result = score_answer(
            example["expected"], example["generated"], example["accepted_answers"]
        )

        assert improved_result["status"] in ("PASS", "REVIEW")
        assert example["human_label"] in ("PASS", "FAIL", "REVIEW")

        if baseline_pass:
            assert improved_result["status"] == "PASS"
