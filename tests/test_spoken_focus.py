"""Global speech controls remain reachable from every workflow's Tab cycle."""

from unittest.mock import MagicMock

from pytest import mark

from test_navigation_guidance import navigation_app


def focus_app(index):
    app = navigation_app()
    app.speech_toggle = MagicMock()
    app.keyboard_help_button = MagicMock()
    app.refresh_reports_button = MagicMock()
    app.notebook.index.return_value = index
    return app


@mark.parametrize("index", [0, 1, 2])
def test_tab_from_workflow_output_enters_spoken_guidance(index):
    app = focus_app(index)
    event = MagicMock()
    event.widget = (app.report_display, app.comparison_display, app.evaluation_display)[index]
    assert app._focus_next(event) == "break"
    app.speech_toggle.focus_set.assert_called_once()
    event.widget.tk_focusNext.assert_not_called()


@mark.parametrize("index", [0, 1, 2])
def test_shift_tab_from_first_workflow_control_reaches_global_help(index):
    app = focus_app(index)
    event = MagicMock()
    event.widget = (app.refresh_reports_button, app.previous_report, app.dataset_entry)[index]
    assert app._focus_previous(event) == "break"
    app.keyboard_help_button.focus_set.assert_called_once()


@mark.parametrize("enabled", [False, True])
def test_global_forward_cycle_includes_checkbox_and_skips_disabled_read_button(enabled):
    app = focus_app(0)
    app.read_view_button.instate.return_value = not enabled
    event = MagicMock()
    event.widget = app.speech_toggle
    app._focus_next(event)
    target = app.read_view_button if enabled else app.keyboard_help_button
    target.focus_set.assert_called_once()


@mark.parametrize("enabled", [False, True])
def test_global_reverse_cycle_includes_checkbox_and_skips_disabled_read_button(enabled):
    app = focus_app(1)
    app.read_view_button.instate.return_value = not enabled
    event = MagicMock()
    event.widget = app.keyboard_help_button
    app._focus_previous(event)
    target = app.read_view_button if enabled else app.speech_toggle
    target.focus_set.assert_called_once()


def test_f6_focuses_checkbox_without_changing_speech_setting():
    app = focus_app(2)
    assert app._focus_spoken_guidance() == "break"
    app.speech_toggle.focus_set.assert_called_once()
    app.speech_enabled.set.assert_not_called()
    app.narrator.set_enabled.assert_not_called()


@mark.parametrize("index", [0, 1, 2])
def test_reverse_from_speech_checkbox_returns_to_current_workflow_output(index):
    app = focus_app(index)
    event = MagicMock()
    event.widget = app.speech_toggle
    app._focus_previous(event)
    target = (app.report_display, app.comparison_display, app.evaluation_display)[index]
    target.focus_set.assert_called_once()
