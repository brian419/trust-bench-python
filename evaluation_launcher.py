"""Build commands for TrustBench desktop evaluations."""

from os import environ, killpg
from pathlib import Path
from signal import SIGKILL, SIGTERM
from subprocess import PIPE, Popen, STDOUT
from sys import executable
from time import monotonic, sleep

from app_entry import WORKER_FLAG
from evaluation_progress import PROGRESS_FILE_ENV
from runtime_paths import is_packaged, reports_directory, resource_directory


PROJECT_ROOT = resource_directory()


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

    if is_packaged():
        return [
            executable,
            WORKER_FLAG,
            "--dataset",
            str(dataset_path),
            "--model",
            model.strip(),
            "--reports-dir",
            str(reports_directory()),
        ]

    return [
        executable,
        str(PROJECT_ROOT / "trustbench.py"),
        "live",
        "--dataset",
        str(dataset_path),
        "--model",
        model.strip(),
    ]


def run_live_command(command: list[str], *, progress_file: Path | None = None) -> Popen:
    """Start a live evaluation without blocking the caller."""

    # The CLI wrapper launches another interpreter. Inheriting this setting
    # makes the evaluator flush too, without changing the caller's environment.
    environment = environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    if progress_file is not None:
        environment[PROGRESS_FILE_ENV] = str(progress_file)

    working_directory = PROJECT_ROOT

    if is_packaged():
        working_directory = reports_directory().parent
        working_directory.mkdir(parents=True, exist_ok=True)

    return Popen(
        command,
        cwd=working_directory,
        env=environment,
        stdout=PIPE,
        stderr=STDOUT,
        text=True,
        encoding="utf-8",
        bufsize=1,
        start_new_session=True,
    )


def request_evaluation_stop(process: Popen) -> bool:
    """Request termination of a running evaluation process group.

    Only use with a process created by run_live_command().
    This requests shutdown without waiting for it to finish.
    """

    if process.poll() is not None:
        return False

    try:
        killpg(process.pid, SIGTERM)
    except ProcessLookupError:
        return False

    return True


def evaluation_group_exists(group_id: int) -> bool:
    """Check whether an evaluation process group still exists."""

    try:
        killpg(group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Cannot verify that the group disappeared.
        return True

    return True


def stop_evaluation_group(
    process: Popen,
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
        killpg(group_id, SIGTERM)
    except ProcessLookupError:
        return True

    deadline = monotonic() + grace_seconds

    while monotonic() < deadline:
        process.poll()

        if not evaluation_group_exists(group_id):
            return True

        sleep(0.1)

    if not evaluation_group_exists(group_id):
        return True

    try:
        killpg(group_id, SIGKILL)
    except ProcessLookupError:
        return True

    deadline = monotonic() + force_wait_seconds

    while monotonic() < deadline:
        process.poll()

        if not evaluation_group_exists(group_id):
            return True

        sleep(0.1)

    process.poll()

    return not evaluation_group_exists(group_id)
