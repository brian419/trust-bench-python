from collections import Counter
from datetime import datetime, timezone
from json import dump
from pathlib import Path
from uuid import uuid4

from consistency_report_reader import load_verified_report
from consistency_review import review_prompt

SOURCE_REPORT = Path("reports/consistency-f0503c787fec46e1a4052f5c17743f5d.json")

SOURCE_SHA256 = "b4a4a5cd5e2c04f98e585bca144efb5cd9e06bc44c0e2be7d9641d89d41fd70c"

REVIEW_SPEC = [
    {
        "prompt": "What is the SI base unit of mass? Answer with only the unit name.",
        "expected": "kilogram",
        "accepted_answers": [],
        "human_labels": {
            1: "INCORRECT",
            2: "INCORRECT",
            3: "INCORRECT",
        },
    },
    {
        "prompt": "What is the capital of Australia? Answer with only the city name.",
        "expected": "Canberra",
        "accepted_answers": [],
        "human_labels": {
            1: "CORRECT",
            2: "CORRECT",
            3: "CORRECT",
        },
    },
    {
        "prompt": "Which DNA base pairs with adenine? Answer with only the base name.",
        "expected": "Thymine",
        "accepted_answers": ["T"],
        "human_labels": {
            1: "FORMATTING_MISMATCH",
            2: "INCORRECT",
            3: "INCORRECT",
        },
    },
]


def main(
    report_path: Path = SOURCE_REPORT,
    output_dir: Path = Path("reports"),
) -> Path:
    original = load_verified_report(report_path, SOURCE_SHA256)

    if original["metadata"].get("model") != "gemma3:1b":
        raise ValueError("Unexpected model in source report.")

    if len(original["results"]) != len(REVIEW_SPEC):
        raise ValueError("Unexpected number of prompts.")

    reviewed_results = []

    for prompt_result, specification in zip(
        original["results"],
        REVIEW_SPEC,
    ):
        if prompt_result["prompt"] != specification["prompt"]:
            raise ValueError("Source report prompts do not match review.")

        attempt_numbers = [attempt["attempt"] for attempt in prompt_result["attempts"]]

        if sorted(attempt_numbers) != [1, 2, 3]:
            raise ValueError("Expected exactly three attempts per prompt.")

        reviewed_results.append(
            review_prompt(
                prompt_result,
                expected=specification["expected"],
                accepted_answers=specification["accepted_answers"],
                human_labels=specification["human_labels"],
            )
        )

    counts = Counter(
        attempt["classification"]
        for result in reviewed_results
        for attempt in result["reviewed_attempts"]
    )

    analysis = {
        "metadata": {
            "source_report": report_path.name,
            "source_sha256": SOURCE_SHA256,
            "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
            "model": original["metadata"]["model"],
            "generation_options": original["metadata"].get("options"),
            "review_method": "Human labels for verified source report",
        },
        "summary": {
            "total_attempts": sum(counts.values()),
            "classification_counts": dict(sorted(counts.items())),
        },
        "results": reviewed_results,
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"consistency-analysis-{uuid4().hex}.json"

    with output_path.open("x", encoding="utf-8") as file:
        dump(analysis, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print(f"Saved analyzed report: {output_path}")
    return output_path


if __name__ == "__main__":
    main()
