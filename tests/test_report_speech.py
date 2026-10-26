"""Report speech describes metadata and list position, never opaque filenames."""

from json import dumps
from unittest.mock import MagicMock, patch

from pytest import mark
from test_navigation_guidance import navigation_app

from report_speech import (
    MAX_DESCRIPTION_BYTES,
    report_speech_details,
    spoken_model_name,
)
from spoken_choices import SpokenChoices


@mark.parametrize(
    "name, expected",
    [
        ("gemma3:1b", "gemma 3 version 1 billion parameters"),
        ("llama3.2:3b", "llama 3.2 version 3 billion parameters"),
        ("team/my_model:latest", "team slash my model version latest"),
        (None, "model not recorded"),
        ("a" * 32, "model name unavailable"),
    ],
)
def test_model_notation_is_spoken_as_words(name, expected):
    assert spoken_model_name(name) == expected


def test_report_metadata_replaces_long_identifier_and_extension(tmp_path):
    path = tmp_path / ("evaluation-" + "a" * 32 + ".json")
    path.write_text(
        dumps(
            {
                "metadata": {
                    "timestamp": "2026-10-25T19:04:04",
                    "model": "gemma3:1b",
                }
            }
        )
    )
    text = report_speech_details(path)
    assert "October 25, 2026 at 7:04:04 PM" in text
    assert "time zone not recorded" in text
    assert "gemma 3 version 1 billion parameters" in text
    assert "a" * 32 not in text
    assert ".json" not in text and str(tmp_path) not in text


@mark.parametrize(
    "content",
    [
        "invalid",
        "null",
        "[]",
        '{"metadata":[]}',
        '{"metadata":{"timestamp":"invalid"}}',
    ],
)
def test_unreadable_metadata_uses_file_time_without_speaking_filename(
    tmp_path, content
):
    path = tmp_path / "evaluation-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.json"
    path.write_text(content)
    text = report_speech_details(path)
    assert text.startswith("File last modified ")
    assert "bbbbbbbb" not in text


def test_missing_file_has_clear_fallback(tmp_path):
    assert report_speech_details(tmp_path / "missing.json") == "Date unavailable"


def test_description_read_is_bounded_for_large_reports(tmp_path):
    path = tmp_path / "large.json"
    path.write_bytes(b"x" * (MAX_DESCRIPTION_BYTES + 2))
    with patch("report_speech.loads") as decode:
        text = report_speech_details(path)
    decode.assert_not_called()
    assert text.startswith("File last modified ")


def speech_app():
    app = navigation_app()
    app.narrator.enabled = True
    app.saved_reports = [
        "/reports/evaluation-" + "a" * 32 + ".json",
        "/reports/evaluation-" + "b" * 32 + ".json",
    ]
    app.model_selector = MagicMock()
    app._announce = MagicMock()
    return app


def test_report_details_cached_but_ordinal_stays_in_current_list_order():
    app = speech_app()
    with patch(
        "desktop_gui.report_speech_details", return_value="Run on October 25"
    ) as describe:
        first = app._spoken_report(0)
        app._spoken_report(0)
        app.saved_reports.reverse()
        moved = app._spoken_report(1)
    describe.assert_called_once()
    assert first == "Report 1 of 2. Run on October 25"
    assert moved == "Report 2 of 2. Run on October 25"


def test_guidance_off_does_not_read_report_files():
    app = speech_app()
    app.narrator.enabled = False
    with patch("desktop_gui.report_speech_details") as describe:
        assert app._spoken_report(0) == "Report 1 of 2"
    describe.assert_not_called()


@mark.parametrize("field", ["previous_report", "current_report"])
def test_compare_focus_and_confirm_use_same_friendly_report_description(field):
    app = speech_app()
    combo = getattr(app, field)
    combo.get.return_value = "evaluation-" + "b" * 32 + ".json"
    combo.current.return_value = 1
    with patch(
        "desktop_gui.report_speech_details", return_value="Run on October 25. Gemma 3"
    ):
        text = app._spoken_field(combo, "Current report")
    assert text == "Current report. Report 2 of 2. Run on October 25. Gemma 3"
    assert "bbbbbbbb" not in text


def test_reports_list_selection_speaks_friendly_label():
    app = speech_app()
    app.report_list.curselection.return_value = (0,)
    with patch("desktop_gui.report_speech_details", return_value="Run on October 25"):
        app._announce_report_selection(MagicMock())
    app._announce.assert_called_once_with("Report 1 of 2. Run on October 25")


def test_spoken_chooser_uses_description_callback_instead_of_visible_filename():
    picker = SpokenChoices.__new__(SpokenChoices)
    picker.closed = False
    picker.last_highlight = None
    picker.values = ("evaluation-" + "a" * 32 + ".json",)
    picker.listbox = MagicMock()
    picker.listbox.curselection.return_value = (0,)
    picker.describe = MagicMock(return_value="Report 1 of 1. Run on October 25")
    picker.announce = MagicMock()
    picker.highlight()
    picker.announce.assert_called_once_with("Report 1 of 1. Run on October 25")
    picker.describe.assert_called_once_with(0, picker.values[0])


def test_manual_model_field_speech_does_not_invent_a_list_position():
    app = speech_app()
    app.model_selector.get.return_value = "gemma3:1b"
    assert app._spoken_field(app.model_selector, "Ollama model") == (
        "Ollama model. gemma 3 version 1 billion parameters"
    )
