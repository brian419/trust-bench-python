"""Visible speech focus, concise narration, spoken browsing and lazy model discovery."""

from unittest.mock import MagicMock, patch

from pytest import mark

from ollama_readiness import OllamaReadiness
from spoken_choices import SpokenChoices
from test_navigation_guidance import navigation_app


def app_with_speech():
    app = navigation_app()
    app.narrator.enabled = True
    app.speech_toggle = MagicMock()
    app.speech_focus_frame = MagicMock()
    app.speech_focus_background = "background"
    app.speech_enabled.get.return_value = False
    app.speech_has_focus = False
    app.model_name.get.return_value = "gemma3:1b"
    app.model_selector = MagicMock()
    app.model_selector.instate.return_value = False
    app.model_selector.cget.return_value = ("gemma3:1b", "other:latest")
    app.choice_picker = None
    return app


def test_checkbox_focus_has_outline_and_explicit_focused_off_label():
    app = app_with_speech()
    app._speech_focus_in(MagicMock())
    app.speech_focus_frame.configure.assert_called_with(highlightbackground="#007aff")
    app.speech_toggle.configure.assert_called_with(text="Spoken guidance: Off [focused]")
    app._speech_focus_out(MagicMock())
    app.speech_focus_frame.configure.assert_called_with(highlightbackground="background")
    app.speech_toggle.configure.assert_called_with(text="Spoken guidance: Off")


def test_toggle_label_reflects_current_on_state_while_focused():
    app = app_with_speech()
    app.speech_enabled.get.return_value = True
    app.speech_has_focus = True
    app._update_speech_label()
    app.speech_toggle.configure.assert_called_with(text="Spoken guidance: On [focused]")


def test_focus_speech_omits_prefix_and_instructions_but_visual_hint_keeps_them():
    app = app_with_speech()
    app._announce = MagicMock()
    hint = "Keyboard focus: Compare Reports. Press Space or Enter/Return to activate."
    app._set_keyboard_hint(hint)
    app.keyboard_hint.set.assert_called_once_with(hint)
    app._announce.assert_called_once_with("Compare Reports")


def test_explicit_spoken_value_is_not_truncated_at_filename_dot():
    app = app_with_speech()
    app._announce = MagicMock()
    app._set_keyboard_hint("Detailed help", spoken="Current report. evaluation-one.json")
    app._announce.assert_called_once_with("Current report. evaluation-one.json")


@mark.parametrize("index, expected", [(0, 0), (1, 0), (2, 1)])
def test_models_discover_on_first_evaluate_visit_only(index, expected):
    app = app_with_speech()
    app.models_loaded = False
    app.notebook.index.return_value = index
    app.check_ollama = MagicMock()
    app._on_tab_changed(MagicMock())
    assert app.check_ollama.call_count == expected


def test_model_discovery_does_not_duplicate_pending_check_or_reload_known_list():
    app = app_with_speech()
    app.check_ollama = MagicMock()
    app.readiness_pending = True
    app._ensure_models_loaded()
    app.check_ollama.assert_not_called()
    app.readiness_pending = False
    app.models_loaded = True
    app._ensure_models_loaded()
    app.check_ollama.assert_not_called()


def test_empty_model_picker_requests_refresh_without_opening_blank_popup():
    app = app_with_speech()
    app.models_loaded = True
    app.model_selector.cget.return_value = ()
    app.check_ollama = MagicMock()
    event = MagicMock(widget=app.model_selector)
    with patch("desktop_gui.SpokenChoices") as chooser:
        assert app._open_dropdown(event) == "break"
    app.check_ollama.assert_called_once()
    chooser.assert_not_called()


def test_model_result_marks_discovery_loaded_and_preserves_typed_name():
    app = app_with_speech()
    app.readiness_pending = True
    app.readiness_request_id = 1
    app.pending_readiness_command = None
    app._handle_ollama_result(1, "gemma3:1b", OllamaReadiness(
        "READY", "gemma3:1b", "Ready", ("gemma3:1b", "other:latest"),
    ))
    assert app.models_loaded is True
    app.model_selector.configure.assert_called_with(values=("gemma3:1b", "other:latest"))
    app.model_name.set.assert_not_called()


@mark.parametrize("field", ["previous_report", "current_report", "model_selector"])
def test_spoken_dropdown_routes_all_fields_through_observable_chooser(field):
    app = app_with_speech()
    combo = getattr(app, field)
    combo.instate.return_value = False
    combo.cget.return_value = ("one", "two")
    event = MagicMock(widget=combo)
    with patch("desktop_gui.SpokenChoices") as chooser:
        app._open_dropdown(event)
    assert chooser.call_args.args[1] is combo
    combo.event_generate.assert_not_called()


