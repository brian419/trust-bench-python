import hashlib
import json
from pathlib import Path


def load_verified_report(
    report_path: Path,
    expected_sha256: str,
) -> dict:
    raw_data = report_path.read_bytes()

    actual_sha256 = hashlib.sha256(raw_data).hexdigest()

    if actual_sha256 != expected_sha256:
        raise ValueError("Report SHA-256 mismatch.")

    report = json.loads(raw_data)

    if not isinstance(report, dict):
        raise ValueError("Report must be a JSON object.")

    metadata = report.get("metadata")
    results = report.get("results")

    if not isinstance(metadata, dict):
        raise ValueError("Report metadata must be an object.")

    if not isinstance(results, list):
        raise ValueError("Report results must be a list.")

    return report
