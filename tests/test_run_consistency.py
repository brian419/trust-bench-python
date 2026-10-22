import json
from unittest.mock import patch

from run_consistency import main, MODEL, OPTIONS, PROMPTS, REPETITIONS


def test_consistency_report_saved(tmp_path):
    fake_results = [
        {
            "prompt": PROMPTS[0],
            "model": MODEL,
            "options": OPTIONS.copy(),
            "attempts": [
                {
                    "attempt": 1,
                    "status": "SUCCESS",
                    "generated": "kilogram",
                }
            ],
            "consistency": {
                "total_responses": 1,
                "unique_responses": 1,
                "disagreement_count": 0,
                "consistent": True,
            },
        }
    ]

    with patch(
        "run_consistency.run_consistency_experiment",
        return_value=fake_results,
    ) as mock_runner:
        report_path = main(report_dir=tmp_path)

    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["metadata"]["model"] == MODEL
    assert report["metadata"]["repetitions"] == REPETITIONS
    assert report["metadata"]["prompt_count"] == 3
    assert report["metadata"]["options"] == OPTIONS
    assert report["metadata"]["timestamp_utc"]
    assert report["results"] == fake_results

    mock_runner.assert_called_once_with(
        prompts=PROMPTS,
        repetitions=3,
        model=MODEL,
        options=OPTIONS,
    )


def test_consistency_reports_do_not_overwrite(tmp_path):
    with patch(
        "run_consistency.run_consistency_experiment",
        return_value=[],
    ):
        first_path = main(report_dir=tmp_path)
        second_path = main(report_dir=tmp_path)

    assert first_path != second_path
    assert first_path.exists()
    assert second_path.exists()
