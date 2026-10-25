from hashlib import sha256

from report_compatibility import (
    compare_input_fingerprints,
    compare_model_configuration,
    compare_report_compatibility,
    compare_scoring_rules,
    detect_report_type,
)


def fingerprint(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def make_report(fingerprint_key=None, fingerprint=None):
    provenance = {}

    if fingerprint_key is not None:
        provenance[fingerprint_key] = fingerprint

    return {
        "metadata": {
            "model": "gemma3:1b",
            "provenance": provenance,
        },
        "results": [],
    }


def test_matching_dataset_fingerprints():
    first = make_report(
        "dataset_sha256",
        fingerprint("dataset-a"),
    )
    second = make_report(
        "dataset_sha256",
        fingerprint("dataset-a"),
    )

    result = compare_input_fingerprints(first, second)

    assert result["status"] == "MATCH"


def test_different_dataset_fingerprints():
    first = make_report(
        "dataset_sha256",
        fingerprint("dataset-a"),
    )
    second = make_report(
        "dataset_sha256",
        fingerprint("dataset-b"),
    )

    result = compare_input_fingerprints(first, second)

    assert result["status"] == "INCOMPATIBLE"


def test_matching_consistency_input_fingerprints():
    first = make_report(
        "inputs_sha256",
        fingerprint("dataset-a"),
    )
    second = make_report(
        "inputs_sha256",
        fingerprint("dataset-a"),
    )

    result = compare_input_fingerprints(first, second)

    assert result["status"] == "MATCH"


def test_different_fingerprint_types():
    first = make_report("dataset_sha256", "abc123")
    second = make_report("inputs_sha256", "abc123")

    result = compare_input_fingerprints(first, second)

    assert result["status"] == "INCOMPATIBLE"


def test_missing_fingerprints_are_unverified():
    first = make_report("dataset_sha256", "abc123")
    second = make_report()

    result = compare_input_fingerprints(first, second)

    assert result["status"] == "UNVERIFIED"


def test_legacy_reports_are_unverified():
    first = {
        "metadata": {"model": "gemma3:1b"},
        "results": [],
    }
    second = make_report("dataset_sha256", "abc123")

    result = compare_input_fingerprints(first, second)

    assert result["status"] == "UNVERIFIED"


def test_invalid_short_fingerprint_is_unverified():
    first = make_report("dataset_sha256", "abc123")
    second = make_report("dataset_sha256", "abc123")

    result = compare_input_fingerprints(first, second)

    assert result["status"] == "UNVERIFIED"


def test_null_fingerprint_is_unverified():
    first = make_report("dataset_sha256", None)
    second = make_report(
        "dataset_sha256",
        fingerprint("dataset-a"),
    )

    result = compare_input_fingerprints(first, second)

    assert result["status"] == "UNVERIFIED"


def test_uppercase_fingerprint_is_unverified():
    valid_hash = fingerprint("dataset-a")

    first = make_report("dataset_sha256", valid_hash.upper())
    second = make_report("dataset_sha256", valid_hash)

    result = compare_input_fingerprints(first, second)

    assert result["status"] == "UNVERIFIED"


def test_detect_live_report_type():
    report = make_report(
        "dataset_sha256",
        fingerprint("dataset-a"),
    )
    report["metadata"]["provenance"]["primary_scoring"] = "normalized-exact-v1"

    assert detect_report_type(report) == "live"


def test_detect_consistency_report_type():
    report = make_report(
        "inputs_sha256",
        fingerprint("dataset-a"),
    )
    report["metadata"]["repetitions"] = 3

    assert detect_report_type(report) == "consistency"


def test_detect_injection_report_type():
    report = make_report(
        "dataset_sha256",
        fingerprint("dataset-a"),
    )

    provenance = report["metadata"]["provenance"]
    provenance["scoring_method"] = "prompt-injection-target-match-v1"
    provenance["prompt_format"] = "single_prompt_delimited_document_v1"

    assert detect_report_type(report) == "injection"


def test_unknown_report_type():
    report = {
        "metadata": {
            "model": "gemma3:1b",
        },
        "results": [],
    }

    assert detect_report_type(report) is None


def test_same_type_and_inputs_produce_partial_match():
    first = make_report("dataset_sha256", fingerprint("dataset-a"))
    second = make_report("dataset_sha256", fingerprint("dataset-a"))

    for report in (first, second):
        provenance = report["metadata"]["provenance"]
        provenance["primary_scoring"] = "normalized-exact-v1"
        provenance["alternative_scoring"] = None
        provenance["model_options"] = {"temperature": 0}
        provenance["model_version"] = "known-version"

    result = compare_report_compatibility(first, second)

    assert result["status"] == "PARTIAL_MATCH"
    assert result["warnings"] == []


def test_different_experiment_types_are_incompatible():
    first = make_report("dataset_sha256", fingerprint("dataset-a"))
    first["metadata"]["provenance"]["primary_scoring"] = "normalized-exact-v1"

    second = make_report("dataset_sha256", fingerprint("dataset-a"))
    second["metadata"]["provenance"]["scoring_method"] = (
        "prompt-injection-target-match-v1"
    )
    second["metadata"]["provenance"]["prompt_format"] = (
        "single_prompt_delimited_document_v1"
    )

    result = compare_report_compatibility(first, second)

    assert result["status"] == "INCOMPATIBLE"


def test_different_inputs_are_incompatible():
    first = make_report("inputs_sha256", fingerprint("prompts-a"))
    second = make_report("inputs_sha256", fingerprint("prompts-b"))

    for report in (first, second):
        report["metadata"]["repetitions"] = 3

    result = compare_report_compatibility(first, second)

    assert result["status"] == "INCOMPATIBLE"


def test_unknown_report_type_is_unverified():
    first = {
        "metadata": {"model": "gemma3:1b"},
        "results": [],
    }

    second = make_report("dataset_sha256", fingerprint("dataset-a"))
    second["metadata"]["provenance"]["primary_scoring"] = "normalized-exact-v1"

    result = compare_report_compatibility(first, second)

    assert result["status"] == "UNVERIFIED"


def test_matching_live_scoring_rules():
    first = make_report("dataset_sha256", fingerprint("dataset-a"))
    second = make_report("dataset_sha256", fingerprint("dataset-a"))

    for report in (first, second):
        provenance = report["metadata"]["provenance"]
        provenance["primary_scoring"] = "normalized-exact-v1"
        provenance["alternative_scoring"] = None

    result = compare_scoring_rules(first, second)

    assert result["status"] == "MATCH"


def test_different_live_scoring_rules():
    first = make_report("dataset_sha256", fingerprint("dataset-a"))
    second = make_report("dataset_sha256", fingerprint("dataset-a"))

    first_provenance = first["metadata"]["provenance"]
    second_provenance = second["metadata"]["provenance"]

    first_provenance["primary_scoring"] = "normalized-exact-v1"
    first_provenance["alternative_scoring"] = None

    second_provenance["primary_scoring"] = "different-scoring-v2"
    second_provenance["alternative_scoring"] = None

    result = compare_scoring_rules(first, second)

    assert result["status"] == "INCOMPATIBLE"


def test_matching_injection_scoring_rules():
    first = make_report("dataset_sha256", fingerprint("dataset-a"))
    second = make_report("dataset_sha256", fingerprint("dataset-a"))

    for report in (first, second):
        provenance = report["metadata"]["provenance"]
        provenance["scoring_method"] = "prompt-injection-target-match-v1"
        provenance["prompt_format"] = "single_prompt_delimited_document_v1"

    result = compare_scoring_rules(first, second)

    assert result["status"] == "MATCH"


def test_missing_scoring_metadata_is_unverified():
    first = make_report("dataset_sha256", fingerprint("dataset-a"))
    second = make_report("dataset_sha256", fingerprint("dataset-a"))

    first["metadata"]["provenance"]["primary_scoring"] = "normalized-exact-v1"

    second_provenance = second["metadata"]["provenance"]
    second_provenance["primary_scoring"] = "normalized-exact-v1"
    second_provenance["alternative_scoring"] = None

    result = compare_scoring_rules(first, second)

    assert result["status"] == "UNVERIFIED"


def test_matching_consistency_scoring_rules():
    first = make_report("inputs_sha256", fingerprint("prompts-a"))
    second = make_report("inputs_sha256", fingerprint("prompts-a"))

    for report in (first, second):
        report["metadata"]["repetitions"] = 3
        provenance = report["metadata"]["provenance"]
        provenance["scoring_method"] = None
        provenance["prompt_format"] = "plain-question-v1"

    result = compare_scoring_rules(first, second)

    assert result["status"] == "MATCH"


def test_different_injection_prompt_formats():
    first = make_report("dataset_sha256", fingerprint("dataset-a"))
    second = make_report("dataset_sha256", fingerprint("dataset-a"))

    for report in (first, second):
        provenance = report["metadata"]["provenance"]
        provenance["scoring_method"] = "prompt-injection-target-match-v1"
        provenance["prompt_format"] = "single_prompt_delimited_document_v1"

    second["metadata"]["provenance"]["prompt_format"] = "different-format-v2"

    result = compare_scoring_rules(first, second)

    assert result["status"] == "INCOMPATIBLE"


def test_missing_consistency_prompt_format_is_unverified():
    first = make_report("inputs_sha256", fingerprint("prompts-a"))
    second = make_report("inputs_sha256", fingerprint("prompts-a"))

    for report in (first, second):
        report["metadata"]["repetitions"] = 3
        report["metadata"]["provenance"]["scoring_method"] = None

    second["metadata"]["provenance"]["prompt_format"] = "plain-question-v1"

    result = compare_scoring_rules(first, second)

    assert result["status"] == "UNVERIFIED"


def test_combined_compatibility_rejects_different_scoring_rules():
    first = make_report("dataset_sha256", fingerprint("dataset-a"))
    second = make_report("dataset_sha256", fingerprint("dataset-a"))

    for report in (first, second):
        provenance = report["metadata"]["provenance"]
        provenance["primary_scoring"] = "normalized-exact-v1"
        provenance["alternative_scoring"] = None

    second["metadata"]["provenance"]["primary_scoring"] = "different-scoring-v2"

    result = compare_report_compatibility(first, second)

    assert result["status"] == "INCOMPATIBLE"
    assert "primary_scoring" in result["reason"]


def test_combined_compatibility_requires_complete_scoring_metadata():
    first = make_report("dataset_sha256", fingerprint("dataset-a"))
    second = make_report("dataset_sha256", fingerprint("dataset-a"))

    for report in (first, second):
        report["metadata"]["provenance"]["primary_scoring"] = "normalized-exact-v1"

    second["metadata"]["provenance"]["alternative_scoring"] = None

    result = compare_report_compatibility(first, second)

    assert result["status"] == "UNVERIFIED"
    assert "alternative_scoring" in result["reason"]


def test_matching_model_configuration():
    first = make_report()
    second = make_report()

    for report in (first, second):
        provenance = report["metadata"]["provenance"]
        provenance["model_options"] = {"temperature": 0, "seed": 42}
        provenance["model_version"] = "known-version"

    result = compare_model_configuration(first, second)

    assert result["status"] == "MATCH"
    assert result["warnings"] == []


def test_different_models_are_not_incompatible():
    first = make_report()
    second = make_report()

    second["metadata"]["model"] = "different-model"

    for report in (first, second):
        provenance = report["metadata"]["provenance"]
        provenance["model_options"] = {"temperature": 0}
        provenance["model_version"] = "known-version"

    result = compare_model_configuration(first, second)

    assert result["status"] == "PARTIAL_MATCH"
    assert "Reports use different models." in result["warnings"]


def test_missing_model_options_are_reported():
    first = make_report()
    second = make_report()

    result = compare_model_configuration(first, second)

    assert result["status"] == "PARTIAL_MATCH"
    assert "Generation options are not fully recorded." in result["warnings"]


def test_missing_model_name_is_unverified():
    first = make_report()
    second = make_report()

    del second["metadata"]["model"]

    result = compare_model_configuration(first, second)

    assert result["status"] == "UNVERIFIED"


def test_different_generation_options_are_reported():
    first = make_report()
    second = make_report()

    for report in (first, second):
        provenance = report["metadata"]["provenance"]
        provenance["model_options"] = {
            "temperature": 0,
            "seed": 42,
        }
        provenance["model_version"] = "known-version"

    second["metadata"]["provenance"]["model_options"]["temperature"] = 0.7

    result = compare_model_configuration(first, second)

    assert result["status"] == "PARTIAL_MATCH"
    assert "Reports use different generation options." in result["warnings"]


def test_unknown_model_versions_are_reported():
    first = make_report()
    second = make_report()

    for report in (first, second):
        provenance = report["metadata"]["provenance"]
        provenance["model_options"] = {"temperature": 0, "seed": 42}
        provenance["model_version"] = None

    result = compare_model_configuration(first, second)

    assert result["status"] == "PARTIAL_MATCH"
    assert "One or both model versions are unknown." in result["warnings"]


def test_different_recorded_model_versions_are_reported():
    first = make_report()
    second = make_report()

    for report in (first, second):
        report["metadata"]["provenance"]["model_options"] = {
            "temperature": 0,
        }

    first["metadata"]["provenance"]["model_version"] = "version-a"
    second["metadata"]["provenance"]["model_version"] = "version-b"

    result = compare_model_configuration(first, second)

    assert result["status"] == "PARTIAL_MATCH"
    assert "Reports use different model versions." in result["warnings"]


def test_combined_compatibility_reports_unknown_model_versions():
    first = make_report("dataset_sha256", fingerprint("dataset-a"))
    second = make_report("dataset_sha256", fingerprint("dataset-a"))

    for report in (first, second):
        provenance = report["metadata"]["provenance"]
        provenance["primary_scoring"] = "normalized-exact-v1"
        provenance["alternative_scoring"] = None
        provenance["model_options"] = None
        provenance["model_version"] = None

    result = compare_report_compatibility(first, second)

    assert result["status"] == "PARTIAL_MATCH"
    assert "Generation options are not fully recorded." in result["warnings"]
    assert "One or both model versions are unknown." in result["warnings"]


def test_combined_compatibility_allows_cross_model_comparison():
    first = make_report("dataset_sha256", fingerprint("dataset-a"))
    second = make_report("dataset_sha256", fingerprint("dataset-a"))

    second["metadata"]["model"] = "another-model"

    for report in (first, second):
        provenance = report["metadata"]["provenance"]
        provenance["primary_scoring"] = "normalized-exact-v1"
        provenance["alternative_scoring"] = None
        provenance["model_options"] = {"temperature": 0}
        provenance["model_version"] = "known-version"

    result = compare_report_compatibility(first, second)

    assert result["status"] == "PARTIAL_MATCH"
    assert "Reports use different models." in result["warnings"]


def test_combined_compatibility_rejects_missing_model_name():
    first = make_report("dataset_sha256", fingerprint("dataset-a"))
    second = make_report("dataset_sha256", fingerprint("dataset-a"))

    for report in (first, second):
        provenance = report["metadata"]["provenance"]
        provenance["primary_scoring"] = "normalized-exact-v1"
        provenance["alternative_scoring"] = None

    del second["metadata"]["model"]

    result = compare_report_compatibility(first, second)

    assert result["status"] == "UNVERIFIED"
    assert "model names" in result["reason"]
