import json
from pathlib import Path

from eval import compare_answers
from answer_scorer import score_answer


def compare_scorers(filename="scoring-examples.json"):
    with Path(filename).open("r", encoding="utf-8") as file:
        examples = json.load(file)

    results = []
    exact_passes = 0
    alternative_passes = 0
    review_count = 0

    for example in examples:
        exact_status = (
            "PASS"
            if compare_answers(example["expected"], example["generated"])
            else "FAIL"
        )

        improved = score_answer(
            example["expected"],
            example["generated"],
            example["accepted_answers"]
        )

        if exact_status == "PASS":
            exact_passes += 1

        if improved["status"] == "PASS":
            alternative_passes += 1

        if improved["status"] == "REVIEW":
            review_count += 1

        result = {
            "id": example["id"],
            "human_label": example["human_label"],
            "exact_status": exact_status,
            "improved_status": improved["status"],
            "reason": improved["reason"]
        }

        results.append(result)

        print(
            example["id"],
            "| Human:", example["human_label"],
            "| Exact:", exact_status,
            "| Improved:", improved["status"]
        )

    summary = {
        "total": len(examples),
        "exact_passes": exact_passes,
        "alternative_passes": alternative_passes,
        "review_count": review_count
    }

    print("\nComparison summary:", summary)

    return {
        "summary": summary,
        "results": results
    }

if __name__ == "__main__":
    compare_scorers()