def test_native_dropdown_is_retained_with_speech_off():
    app = app_with_speech()
    app.narrator.enabled = False
    combo = app.current_report
    combo.instate.return_value = False
    with patch("desktop_gui.SpokenChoices") as chooser:
        app._open_dropdown(MagicMock(widget=combo))
    chooser.assert_not_called()
    combo.event_generate.assert_called_once_with("<Down>")


def choice_picker():
    picker = SpokenChoices.__new__(SpokenChoices)
    picker.closed = False
    picker.focus_timer = None
    picker.last_highlight = None
    picker.values = ("evaluation-one.json", "evaluation-two.json")
    picker.window = MagicMock()
    picker.combo = MagicMock()
    picker.combo.cget.return_value = picker.values
    picker.listbox = MagicMock()
    picker.listbox.curselection.return_value = (1,)
    picker.announce = MagicMock()
    picker.on_close = MagicMock()
    return picker


def test_highlight_announces_before_confirmation_without_committing():
    picker = choice_picker()
    picker.highlight()
    picker.highlight()
    picker.announce.assert_called_once_with("2 of 2. evaluation-two.json")
    picker.combo.current.assert_not_called()
    picker.listbox.curselection.return_value = (0,)
    picker.highlight()
    picker.announce.assert_called_with("1 of 2. evaluation-one.json")


def test_confirmation_commits_and_restores_focus_once():
    picker = choice_picker()
    assert picker.commit() == "break"
    picker.commit()
    picker.combo.current.assert_called_once_with(1)
    picker.window.grab_release.assert_called_once()
    picker.combo.focus_set.assert_called_once()
    picker.combo.event_generate.assert_called_once_with("<<ComboboxSelected>>", when="tail")


def test_escape_cancels_without_changing_original_value_and_cleans_timer():
    picker = choice_picker()
    picker.focus_timer = "blur"
    picker.cancel()
    picker.combo.current.assert_not_called()
    picker.window.after_cancel.assert_called_once_with("blur")
    picker.window.destroy.assert_called_once()


def test_reordered_reports_commit_by_value_not_outdated_index():
    picker = choice_picker()
    picker.combo.cget.return_value = tuple(reversed(picker.values))
    picker.commit()
    picker.combo.current.assert_called_once_with(0)


def test_removed_report_is_not_replaced_by_another_report():
    picker = choice_picker()
    picker.combo.cget.return_value = ("different.json",)
    picker.commit()
    picker.combo.current.assert_not_called()
    assert "no longer available" in picker.announce.call_args.args[0]


def test_popup_constructor_binds_arrows_selection_confirmation_and_cancel():
    combo = MagicMock()
    combo.cget.return_value = ("one", "two")
    combo.current.return_value = 0
    combo.winfo_width.return_value = 400
    combo.winfo_rootx.return_value = combo.winfo_rooty.return_value = 50
    root = MagicMock()
    root.winfo_screenwidth.return_value = 1280
    root.winfo_screenheight.return_value = 800
    with (
        patch("spoken_choices.Toplevel"), patch("spoken_choices.Frame"),
        patch("spoken_choices.Label"), patch("spoken_choices.Scrollbar"),
        patch("spoken_choices.Listbox") as listbox,
    ):
        listbox.return_value.curselection.return_value = (0,)
        picker = SpokenChoices(root, combo, "Previous report", MagicMock(), MagicMock())
    bindings = {c.args[0]: c.args[1] for c in picker.window.bind.call_args_list}
    for key in ("Return", "KP_Enter", "space"):
        assert bindings[f"<{key}>"] == picker.commit
    assert bindings["<Escape>"] == picker.cancel
    picker.listbox.bind.assert_any_call("<<ListboxSelect>>", picker.highlight)
    picker.window.grab_set.assert_called_once()


def test_window_closure_destroys_spoken_chooser_without_restoring_focus():
    app = app_with_speech()
    app.choice_picker = MagicMock()
    app._close_accessibility()
    app.choice_picker.cancel.assert_called_once_with(restore_focus=False)


def test_late_popup_events_do_not_touch_destroyed_widgets():
    picker = choice_picker()
    picker.closed = True
    picker.highlight()
    picker.commit()
    picker.pointer_highlight(MagicMock())
    picker.traverse(1)
    picker.listbox.curselection.assert_not_called()
    picker.listbox.nearest.assert_not_called()


def test_click_outside_closes_popup_without_selecting():
    picker = choice_picker()
    picker.window.winfo_rootx.return_value = picker.window.winfo_rooty.return_value = 50
    picker.window.winfo_width.return_value = 500
    picker.window.winfo_height.return_value = 300
    assert picker._outside_click(MagicMock(x_root=10, y_root=10)) == "break"
    picker.combo.current.assert_not_called()
    picker.window.grab_release.assert_called_once()
