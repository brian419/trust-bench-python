import sys
import signal
import os
import time
from unittest.mock import MagicMock
import pytest
import subprocess
from unittest.mock import patch
from evaluation_launcher import (
    PROJECT_ROOT,
    build_live_command,
    run_live_command,
    request_evaluation_stop,
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
        sys.executable,
        str(PROJECT_ROOT / "trustbench.py"),
        "live",
        "--dataset",
        str(dataset),
        "--model",
        "gemma3:1b",
    ]


def test_build_live_command_rejects_missing_dataset():
    with pytest.raises(
        ValueError,
        match="Choose an evaluation dataset",
    ):
        build_live_command("", "gemma3:1b")


def test_build_live_command_rejects_missing_model(tmp_path):
    dataset = tmp_path / "questions.json"
    dataset.write_text("[]", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Enter an Ollama model name",
    ):
        build_live_command(str(dataset), "   ")


def test_build_live_command_rejects_missing_file(tmp_path):
    missing = tmp_path / "missing.json"

    with pytest.raises(
        ValueError,
        match="Dataset file does not exist",
    ):
        build_live_command(str(missing), "gemma3:1b")


def test_run_live_command_starts_subprocess():
    command = ["python3", "trustbench.py", "live"]

    with patch("evaluation_launcher.subprocess.Popen") as popen:
        process = run_live_command(command)

    assert process is popen.return_value

    popen.assert_called_once_with(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        bufsize=1,
        start_new_session=True,
    )


def test_run_live_command_propagates_startup_error():
    command = ["nonexistent-python", "trustbench.py", "live"]

    with patch(
        "evaluation_launcher.subprocess.Popen",
        side_effect=OSError("Executable not found"),
    ):
        with pytest.raises(OSError, match="Executable not found"):
            run_live_command(command)


def test_request_evaluation_stop_running_process():
    process = MagicMock()
    process.pid = 12345
    process.poll.return_value = None

    with patch("evaluation_launcher.os.killpg") as killpg:
        result = request_evaluation_stop(process)

    assert result is True
    killpg.assert_called_once_with(
        12345,
        signal.SIGTERM,
    )


def test_request_evaluation_stop_completed_process():
    process = MagicMock()
    process.poll.return_value = 0

    with patch("evaluation_launcher.os.killpg") as killpg:
        result = request_evaluation_stop(process)

    assert result is False
    killpg.assert_not_called()


def test_request_evaluation_stop_missing_process():
    process = MagicMock()
    process.pid = 12345
    process.poll.return_value = None

    with patch(
        "evaluation_launcher.os.killpg",
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
        "evaluation_launcher.os.killpg",
        side_effect=fake_killpg,
    ):
        result = stop_evaluation_group(process)

    assert result is True
    assert calls == [
        (12345, signal.SIGTERM),
        (12345, 0),
    ]


def test_stop_group_escalates_after_timeout():
    process = MagicMock()
    process.pid = 12345

    with (
        patch("evaluation_launcher.os.killpg") as killpg,
        patch(
            "evaluation_launcher.time.monotonic",
            side_effect=[0.0, 0.0, 0.2, 1.0, 1.0, 2.1],
        ),
        patch("evaluation_launcher.time.sleep"),
    ):
        result = stop_evaluation_group(
            process,
            grace_seconds=0.1,
            force_wait_seconds=1.0,
        )

    assert result is False

    signals_sent = [call.args[1] for call in killpg.call_args_list]

    assert signal.SIGTERM in signals_sent
    assert signal.SIGKILL in signals_sent
    assert signals_sent[-1] == 0


def test_stop_group_rejects_negative_grace_period():
    process = MagicMock()

    with pytest.raises(
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

        if sig == signal.SIGKILL:
            force_requested = True

        elif sig == 0 and force_requested:
            raise ProcessLookupError

    with (
        patch(
            "evaluation_launcher.os.killpg",
            side_effect=fake_killpg,
        ),
        patch(
            "evaluation_launcher.time.monotonic",
            side_effect=[0.0, 0.0, 0.2, 1.0, 1.0],
        ),
        patch("evaluation_launcher.time.sleep"),
    ):
        result = stop_evaluation_group(
            process,
            grace_seconds=0.1,
            force_wait_seconds=1.0,
        )

    assert result is True
    assert signal.SIGKILL in signals_sent


def test_stop_group_rejects_negative_force_wait():
    process = MagicMock()

    with pytest.raises(
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
            sys.executable,
            "-u",
            "-c",
            "import time; time.sleep(30)",
        ]
    )

    try:
        assert os.getpgid(process.pid) == process.pid

        time.sleep(0.1)

        verified = stop_evaluation_group(process)

        assert verified is True
        process.wait(timeout=3.0)
        assert process.returncode is not None

    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)

        try:
            process.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3.0)


def test_group_permission_error_is_not_treated_as_missing():
    from evaluation_launcher import evaluation_group_exists

    with patch(
        "evaluation_launcher.os.killpg",
        side_effect=PermissionError("Operation not permitted"),
    ):
        assert evaluation_group_exists(12345) is True


def test_real_process_group_stops_parent_and_child():
    """Verify shutdown of a parent and its child process."""

    parent_code = (
        "import subprocess, sys, time\n"
        "child = subprocess.Popen(["
        "sys.executable, '-c', 'import time; time.sleep(30)'])\n"
        "print(child.pid, flush=True)\n"
        "time.sleep(30)\n"
    )

    process = run_live_command(
        [
            sys.executable,
            "-u",
            "-c",
            parent_code,
        ]
    )

    child_pid = None

    try:
        child_pid = int(process.stdout.readline().strip())

        assert os.getpgid(process.pid) == process.pid
        assert os.getpgid(child_pid) == process.pid

        verified = stop_evaluation_group(process)

        assert verified is True
        process.wait(timeout=3.0)

    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        process.wait(timeout=3.0)
