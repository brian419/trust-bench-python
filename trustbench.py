"""Unified command-line entry point for TrustBench."""

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def nonempty_model(value: str) -> str:
    """Require a nonempty Ollama model name."""
    if not value.strip():
        raise argparse.ArgumentTypeError("Model name cannot be empty.")

    return value


def readable_dataset(value: str) -> Path:
    """Require an existing, readable dataset file."""
    path = Path(value)

    if not path.is_file():
        raise argparse.ArgumentTypeError(f"Dataset file does not exist: {value}")

    try:
        with path.open("r", encoding="utf-8"):
            pass
    except OSError as error:
        raise argparse.ArgumentTypeError(
            f"Cannot read dataset file: {error}"
        ) from error

    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trustbench",
        description="Run local AI response evaluations with TrustBench.",
    )

    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )

    offline = commands.add_parser(
        "offline",
        help="Evaluate prerecorded JSON responses.",
    )
    offline.add_argument(
        "--dataset",
        type=readable_dataset,
        help="Path to an offline evaluation dataset.",
    )

    scorers = commands.add_parser(
        "scorers",
        help="Compare exact matching with accepted-answer scoring.",
    )
    scorers.add_argument(
        "--dataset",
        type=readable_dataset,
        help="Path to a scoring-examples JSON dataset.",
    )

    live = commands.add_parser(
        "live",
        help="Evaluate questions using the local Ollama model.",
    )
    live.add_argument("--dataset", type=readable_dataset)
    live.add_argument("--model", type=nonempty_model)

    commands.add_parser(
        "consistency",
        help="Run repeated-response consistency experiments.",
    )

    commands.add_parser(
        "injection",
        help="Run controlled prompt-injection experiments.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "offline":
        command = [
            sys.executable,
            str(PROJECT_ROOT / "eval.py"),
        ]

    elif args.command == "scorers":
        command = [
            sys.executable,
            str(PROJECT_ROOT / "compare_scorers.py"),
        ]

    elif args.command == "live":
        command = [
            sys.executable,
            str(PROJECT_ROOT / "eval_live.py"),
        ]

    elif args.command == "consistency":
        command = [
            sys.executable,
            str(PROJECT_ROOT / "run_consistency.py"),
        ]

    elif args.command == "injection":
        command = [
            sys.executable,
            str(PROJECT_ROOT / "run_prompt_injection.py"),
        ]

    else:
        parser.error("Unsupported command.")

    if args.command == "live":
        if args.dataset is not None:
            command.extend(["--dataset", str(args.dataset)])
        if args.model is not None:
            command.extend(["--model", args.model])
    elif args.command in ("offline", "scorers"):
        if args.dataset is not None:
            command.append(str(args.dataset))

    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
