"""Keyboard actions expose focus and respect editing and disabled controls."""

from unittest.mock import MagicMock

from pytest import mark

from desktop_gui import KEYBOARD_HINT
from test_desktop_gui import make_test_app


def key_event(key="Return"):
    event = MagicMock()
    event.keysym = key
    event.widget.instate.return_value = False
    return event


@mark.parametrize("key", ["Return", "space"])
def test_button_key_invokes_once_after_matching_press_and_release(key):
    app = make_test_app()
    event = key_event(key)
    assert app._press_button(event) == "break"
    event.widget.invoke.assert_not_called()
    assert app._activate_button(event) == "break"
    app._activate_button(event)
    event.widget.invoke.assert_called_once()


def test_key_release_without_press_does_not_activate_button():
    app = make_test_app()
    event = key_event()
    app._activate_button(event)
    event.widget.invoke.assert_not_called()


def test_disabled_button_cannot_be_activated():
    app = make_test_app()
    event = key_event()
    app._press_button(event)
    event.widget.instate.return_value = True
    app._activate_button(event)
    event.widget.invoke.assert_not_called()


def test_focus_out_cancels_pending_activation_and_restores_normal_appearance():
    app = make_test_app()
    app.keyboard_hint = MagicMock()
    event = key_event()
    app._press_button(event)
    app._button_focus_out(event)
    app._activate_button(event)
    event.widget.invoke.assert_not_called()
    event.widget.configure.assert_called_with(default="normal")
    app.keyboard_hint.set.assert_called_with(KEYBOARD_HINT)


def test_focus_names_the_actual_button_and_requests_native_highlight():
    app = make_test_app()
    app.keyboard_hint = MagicMock()
    event = key_event()
    event.widget.cget.return_value = "Compare Reports"
    app._button_focus_in(event)
    event.widget.configure.assert_called_once_with(default="active")
    hint = app.keyboard_hint.set.call_args.args[0]
    assert "Compare Reports" in hint
    assert "Space or Enter/Return" in hint


def test_return_on_dropdown_forwards_to_native_down_binding():
    app = make_test_app()
    event = key_event()
    assert app._open_dropdown(event) == "break"
    event.widget.event_generate.assert_called_once_with("<Down>")
    event.widget.invoke.assert_not_called()


def test_disabled_dropdown_does_not_open():
    app = make_test_app()
    event = key_event()
    event.widget.instate.return_value = True
    app._open_dropdown(event)
    event.widget.event_generate.assert_not_called()


def test_space_in_editable_model_field_remains_text_input():
    app = make_test_app()
    event = key_event("space")
    assert app._dropdown_space(event) is None
    event.widget.event_generate.assert_not_called()


def test_space_in_readonly_report_dropdown_opens_choices():
    app = make_test_app()
    event = key_event("space")
    event.widget.instate.side_effect = [True, False]
    assert app._dropdown_space(event) == "break"
    event.widget.event_generate.assert_called_once_with("<Down>")


def test_button_traversal_skips_hidden_and_disabled_controls_and_binds_both_key_halves():
    app = make_test_app()
    parent, button, scrollbar = MagicMock(), MagicMock(), MagicMock()
    parent.winfo_children.return_value = [button, scrollbar]
    button.winfo_children.return_value = scrollbar.winfo_children.return_value = []
    button.winfo_class.return_value = "TButton"
    scrollbar.winfo_class.return_value = "TScrollbar"
    app._configure_button_keys(parent)
    accepts_focus = button.configure.call_args.kwargs["takefocus"]
    button.instate.return_value = False
    button.winfo_viewable.return_value = True
    assert accepts_focus() is True
    assert accepts_focus(".button") is True  # Tk appends the widget path to the script.
    button.instate.return_value = True
    assert accepts_focus() is False
    button.instate.return_value = False
    button.winfo_viewable.return_value = False
    assert accepts_focus() is False
    bindings = {call.args[0]: call.args[1] for call in button.bind.call_args_list}
    assert bindings["<KeyPress-Return>"] == app._press_button
    assert bindings["<KeyRelease-Return>"] == app._activate_button
    assert bindings["<KeyPress-space>"] == app._press_button
    assert bindings["<KeyRelease-space>"] == app._activate_button
    scrollbar.configure.assert_called_once_with(takefocus=False)
