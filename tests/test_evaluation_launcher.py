from os import getpgid, killpg
from signal import SIGKILL, SIGTERM
from subprocess import PIPE, STDOUT, TimeoutExpired
from sys import executable
from time import sleep
from unittest.mock import MagicMock, patch

from pytest import raises

from evaluation_launcher import (
    build_live_command,
    evaluation_group_exists,
    PROJECT_ROOT,
    request_evaluation_stop,
    run_live_command,
    stop_evaluation_group,
)


def test_build_live_command(tmp_path):
    dataset = tmp_path / "questions.json"
    dataset.write_text("[]", encoding="utf-8")

    command = build_live_command(
        str(dataset),
        "gemma3:1b",
    )

    assert command == [
        executable,
        str(PROJECT_ROOT / "trustbench.py"),
        "live",
        "--dataset",
        str(dataset),
        "--model",
        "gemma3:1b",
    ]


def test_build_live_command_rejects_missing_dataset():
    with raises(
        ValueError,
        match="Choose an evaluation dataset",
    ):
        build_live_command("", "gemma3:1b")


def test_build_live_command_rejects_missing_model(tmp_path):
    dataset = tmp_path / "questions.json"
    dataset.write_text("[]", encoding="utf-8")

    with raises(
        ValueError,
        match="Enter an Ollama model name",
    ):
        build_live_command(str(dataset), "   ")


def test_build_live_command_rejects_missing_file(tmp_path):
    missing = tmp_path / "missing.json"

    with raises(
        ValueError,
        match="Dataset file does not exist",
    ):
        build_live_command(str(missing), "gemma3:1b")


def test_run_live_command_starts_subprocess(monkeypatch):
    command = ["python3", "trustbench.py", "live"]
    environment = {"EXISTING_SETTING": "preserved", "PYTHONUNBUFFERED": "0"}
    monkeypatch.setattr("evaluation_launcher.environ", environment)

    with patch("evaluation_launcher.Popen") as popen:
        process = run_live_command(command)

    assert process is popen.return_value

    popen.assert_called_once_with(
        command,
        cwd=PROJECT_ROOT,
        env={"EXISTING_SETTING": "preserved", "PYTHONUNBUFFERED": "1"},
        stdout=PIPE,
        stderr=STDOUT,
        text=True,
        encoding="utf-8",
        bufsize=1,
        start_new_session=True,
    )
    assert environment["PYTHONUNBUFFERED"] == "0"


def test_run_live_command_propagates_startup_error():
    command = ["nonexistent-python", "trustbench.py", "live"]

    with patch(
        "evaluation_launcher.Popen",
        side_effect=OSError("Executable not found"),
    ):
        with raises(OSError, match="Executable not found"):
            run_live_command(command)


def test_request_evaluation_stop_running_process():
    process = MagicMock()
    process.pid = 12345
    process.poll.return_value = None

    with patch("evaluation_launcher.killpg") as killpg:
        result = request_evaluation_stop(process)

    assert result is True
    killpg.assert_called_once_with(
        12345,
        SIGTERM,
    )


def test_request_evaluation_stop_completed_process():
    process = MagicMock()
    process.poll.return_value = 0

    with patch("evaluation_launcher.killpg") as killpg:
        result = request_evaluation_stop(process)

    assert result is False
    killpg.assert_not_called()


def test_request_evaluation_stop_missing_process():
    process = MagicMock()
    process.pid = 12345
    process.poll.return_value = None

    with patch(
        "evaluation_launcher.killpg",
        side_effect=ProcessLookupError,
    ):
        result = request_evaluation_stop(process)

    assert result is False


def test_stop_group_exits_during_grace_period():
    process = MagicMock()
    process.pid = 12345

    calls = []

    def fake_killpg(group_id, sig):
        calls.append((group_id, sig))

        if sig == 0:
            raise ProcessLookupError

    with patch(
        "evaluation_launcher.killpg",
        side_effect=fake_killpg,
    ):
        result = stop_evaluation_group(process)

    assert result is True
    assert calls == [
        (12345, SIGTERM),
        (12345, 0),
    ]


