from json import dumps
from pathlib import Path
from subprocess import run
from sys import executable


SCRIPT = Path(__file__).resolve().parent.parent / "compare_scorers.py"


def test_custom_dataset_used(tmp_path):
    dataset = tmp_path / "custom.json"
    dataset.write_text(
        dumps(
            [
                {
                    "id": "custom_001",
                    "expected": "Paris",
                    "generated": "Paris",
                    "accepted_answers": [],
                    "human_label": "PASS",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = run(
        [executable, str(SCRIPT), str(dataset)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "custom_001" in result.stdout
    assert "'total': 1" in result.stdout


def test_missing_dataset_returns_failure(tmp_path):
    missing = tmp_path / "missing.json"

    result = run(
        [executable, str(SCRIPT), str(missing)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "No such file or directory" in result.stderr
    assert "Error reading scoring dataset:" in result.stderr
    assert "Traceback" not in result.stderr


def test_malformed_dataset_returns_clean_error(tmp_path):
    dataset = tmp_path / "invalid.json"
    dataset.write_text('{"broken": ', encoding="utf-8")

    result = run(
        [executable, str(SCRIPT), str(dataset)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Error reading scoring dataset:" in result.stderr
    assert "Traceback" not in result.stderr
