"""Separate read-only application resources from writable user reports."""

from pathlib import Path
from sys import platform


def is_packaged() -> bool:
    """Read the frozen marker without requiring it in source installations."""
    try:
        from sys import frozen
    except ImportError:
        return False

    return bool(frozen)


def resource_directory() -> Path:
    """Return the source or bundled module directory, independent of cwd."""
    return Path(__file__).resolve().parent


def user_data_directory() -> Path:
    """Return the macOS application's persistent writable data directory."""
    if platform != "darwin":
        raise ValueError("Packaged application data paths currently require macOS.")

    return Path.home() / "Library" / "Application Support" / "TrustBench"


def reports_directory(source_root: Path | None = None) -> Path:
    """Keep source GUI reports in place; put packaged reports outside the app."""
    if is_packaged():
        return user_data_directory() / "reports"

    root = source_root if source_root is not None else resource_directory()
    return root / "reports"