def test_stop_group_escalates_after_timeout():
    process = MagicMock()
    process.pid = 12345

    with (
        patch("evaluation_launcher.killpg") as killpg,
        patch(
            "evaluation_launcher.monotonic",
            side_effect=[0.0, 0.0, 0.2, 1.0, 1.0, 2.1],
        ),
        patch("evaluation_launcher.sleep"),
    ):
        result = stop_evaluation_group(
            process,
            grace_seconds=0.1,
            force_wait_seconds=1.0,
        )

    assert result is False

    signals_sent = [call.args[1] for call in killpg.call_args_list]

    assert SIGTERM in signals_sent
    assert SIGKILL in signals_sent
    assert signals_sent[-1] == 0


def test_stop_group_rejects_negative_grace_period():
    process = MagicMock()

    with raises(
        ValueError,
        match="Shutdown timeouts cannot be negative",
    ):
        stop_evaluation_group(
            process,
            grace_seconds=-1,
        )


def test_stop_group_verifies_forced_termination():
    process = MagicMock()
    process.pid = 12345

    signals_sent = []
    force_requested = False

    def fake_killpg(group_id, sig):
        nonlocal force_requested

        signals_sent.append(sig)

        if sig == SIGKILL:
            force_requested = True

        elif sig == 0 and force_requested:
            raise ProcessLookupError

    with (
        patch(
            "evaluation_launcher.killpg",
            side_effect=fake_killpg,
        ),
        patch(
            "evaluation_launcher.monotonic",
            side_effect=[0.0, 0.0, 0.2, 1.0, 1.0],
        ),
        patch("evaluation_launcher.sleep"),
    ):
        result = stop_evaluation_group(
            process,
            grace_seconds=0.1,
            force_wait_seconds=1.0,
        )

    assert result is True
    assert SIGKILL in signals_sent


def test_stop_group_rejects_negative_force_wait():
    process = MagicMock()

    with raises(
        ValueError,
        match="Shutdown timeouts cannot be negative",
    ):
        stop_evaluation_group(
            process,
            force_wait_seconds=-1,
        )


def test_real_subprocess_group_can_be_stopped():
    """Verify shutdown against a disposable real subprocess."""

    process = run_live_command(
        [
            executable,
            "-u",
            "-c",
            "from time import sleep; sleep(30)",
        ]
    )

    try:
        assert getpgid(process.pid) == process.pid

        sleep(0.1)

        verified = stop_evaluation_group(process)

        assert verified is True
        process.wait(timeout=3.0)
        assert process.returncode is not None

    finally:
        if process.poll() is None:
            killpg(process.pid, SIGKILL)

        try:
            process.wait(timeout=3.0)
        except TimeoutExpired:
            process.kill()
            process.wait(timeout=3.0)


def test_group_permission_error_is_not_treated_as_missing():
    with patch(
        "evaluation_launcher.killpg",
        side_effect=PermissionError("Operation not permitted"),
    ):
        assert evaluation_group_exists(12345) is True


def test_real_process_group_stops_parent_and_child():
    """Verify shutdown of a parent and its child process."""

    parent_code = (
        "from subprocess import Popen\n"
        "from sys import executable\n"
        "from time import sleep\n"
        "child = Popen(["
        "executable, '-c', 'from time import sleep; sleep(30)'])\n"
        "print(child.pid, flush=True)\n"
        "sleep(30)\n"
    )

    process = run_live_command(
        [
            executable,
            "-u",
            "-c",
            parent_code,
        ]
    )

    child_pid = None

    try:
        child_pid = int(process.stdout.readline().strip())

        assert getpgid(process.pid) == process.pid
        assert getpgid(child_pid) == process.pid

        verified = stop_evaluation_group(process)

        assert verified is True
        process.wait(timeout=3.0)

    finally:
        if process.poll() is None:
            try:
                killpg(process.pid, SIGKILL)
            except ProcessLookupError:
                pass

        process.wait(timeout=3.0)
