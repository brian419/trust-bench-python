"""Build commands for TrustBench desktop evaluations."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def build_live_command(dataset: str, model: str) -> list[str]:
    """Build a command to run a local Ollama evaluation."""

    if not isinstance(dataset, str) or not dataset.strip():
        raise ValueError("Choose an evaluation dataset.")

    if not isinstance(model, str) or not model.strip():
        raise ValueError("Enter an Ollama model name.")

    dataset_path = Path(dataset).expanduser()

    if not dataset_path.is_absolute():
        dataset_path = PROJECT_ROOT / dataset_path

    dataset_path = dataset_path.resolve()

    if not dataset_path.is_file():
        raise ValueError(f"Dataset file does not exist: {dataset_path}")

    return [
        sys.executable,
        str(PROJECT_ROOT / "trustbench.py"),
        "live",
        "--dataset",
        str(dataset_path),
        "--model",
        model.strip(),
    ]


def run_live_command(command: list[str]) -> subprocess.Popen:
    """Start a live evaluation without blocking the caller."""

    return subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        bufsize=1,
        start_new_session=True,
    )


def request_evaluation_stop(process: subprocess.Popen) -> bool:
    """Request termination of a running evaluation process group.

    Only use with a process created by run_live_command().
    This requests shutdown without waiting for it to finish.
    """

    if process.poll() is not None:
        return False

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return False

    return True


def evaluation_group_exists(group_id: int) -> bool:
    """Check whether an evaluation process group still exists."""

    try:
        os.killpg(group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Cannot verify that the group disappeared.
        return True

    return True


def stop_evaluation_group(
    process: subprocess.Popen,
    grace_seconds: float = 3.0,
    force_wait_seconds: float = 1.0,
) -> bool:
    """Stop an evaluation group and verify that it disappears.

    Return True if the group no longer exists.
    Return False if its termination remains unverified.

    Call only from a background thread.
    """

    if grace_seconds < 0 or force_wait_seconds < 0:
        raise ValueError("Shutdown timeouts cannot be negative.")

    group_id = process.pid

    try:
        os.killpg(group_id, signal.SIGTERM)
    except ProcessLookupError:
        return True

    deadline = time.monotonic() + grace_seconds

    while time.monotonic() < deadline:
        process.poll()

        if not evaluation_group_exists(group_id):
            return True

        time.sleep(0.1)

    if not evaluation_group_exists(group_id):
        return True

    try:
        os.killpg(group_id, signal.SIGKILL)
    except ProcessLookupError:
        return True

    deadline = time.monotonic() + force_wait_seconds

    while time.monotonic() < deadline:
        process.poll()

        if not evaluation_group_exists(group_id):
            return True

        time.sleep(0.1)

    process.poll()

    return not evaluation_group_exists(group_id)
