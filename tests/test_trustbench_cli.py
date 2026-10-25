from sys import executable
from unittest.mock import patch

from pytest import mark, raises

from trustbench import main, PROJECT_ROOT


def test_offline_default():
    with patch("trustbench.run") as mock_run:
        mock_run.return_value.returncode = 0

        result = main(["offline"])

    assert result == 0
    mock_run.assert_called_once_with(
        [executable, str(PROJECT_ROOT / "eval.py")],
        check=False,
    )


def test_offline_custom_dataset(tmp_path):
    dataset = tmp_path / "custom.json"
    dataset.write_text("[]", encoding="utf-8")

    with patch("trustbench.run") as mock_run:
        mock_run.return_value.returncode = 0

        result = main(
            [
                "offline",
                "--dataset",
                str(dataset),
            ]
        )

    assert result == 0
    mock_run.assert_called_once_with(
        [
            executable,
            str(PROJECT_ROOT / "eval.py"),
            str(dataset),
        ],
        check=False,
    )


def test_scorers_default():
    with patch("trustbench.run") as mock_run:
        mock_run.return_value.returncode = 0

        result = main(["scorers"])

    assert result == 0
    mock_run.assert_called_once_with(
        [
            executable,
            str(PROJECT_ROOT / "compare_scorers.py"),
        ],
        check=False,
    )


def test_scorers_custom_dataset(tmp_path):
    dataset = tmp_path / "examples.json"
    dataset.write_text("[]", encoding="utf-8")

    with patch("trustbench.run") as mock_run:
        mock_run.return_value.returncode = 0

        result = main(
            [
                "scorers",
                "--dataset",
                str(dataset),
            ]
        )

    assert result == 0
    mock_run.assert_called_once_with(
        [
            executable,
            str(PROJECT_ROOT / "compare_scorers.py"),
            str(dataset),
        ],
        check=False,
    )


def test_error_exit_code_preserved():
    with patch("trustbench.run") as mock_run:
        mock_run.return_value.returncode = 1

        result = main(["offline"])

    assert result == 1


@mark.parametrize(
    "arguments",
    [
        [],
        ["unknown"],
        ["offline", "--unknown"],
    ],
)
def test_invalid_commands_exit(arguments):
    with raises(SystemExit) as error:
        main(arguments)

    assert error.value.code == 2


def test_help_lists_commands(capsys):
    with raises(SystemExit) as error:
        main(["--help"])

    assert error.value.code == 0

    output = capsys.readouterr().out

    assert "offline" in output
    assert "scorers" in output
    assert "live" in output
    assert "consistency" in output
    assert "injection" in output


def test_live_default():
    with patch("trustbench.run") as mock_run:
        mock_run.return_value.returncode = 0

        result = main(["live"])

    assert result == 0
    mock_run.assert_called_once_with(
        [
            executable,
            str(PROJECT_ROOT / "eval_live.py"),
        ],
        check=False,
    )


def test_live_custom_dataset_and_model(tmp_path):
    dataset = tmp_path / "custom.json"
    dataset.write_text("[]", encoding="utf-8")

    with patch("trustbench.run") as mock_run:
        mock_run.return_value.returncode = 0

        result = main(
            [
                "live",
                "--dataset",
                str(dataset),
                "--model",
                "gemma3:1b",
            ]
        )

    assert result == 0
    mock_run.assert_called_once_with(
        [
            executable,
            str(PROJECT_ROOT / "eval_live.py"),
            "--dataset",
            str(dataset),
            "--model",
            "gemma3:1b",
        ],
        check=False,
    )


def test_live_custom_model_only():
    with patch("trustbench.run") as mock_run:
        mock_run.return_value.returncode = 0

        result = main(["live", "--model", "gemma3:1b"])

    assert result == 0
    mock_run.assert_called_once_with(
        [
            executable,
            str(PROJECT_ROOT / "eval_live.py"),
            "--model",
            "gemma3:1b",
        ],
        check=False,
    )


def test_consistency_default():
    with patch("trustbench.run") as mock_run:
        mock_run.return_value.returncode = 0

        result = main(["consistency"])

    assert result == 0
    mock_run.assert_called_once_with(
        [
            executable,
            str(PROJECT_ROOT / "run_consistency.py"),
        ],
        check=False,
    )


def test_injection_default():
    with patch("trustbench.run") as mock_run:
        mock_run.return_value.returncode = 0

        result = main(["injection"])

    assert result == 0
    mock_run.assert_called_once_with(
        [
            executable,
            str(PROJECT_ROOT / "run_prompt_injection.py"),
        ],
        check=False,
    )


@mark.parametrize(
    "command",
    ["consistency", "injection"],
)
def test_experiment_commands_reject_unsupported_dataset_argument(command):
    with raises(SystemExit) as error:
        main([command, "--dataset", "custom.json"])

    assert error.value.code == 2


@mark.parametrize("model", ["", "   "])
def test_live_rejects_empty_model(model):
    with patch("trustbench.run") as mock_run:
        with raises(SystemExit) as error:
            main(["live", "--model", model])

    assert error.value.code == 2
    mock_run.assert_not_called()


def test_scorers_missing_dataset_exits_before_subprocess(tmp_path):
    dataset = tmp_path / "missing-scoring-examples.json"

    with patch("trustbench.run") as mock_run:
        with raises(SystemExit) as error:
            main(["scorers", "--dataset", str(dataset)])

    assert error.value.code == 2
    mock_run.assert_not_called()


@mark.parametrize("command", ["offline", "scorers", "live"])
def test_missing_dataset_rejected_before_subprocess(command, tmp_path):
    missing = tmp_path / "missing.json"

    with patch("trustbench.run") as mock_run:
        with raises(SystemExit) as error:
            main([command, "--dataset", str(missing)])

    assert error.value.code == 2
    mock_run.assert_not_called()


def test_existing_dataset_accepted(tmp_path):
    dataset = tmp_path / "custom.json"
    dataset.write_text("[]", encoding="utf-8")

    with patch("trustbench.run") as mock_run:
        mock_run.return_value.returncode = 0
        result = main(["offline", "--dataset", str(dataset)])

    assert result == 0
    mock_run.assert_called_once()
