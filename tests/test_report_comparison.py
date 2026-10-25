from pytest import mark, raises

from report_comparison import (
    classify_status_change,
    compare_live_reports,
    compare_live_results,
    index_results_by_id,
    summarize_live_comparison,
)


@mark.parametrize(
    "previous,current,expected",
    [
        ("PASS", "PASS", "UNCHANGED"),
        ("FAIL", "FAIL", "UNCHANGED"),
        ("ERROR", "ERROR", "UNCHANGED"),
        ("FAIL", "PASS", "IMPROVEMENT"),
        ("PASS", "FAIL", "REGRESSION"),
        ("ERROR", "PASS", "RECOVERED"),
        ("ERROR", "FAIL", "RECOVERED"),
        ("PASS", "ERROR", "NEW_ERROR"),
        ("FAIL", "ERROR", "NEW_ERROR"),
    ],
)
def test_classify_status_change(previous, current, expected):
    assert classify_status_change(previous, current) == expected


def test_invalid_previous_status():
    with raises(ValueError, match="Unknown previous status"):
        classify_status_change("UNKNOWN", "PASS")


def test_invalid_current_status():
    with raises(ValueError, match="Unknown current status"):
        classify_status_change("PASS", "UNKNOWN")


def test_index_results_by_id():
    results = [
        {"id": "fact_002", "status": "FAIL"},
        {"id": "fact_001", "status": "PASS"},
    ]

    indexed = index_results_by_id(results)

    assert indexed["fact_001"]["status"] == "PASS"
    assert indexed["fact_002"]["status"] == "FAIL"


def test_index_empty_results():
    assert index_results_by_id([]) == {}


def test_duplicate_case_ids_are_rejected():
    results = [
        {"id": "fact_001", "status": "PASS"},
        {"id": "fact_001", "status": "FAIL"},
    ]

    with raises(ValueError, match="Duplicate case ID"):
        index_results_by_id(results)


def test_missing_case_id_is_rejected():
    results = [{"status": "PASS"}]

    with raises(ValueError, match="non-empty string ID"):
        index_results_by_id(results)


def test_invalid_results_list_is_rejected():
    with raises(ValueError, match="Results must be a list"):
        index_results_by_id({"id": "fact_001"})


def test_compare_live_results_detects_changes():
    previous = [
        {"id": "fact_001", "status": "PASS"},
        {"id": "fact_002", "status": "FAIL"},
        {"id": "fact_003", "status": "PASS"},
    ]

    current = [
        {"id": "fact_003", "status": "FAIL"},
        {"id": "fact_001", "status": "PASS"},
        {"id": "fact_002", "status": "PASS"},
    ]

    comparisons = compare_live_results(previous, current)

    changes = {item["id"]: item["change"] for item in comparisons}

    assert changes == {
        "fact_001": "UNCHANGED",
        "fact_002": "IMPROVEMENT",
        "fact_003": "REGRESSION",
    }


def test_compare_live_results_detects_added_cases():
    previous = [
        {"id": "fact_001", "status": "PASS"},
    ]

    current = [
        {"id": "fact_001", "status": "PASS"},
        {"id": "fact_002", "status": "FAIL"},
    ]

    comparisons = compare_live_results(previous, current)

    assert comparisons[1] == {
        "id": "fact_002",
        "previous_status": None,
        "current_status": "FAIL",
        "change": "ADDED",
    }


def test_compare_live_results_detects_removed_cases():
    previous = [
        {"id": "fact_001", "status": "PASS"},
        {"id": "fact_002", "status": "FAIL"},
    ]

    current = [
        {"id": "fact_001", "status": "PASS"},
    ]

    comparisons = compare_live_results(previous, current)

    assert comparisons[1] == {
        "id": "fact_002",
        "previous_status": "FAIL",
        "current_status": None,
        "change": "REMOVED",
    }


def test_compare_live_results_empty_reports():
    assert compare_live_results([], []) == []


def test_added_case_with_invalid_status_is_rejected():
    previous = []

    current = [
        {"id": "fact_001", "status": "UNKNOWN"},
    ]

    with raises(ValueError, match="Invalid current status"):
        compare_live_results(previous, current)


def test_removed_case_with_invalid_status_is_rejected():
    previous = [
        {"id": "fact_001", "status": "UNKNOWN"},
    ]

    current = []

    with raises(ValueError, match="Invalid previous status"):
        compare_live_results(previous, current)


def test_added_case_with_missing_status_is_rejected():
    previous = []

    current = [
        {"id": "fact_001"},
    ]

    with raises(ValueError, match="Invalid current status"):
        compare_live_results(previous, current)


def test_removed_case_with_missing_status_is_rejected():
    previous = [
        {"id": "fact_001"},
    ]

    current = []

    with raises(ValueError, match="Invalid previous status"):
        compare_live_results(previous, current)


def test_summarize_live_comparison():
    comparisons = [
        {"id": "fact_001", "change": "UNCHANGED"},
        {"id": "fact_002", "change": "IMPROVEMENT"},
        {"id": "fact_003", "change": "REGRESSION"},
        {"id": "fact_004", "change": "RECOVERED"},
        {"id": "fact_005", "change": "NEW_ERROR"},
        {"id": "fact_006", "change": "ADDED"},
        {"id": "fact_007", "change": "REMOVED"},
        {"id": "fact_008", "change": "IMPROVEMENT"},
    ]

    summary = summarize_live_comparison(comparisons)

    assert summary == {
        "total_cases": 8,
        "unchanged": 1,
        "improvements": 2,
        "regressions": 1,
        "recovered": 1,
        "new_errors": 1,
        "added": 1,
        "removed": 1,
    }


