"""Entry point for the future macOS app and its live-evaluation worker."""

from argparse import ArgumentParser
from contextlib import redirect_stderr, redirect_stdout
from os import dup, fdopen
from pathlib import Path
from sys import argv, exit
from traceback import print_exc

from trustbench import nonempty_model, readable_dataset

WORKER_FLAG = "--trustbench-evaluate"


def run_evaluation_worker(arguments: list[str]) -> int:
    """Run live inference in this process without importing the GUI."""
    from eval_live import main as evaluate

    parser = ArgumentParser(description="TrustBench live-evaluation worker.")
    parser.add_argument("--dataset", required=True, type=readable_dataset)
    parser.add_argument("--model", required=True, type=nonempty_model)
    parser.add_argument("--reports-dir", required=True, type=Path)
    args = parser.parse_args(arguments)

    try:
        evaluate(
            filename=str(args.dataset.expanduser().resolve()),
            model=args.model,
            report_dir=args.reports_dir.expanduser().resolve(),
        )
    except (OSError, ValueError) as error:
        print("Error:", error)
        return 1

    return 0


def main(arguments: list[str] | None = None) -> int:
    """Select worker mode before any Tkinter import or window creation."""
    arguments = list(argv[1:] if arguments is None else arguments)

    if arguments and arguments[0] == WORKER_FLAG:
        # Windowed builds can lack Python stdout/stderr objects. The launcher
        # supplies pipe file descriptors; duplicate them and flush each line.
        with (
            fdopen(dup(1), "w", encoding="utf-8", buffering=1) as output,
            fdopen(dup(2), "w", encoding="utf-8", buffering=1) as errors,
            redirect_stdout(output),
            redirect_stderr(errors),
        ):
            try:
                return run_evaluation_worker(arguments[1:])
            except Exception:
                # Keep unexpected diagnostics in the pipe even if the windowed
                # runtime restores sys.stderr to None after this context ends.
                print_exc(file=errors)
                return 1

    parser = ArgumentParser(description="Launch the TrustBench desktop app.")
    parser.parse_args(arguments)

    from desktop_gui import main as run_desktop

    run_desktop()
    return 0


if __name__ == "__main__":
    exit(main())
