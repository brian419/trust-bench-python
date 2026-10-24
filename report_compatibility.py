"""Compatibility checks for TrustBench reports."""

import re


def compare_input_fingerprints(first: dict, second: dict) -> dict:
    """Compare available report input fingerprints."""

    first_metadata = first.get("metadata", {})
    second_metadata = second.get("metadata", {})

    first_provenance = first_metadata.get("provenance") or {}
    second_provenance = second_metadata.get("provenance") or {}

    fingerprint_keys = ("dataset_sha256", "inputs_sha256")

    first_key = next(
        (key for key in fingerprint_keys if key in first_provenance),
        None,
    )
    second_key = next(
        (key for key in fingerprint_keys if key in second_provenance),
        None,
    )

    if first_key is None or second_key is None:
        return {
            "status": "UNVERIFIED",
            "reason": "One or both reports lack input fingerprints.",
        }

    if first_key != second_key:
        return {
            "status": "INCOMPATIBLE",
            "reason": "Reports use different fingerprint types.",
        }

    first_hash = first_provenance[first_key]
    second_hash = second_provenance[second_key]

    sha256_pattern = r"[0-9a-f]{64}"

    if not (
        isinstance(first_hash, str)
        and isinstance(second_hash, str)
        and re.fullmatch(sha256_pattern, first_hash)
        and re.fullmatch(sha256_pattern, second_hash)
    ):
        return {
            "status": "UNVERIFIED",
            "reason": "One or both input fingerprints are invalid.",
        }

    if first_hash != second_hash:
        return {
            "status": "INCOMPATIBLE",
            "reason": "Reports use different evaluation inputs.",
        }

    return {
        "status": "MATCH",
        "reason": "Input fingerprints match.",
    }


def detect_report_type(report: dict) -> str | None:
    """Identify a TrustBench report from its metadata."""

    metadata = report.get("metadata")

    if not isinstance(metadata, dict):
        return None

    provenance = metadata.get("provenance")

    if not isinstance(provenance, dict):
        return None

    if "dataset_sha256" in provenance and "primary_scoring" in provenance:
        return "live"

    if "inputs_sha256" in provenance and "repetitions" in metadata:
        return "consistency"

    if (
        "dataset_sha256" in provenance
        and "scoring_method" in provenance
        and "prompt_format" in provenance
    ):
        return "injection"

    return None


def compare_report_compatibility(first: dict, second: dict) -> dict:
    """Check report type, inputs, scoring, and model configuration."""

    first_type = detect_report_type(first)
    second_type = detect_report_type(second)

    if first_type is None or second_type is None:
        return {
            "status": "UNVERIFIED",
            "reason": "One or both report types could not be identified.",
        }

    if first_type != second_type:
        return {
            "status": "INCOMPATIBLE",
            "reason": "Reports use different experiment types.",
        }

    fingerprint_result = compare_input_fingerprints(first, second)

    if fingerprint_result["status"] != "MATCH":
        return fingerprint_result

    scoring_result = compare_scoring_rules(first, second)

    if scoring_result["status"] != "MATCH":
        return scoring_result

    model_result = compare_model_configuration(first, second)

    if model_result["status"] == "UNVERIFIED":
        return model_result

    warnings = model_result["warnings"]

    return {
        "status": "PARTIAL_MATCH",
        "reason": (
            "Experiment types, inputs, and scoring rules match. "
            "Model configuration was inspected, but full "
            "reproducibility is not guaranteed."
        ),
        "warnings": warnings,
    }


def compare_scoring_rules(first: dict, second: dict) -> dict:
    """Compare scoring definitions for two reports."""

    first_type = detect_report_type(first)
    second_type = detect_report_type(second)

    if first_type is None or second_type is None:
        return {
            "status": "UNVERIFIED",
            "reason": "One or both report types are unknown.",
        }

    if first_type != second_type:
        return {
            "status": "INCOMPATIBLE",
            "reason": "Reports use different experiment types.",
        }

    first_provenance = first["metadata"]["provenance"]
    second_provenance = second["metadata"]["provenance"]

    if first_type == "live":
        scoring_keys = ("primary_scoring", "alternative_scoring")
    elif first_type == "injection":
        scoring_keys = ("scoring_method", "prompt_format")
    else:
        scoring_keys = ("scoring_method", "prompt_format")

    for key in scoring_keys:
        if key not in first_provenance or key not in second_provenance:
            return {
                "status": "UNVERIFIED",
                "reason": f"Missing scoring metadata: {key}.",
            }

        if first_provenance[key] != second_provenance[key]:
            return {
                "status": "INCOMPATIBLE",
                "reason": f"Different scoring metadata: {key}.",
            }

    return {
        "status": "MATCH",
        "reason": "Scoring definitions match.",
    }


def compare_model_configuration(first: dict, second: dict) -> dict:
    """Inspect model identity and recorded generation settings."""

    first_metadata = first.get("metadata", {})
    second_metadata = second.get("metadata", {})

    first_model = first_metadata.get("model")
    second_model = second_metadata.get("model")

    if not (
        isinstance(first_model, str)
        and first_model.strip()
        and isinstance(second_model, str)
        and second_model.strip()
    ):
        return {
            "status": "UNVERIFIED",
            "reason": "One or both model names are missing or invalid.",
        }

    first_provenance = first_metadata.get("provenance") or {}
    second_provenance = second_metadata.get("provenance") or {}

    first_options = first_provenance.get("model_options")
    second_options = second_provenance.get("model_options")

    warnings = []

    if first_model != second_model:
        warnings.append("Reports use different models.")

    if first_options is None or second_options is None:
        warnings.append("Generation options are not fully recorded.")
    elif first_options != second_options:
        warnings.append("Reports use different generation options.")

    first_version = first_provenance.get("model_version")
    second_version = second_provenance.get("model_version")

    if first_version is None or second_version is None:
        warnings.append("One or both model versions are unknown.")
    elif first_version != second_version:
        warnings.append("Reports use different model versions.")

    return {
        "status": "MATCH" if not warnings else "PARTIAL_MATCH",
        "reason": (
            "Recorded model configuration matches."
            if not warnings
            else "Model configuration differences or limitations detected."
        ),
        "warnings": warnings,
    }