def test_summarize_empty_comparison():
    summary = summarize_live_comparison([])

    assert summary == {
        "total_cases": 0,
        "unchanged": 0,
        "improvements": 0,
        "regressions": 0,
        "recovered": 0,
        "new_errors": 0,
        "added": 0,
        "removed": 0,
    }


def test_summarize_unknown_change_is_rejected():
    comparisons = [
        {"id": "fact_001", "change": "UNKNOWN"},
    ]

    with raises(ValueError, match="Unknown comparison change"):
        summarize_live_comparison(comparisons)


def make_live_report(results, dataset_hash="a" * 64):
    return {
        "metadata": {
            "model": "gemma3:1b",
            "provenance": {
                "dataset_sha256": dataset_hash,
                "primary_scoring": "normalized-exact-v1",
                "alternative_scoring": None,
                "model_options": None,
                "model_version": None,
            },
        },
        "results": results,
    }


def test_compare_live_reports_end_to_end():
    previous = make_live_report(
        [
            {"id": "fact_001", "status": "FAIL"},
            {"id": "fact_002", "status": "PASS"},
        ]
    )

    current = make_live_report(
        [
            {"id": "fact_002", "status": "FAIL"},
            {"id": "fact_001", "status": "PASS"},
        ]
    )

    result = compare_live_reports(previous, current)

    assert result["compatibility"]["status"] == "PARTIAL_MATCH"
    assert result["summary"]["improvements"] == 1
    assert result["summary"]["regressions"] == 1
    assert len(result["comparisons"]) == 2


def test_compare_live_reports_rejects_different_datasets():
    previous = make_live_report(
        [{"id": "fact_001", "status": "PASS"}],
        dataset_hash="a" * 64,
    )
    current = make_live_report(
        [{"id": "fact_001", "status": "PASS"}],
        dataset_hash="b" * 64,
    )

    with raises(ValueError, match="Reports cannot be compared"):
        compare_live_reports(previous, current)


def test_compare_live_reports_preserves_warnings():
    previous = make_live_report(
        [
            {"id": "fact_001", "status": "PASS"},
        ]
    )
    current = make_live_report(
        [
            {"id": "fact_001", "status": "PASS"},
        ]
    )

    result = compare_live_reports(previous, current)

    warnings = result["compatibility"]["warnings"]

    assert "Generation options are not fully recorded." in warnings
    assert "One or both model versions are unknown." in warnings


def test_compare_live_reports_rejects_consistency_reports():
    report = {
        "metadata": {
            "model": "gemma3:1b",
            "repetitions": 3,
            "provenance": {
                "inputs_sha256": "a" * 64,
                "scoring_method": None,
                "prompt_format": "plain-question-v1",
                "model_options": {"temperature": 0.7},
                "model_version": None,
            },
        },
        "results": [],
    }

    with raises(ValueError, match="requires two live-evaluation"):
        compare_live_reports(report, report)


def test_compare_live_reports_rejects_injection_reports():
    report = {
        "metadata": {
            "model": "gemma3:1b",
            "provenance": {
                "dataset_sha256": "a" * 64,
                "scoring_method": "prompt-injection-target-match-v1",
                "prompt_format": "single_prompt_delimited_document_v1",
                "model_options": {"temperature": 0},
                "model_version": None,
            },
        },
        "results": [],
    }

    with raises(ValueError, match="requires two live-evaluation"):
        compare_live_reports(report, report)


def test_compare_live_reports_rejects_mixed_report_types():
    live_report = make_live_report(
        [
            {"id": "fact_001", "status": "PASS"},
        ]
    )

    injection_report = {
        "metadata": {
            "model": "gemma3:1b",
            "provenance": {
                "dataset_sha256": "a" * 64,
                "scoring_method": "prompt-injection-target-match-v1",
                "prompt_format": "single_prompt_delimited_document_v1",
            },
        },
        "results": [],
    }

    with raises(ValueError, match="requires two live-evaluation"):
        compare_live_reports(live_report, injection_report)


def test_compare_live_reports_rejects_missing_previous_results():
    previous = make_live_report([])
    current = make_live_report([])

    del previous["results"]

    with raises(ValueError, match="previous report must contain"):
        compare_live_reports(previous, current)


def test_compare_live_reports_rejects_missing_current_results():
    previous = make_live_report([])
    current = make_live_report([])

    del current["results"]

    with raises(ValueError, match="current report must contain"):
        compare_live_reports(previous, current)


def test_compare_live_reports_rejects_invalid_previous_results():
    previous = make_live_report([])
    current = make_live_report([])

    previous["results"] = {}

    with raises(ValueError, match="previous report must contain"):
        compare_live_reports(previous, current)


def test_compare_live_reports_rejects_invalid_current_results():
    previous = make_live_report([])
    current = make_live_report([])

    current["results"] = "invalid"

    with raises(ValueError, match="current report must contain"):
        compare_live_reports(previous, current)
