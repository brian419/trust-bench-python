from json import load, loads
from platform import python_version
from unittest.mock import patch

from provenance import consistency_inputs_sha256
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

    report = loads(report_path.read_text(encoding="utf-8"))

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


def test_consistency_report_records_model_provenance(tmp_path, monkeypatch):
    fake_results = []

    monkeypatch.setattr(
        "run_consistency.run_consistency_experiment",
        lambda **kwargs: fake_results,
    )

    report_path = main(report_dir=tmp_path)

    with report_path.open("r", encoding="utf-8") as file:
        report = load(file)

    metadata = report["metadata"]

    assert metadata["provenance"]["model_options"] == {
        "temperature": 0.7,
        "seed": 42,
        "num_predict": 64,
    }
    assert metadata["provenance"]["model_version"] is None
    assert metadata["options"] == metadata["provenance"]["model_options"]

    assert metadata["provenance"]["inputs_sha256"] == (
        consistency_inputs_sha256(PROMPTS, REPETITIONS)
    )
    assert metadata["provenance"]["scoring_method"] is None
    assert metadata["provenance"]["prompt_format"] == "plain-question-v1"
    assert metadata["provenance"]["python_version"] == python_version()
