"""Discover saved TrustBench evaluation reports."""

from pathlib import Path


def list_saved_reports(directory: str = "reports") -> list[str]:
    """Return saved evaluation report paths, newest first."""

    folder = Path(directory)

    if not folder.exists():
        return []

    if not folder.is_dir():
        raise ValueError(f"Report location is not a directory: {directory}")

    reports = [path for path in folder.glob("evaluation-*.json") if path.is_file()]

    reports.sort(
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    return [str(path) for path in reports]
