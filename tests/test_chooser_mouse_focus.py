"""Opening gestures and transient native focus must not select or close choices."""

from unittest.mock import MagicMock

from pytest import mark
from test_guidance_choices import app_with_speech, choice_picker


@mark.parametrize("index", [None, 0, 1])
def test_reports_entry_announces_first_or_existing_report_without_opening(index):
    app = app_with_speech()
    app.saved_reports = ["first.json", "second.json"]
    app.report_list.curselection.return_value = () if index is None else (index,)
    app._spoken_report = MagicMock(return_value="Report with readable metadata")
    app._set_keyboard_hint = MagicMock()
    app.load_report = MagicMock()
    app._reports_focus_in(MagicMock())
    expected = 0 if index is None else index
    app._spoken_report.assert_called_once_with(expected)
    assert (
        app._set_keyboard_hint.call_args.kwargs["spoken"]
        == "Report with readable metadata"
    )
    if index is None:
        app.report_list.selection_set.assert_called_once_with(0)
        app.report_list.see.assert_called_once_with(0)
    else:
        app.report_list.selection_set.assert_not_called()
    app.load_report.assert_not_called()


def test_reports_entry_handles_empty_list_without_indexing():
    app = app_with_speech()
    app.saved_reports = []
    app.report_list.curselection.return_value = ()
    app._set_keyboard_hint = MagicMock()
    app._reports_focus_in(MagicMock())
    assert "No reports available" in app._set_keyboard_hint.call_args.kwargs["spoken"]
    app.report_list.selection_set.assert_not_called()


@mark.parametrize("field", ["previous_report", "current_report", "model_selector"])
def test_mouse_open_waits_until_release_then_idle_for_every_selector(field):
    app = app_with_speech()
    combo = getattr(app, field)
    combo.instate.side_effect = lambda states: (
        states == ["readonly"] and field != "model_selector"
    )
    combo.identify.return_value = "downarrow"
    combo.cget.return_value = ("one", "two")
    app.root.focus_get.return_value = combo
    app._show_spoken_choices = MagicMock()
    event = MagicMock(widget=combo)
    assert app._dropdown_click(event) == "break"
    combo.focus_set.assert_called_once()
    app._show_spoken_choices.assert_not_called()
    app.root.after_idle.assert_not_called()
    assert app._dropdown_release(event) == "break"
    app._show_spoken_choices.assert_not_called()
    app.root.after_idle.call_args.args[0]()
    app._show_spoken_choices.assert_called_once_with(combo)


@mark.parametrize("change", ["closed", "focus", "speech_off", "hidden"])
def test_pending_mouse_open_is_discarded_if_context_changes(change):
    app = app_with_speech()
    combo = app.current_report
    combo.instate.side_effect = lambda states: states == ["readonly"]
    app.root.focus_get.return_value = combo
    app._show_spoken_choices = MagicMock()
    event = MagicMock(widget=combo)
    app._dropdown_click(event)
    app._dropdown_release(event)
    if change == "closed":
        app.window_closed = True
    elif change == "focus":
        app.root.focus_get.return_value = app.previous_report
    elif change == "speech_off":
        app.narrator.enabled = False
    else:
        combo.winfo_viewable.return_value = False
    app.root.after_idle.call_args.args[0]()
    app._show_spoken_choices.assert_not_called()


def test_speech_off_preserves_native_mouse_press_and_release():
    app = app_with_speech()
    app.narrator.enabled = False
    combo = app.current_report
    combo.instate.side_effect = lambda states: states == ["readonly"]
    event = MagicMock(widget=combo)
    assert app._dropdown_click(event) is None
    assert app._dropdown_release(event) is None
    app.root.after_idle.assert_not_called()


def test_release_from_opening_click_cannot_confirm_report():
    picker = choice_picker()
    assert picker._pointer_release(MagicMock()) == "break"
    picker.combo.current.assert_not_called()
    assert picker.closed is False
    picker._pointer_press(MagicMock())
    picker._pointer_release(MagicMock())
    picker.combo.current.assert_called_once_with(1)


@mark.parametrize("focus", ["none", "origin", "inside", "outside"])
def test_transient_focus_is_not_treated_as_outside_action(focus):
    picker = choice_picker()
    if focus == "none":
        value = None
    elif focus == "origin":
        value = picker.combo
    else:
        value = MagicMock()
        value.winfo_toplevel.return_value = (
            picker.window if focus == "inside" else MagicMock()
        )
    picker.window.focus_get.return_value = value
    picker._check_focus()
    assert picker.closed is (focus == "outside")


def test_application_close_cancels_pending_mouse_open():
    app = app_with_speech()
    app.choice_open_timer = "pending chooser"
    app._close_accessibility()
    app.root.after_cancel.assert_called_with("pending chooser")
    assert app.choice_open_timer is None
