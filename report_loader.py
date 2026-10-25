"""Utilities for reading existing TrustBench reports."""

from json import load
from pathlib import Path


def load_report(filename: str | Path) -> dict:
    """Load a JSON report and validate its basic structure."""
    path = Path(filename)

    with path.open("r", encoding="utf-8") as file:
        report = load(file)

    if not isinstance(report, dict):
        raise ValueError("Report must be a JSON object.")

    if not isinstance(report.get("metadata"), dict):
        raise ValueError("Report must contain a metadata object.")

    if not isinstance(report.get("results"), list):
        raise ValueError("Report must contain a results list.")

    return report
