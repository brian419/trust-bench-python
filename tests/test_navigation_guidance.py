"""Consistent keyboard help, tab shortcuts and focus recovery across workflows."""

from unittest.mock import MagicMock, patch

from pytest import mark, raises
from test_desktop_gui import make_test_app


def navigation_app():
    app = make_test_app()
    app.notebook = MagicMock()
    app.dataset_entry = MagicMock()
    app.keyboard_hint = MagicMock()
    app.narrator = MagicMock()
    app.narrator.enabled = False
    app.narrator.failed = False
    app.speech_enabled = MagicMock()
    app.speech_timer = None
    app.speech_poll_timer = None
    app.read_view_button = MagicMock()
    return app


@mark.parametrize(
    "index, name", [(0, "report_list"), (1, "previous_report"), (2, "dataset_entry")]
)
def test_direct_tab_jump_focuses_entry_without_traversing_other_controls(index, name):
    app = navigation_app()
    app.notebook.index.return_value = index
    assert app._select_tab(index) == "break"
    app.notebook.select.assert_called_once_with(index)
    app.root.after_idle.call_args.args[0]()
    getattr(app, name).focus_set.assert_called_once()


def test_rapid_tab_jumps_ignore_stale_focus_callbacks():
    app = navigation_app()
    app._select_tab(0)
    old = app.root.after_idle.call_args.args[0]
    app._select_tab(2)
    current = app.root.after_idle.call_args.args[0]
    app.notebook.index.return_value = 2
    old()
    app.report_list.focus_set.assert_not_called()
    current()
    app.dataset_entry.focus_set.assert_called_once()


def test_tab_focus_callback_does_nothing_after_close():
    app = navigation_app()
    app._select_tab(0)
    app.window_closed = True
    app.root.after_idle.call_args.args[0]()
    app.report_list.focus_set.assert_not_called()


@mark.parametrize("dialog_kind", ["error", "warning", "info", "file", "confirmation"])
def test_every_dialog_restores_original_focus_and_preserves_return_value(dialog_kind):
    app = navigation_app()
    origin = app.root.focus_get.return_value
    origin.winfo_class.return_value = "TButton"
    origin.instate.return_value = False
    dialog = MagicMock(return_value="chosen")
    assert app._dialog(dialog, dialog_kind, "Message") == "chosen"
    dialog.assert_called_once_with(dialog_kind, "Message", parent=app.root)
    origin.focus_set.assert_called_once()
    app.root.focus_set.assert_called_once()
    app.root.focus_force.assert_not_called()


def test_dialog_restores_focus_even_when_callback_fails():
    app = navigation_app()
    dialog = MagicMock(side_effect=RuntimeError("test"))
    with raises(RuntimeError):
        app._dialog(dialog, "Test", "Message")
    app.root.focus_get.return_value.focus_set.assert_called_once()


def test_dialog_falls_back_to_selected_tab_when_origin_is_disabled():
    app = navigation_app()
    origin = app.root.focus_get.return_value
    origin.winfo_class.return_value = "TButton"
    origin.instate.return_value = True
    app.notebook.index.return_value = 1
    app._dialog(MagicMock(), "Test", "Message")
    origin.focus_set.assert_not_called()
    app.previous_report.focus_set.assert_called_once()


def test_dismissed_compare_warning_allows_tabbing_from_trigger_button():
    app = navigation_app()
    app.previous_report.current.return_value = -1
    app.current_report.current.return_value = -1
    origin = app.root.focus_get.return_value
    origin.winfo_class.return_value = "TButton"
    origin.instate.return_value = False
    with patch("desktop_gui.showwarning") as warning:
        assert app.compare_selected_reports() is False
    warning.assert_called_once()
    origin.focus_set.assert_called_once()


def test_keyboard_help_explains_list_as_one_tab_stop_and_enter_return():
    app = navigation_app()
    with (
        patch("desktop_gui.showinfo") as help_dialog,
        patch("desktop_gui.platform", "darwin"),
    ):
        app.show_keyboard_help()
    text = help_dialog.call_args.args[1]
    assert "one Tab stop" in text
    assert "Command+1 Reports" in text
    assert "Enter/Return confirms" in text
    assert "off at startup" in text


def test_guidance_off_produces_no_speech_or_timer():
    app = navigation_app()
    app._set_keyboard_hint("Focused report")
    app._announce("An error", immediate=True)
    app.narrator.speak.assert_not_called()
    app.root.after.assert_not_called()


def test_rapid_focus_hints_debounce_and_dialog_speaks_immediately():
    app = navigation_app()
    app.narrator.enabled = True
    app._announce("First")
    first_timer = app.speech_timer
    app._announce("Second")
    app.root.after_cancel.assert_called_with(first_timer)
    app.narrator.speak.assert_not_called()
    app._dialog(MagicMock(), "Error", "Choose a report")
    app.narrator.speak.assert_called_once_with("Error. Choose a report")
    assert app.speech_timer is None


def test_toggle_off_stops_speech_and_cancels_pending_callbacks():
    app = navigation_app()
    app.speech_enabled.get.return_value = False
    app.speech_timer = "hint"
    app.speech_poll_timer = "poll"
    app.toggle_spoken_guidance()
    app.narrator.set_enabled.assert_called_once_with(False)
    app.read_view_button.configure.assert_called_with(state="disabled")
    assert app.speech_timer is None and app.speech_poll_timer is None
    app.narrator.speak.assert_not_called()


def test_speech_failure_turns_option_off_without_disrupting_evaluation():
    app = navigation_app()
    app.narrator.failed = True
    app.evaluation_running = True
    app._poll_speech()
    app.speech_enabled.set.assert_called_with(False)
    app.narrator.stop.assert_called_once()
    assert app.evaluation_running is True
    assert "turned off" in app.keyboard_hint.set.call_args.args[0]


@mark.parametrize("index", [0, 1, 2])
def test_read_current_view_is_explicit_and_bounded_for_all_tabs(index):
    app = navigation_app()
    app.narrator.enabled = True
    app.notebook.index.return_value = index
    displays = (app.report_display, app.comparison_display, app.evaluation_display)
    displays[index].get.return_value = "Details " * 1000
    app.read_current_view()
    text = app.narrator.speak.call_args.args[0]
    assert len(text) < 4000
    assert "End of excerpt" in text


def test_elapsed_ticks_are_not_narrated_repeatedly():
    app = navigation_app()
    app._announce = MagicMock()
    app._render_progress()
    app._render_progress()
    app._announce.assert_called_once()


def test_closing_cancels_speech_even_when_a_hint_is_pending():
    app = navigation_app()
    app.speech_timer = "hint"
    app.on_window_close()
    app.narrator.close.assert_called_once()
    app.root.after_cancel.assert_called_with("hint")
    app.root.destroy.assert_called_once()
