"""GUI readiness coordination stays off the Tkinter event thread."""

from json import dumps
from queue import Queue
from threading import Event, Thread
from unittest.mock import MagicMock, patch

from pytest import fixture, mark

from desktop_gui import TrustBenchDesktop
from evaluation_progress import EvaluationProgress
from ollama_readiness import OllamaReadiness


@fixture
def app(tmp_path):
    desktop = TrustBenchDesktop.__new__(TrustBenchDesktop)
    desktop.root = MagicMock()
    desktop.progress = EvaluationProgress()
    for name in (
        "progress_status",
        "progress_counts",
        "progress_elapsed",
        "progress_bar",
    ):
        setattr(desktop, name, MagicMock())
    desktop.evaluation_events = Queue()
    for name in (
        "evaluation_running",
        "shutdown_pending",
        "shutdown_unverified",
        "close_requested",
        "readiness_pending",
        "window_closed",
        "event_poll_scheduled",
        "stop_requested",
    ):
        setattr(desktop, name, False)
    desktop.readiness_request_id = 0
    desktop.event_poll_id = None
    desktop.pending_readiness_command = None
    desktop.dataset_path = MagicMock()
    dataset = tmp_path / "cases.json"
    dataset.write_text("[]", encoding="utf-8")
    desktop.dataset_path.get.return_value = str(dataset)
    desktop.model_name = MagicMock()
    desktop.model_name.get.return_value = "gemma3:1b"
    desktop.ollama_status = MagicMock()
    desktop.ollama_status.get.return_value = "Not checked"
    for name in (
        "start_button",
        "stop_button",
        "check_ollama_button",
        "refresh_models_button",
        "model_selector",
        "report_path",
        "report_display",
        "comparison_display",
        "report_list",
        "previous_report",
        "current_report",
        "evaluation_display",
    ):
        setattr(desktop, name, MagicMock())
    desktop.saved_reports = []
    desktop.start_evaluation = MagicMock(return_value=True)
    return desktop


def queue_result(app, status="READY", request_id=None, model="gemma3:1b"):
    result = OllamaReadiness(status, model, f"Result: {status}")
    app.evaluation_events.put(
        (
            "readiness",
            (
                app.readiness_request_id if request_id is None else request_id,
                model,
                result,
            ),
        )
    )


def begin_start(app):
    with patch("desktop_gui.Thread"):
        assert app.check_and_start_evaluation() is True


def test_ui_start_waits_for_ready_event(app):
    begin_start(app)
    assert app.readiness_pending is True
    app.start_evaluation.assert_not_called()
    queue_result(app)
    app._drain_evaluation_events()
    app.start_evaluation.assert_called_once_with()
    assert app.readiness_pending is False


@mark.parametrize("status", ["UNAVAILABLE", "MODEL_MISSING", "CHECK_FAILED"])
def test_unsuccessful_check_blocks_launch_and_allows_retry(app, status):
    begin_start(app)
    queue_result(app, status)
    app._drain_evaluation_events()
    app.start_evaluation.assert_not_called()
    assert app.readiness_pending is False
    app.start_button.configure.assert_called_with(state="normal")
    begin_start(app)
    queue_result(app, "READY")
    app._drain_evaluation_events()
    app.start_evaluation.assert_called_once()


def test_check_only_never_starts_an_evaluation(app):
    with patch("desktop_gui.Thread"):
        assert app.check_ollama() is True
    queue_result(app)
    app._drain_evaluation_events()
    app.start_evaluation.assert_not_called()


def test_duplicate_check_or_start_does_not_launch_more_threads(app):
    with patch("desktop_gui.Thread") as thread:
        assert app.check_ollama() is True
        assert app.check_ollama() is False
        assert app.check_and_start_evaluation() is False
    thread.assert_called_once()


def test_previous_ready_result_does_not_skip_a_fresh_start_check(app):
    with patch("desktop_gui.Thread") as thread:
        assert app.check_ollama() is True
        queue_result(app)
        app._drain_evaluation_events()
        assert app.check_and_start_evaluation() is True
    assert thread.call_count == 2
    app.start_evaluation.assert_not_called()


@mark.parametrize("setting", ["model", "dataset", "removed_dataset"])
def test_settings_changed_during_check_do_not_auto_start(app, tmp_path, setting):
    begin_start(app)
    if setting == "model":
        app.model_name.get.return_value = "other:latest"
    elif setting == "dataset":
        other = tmp_path / "other.json"
        other.write_text("[]", encoding="utf-8")
        app.dataset_path.get.return_value = str(other)
    else:
        (tmp_path / "cases.json").unlink()
    queue_result(app)
    app._drain_evaluation_events()
    app.start_evaluation.assert_not_called()
    assert "changed" in app.ollama_status.set.call_args.args[0]
    assert app.pending_readiness_command is None


def test_stale_result_cannot_clear_a_newer_check(app):
    begin_start(app)
    queue_result(app, request_id=app.readiness_request_id - 1)
    app._drain_evaluation_events()
    assert app.readiness_pending is True
    app.start_evaluation.assert_not_called()


def test_close_during_check_discards_late_results(app):
    begin_start(app)
    request_id = app.readiness_request_id
    timer = app.event_poll_id
    app.on_window_close()
    app.root.destroy.assert_called_once()
    app.root.after_cancel.assert_called_once_with(timer)
    assert app.window_closed is True
    assert app.readiness_pending is False
    app.ollama_status.reset_mock()
    app.root.after.reset_mock()
    queue_result(app, request_id=request_id)
    app._drain_evaluation_events()
    app.start_evaluation.assert_not_called()
    app.ollama_status.set.assert_not_called()
    app.root.after.assert_not_called()


def test_worker_touches_no_tkinter_objects_and_recovers_from_exception(app):
    with patch(
        "desktop_gui.check_ollama_readiness", side_effect=RuntimeError("failed")
    ):
        app._check_ollama_worker(4, "gemma3:1b")
    event, (request_id, model, result) = app.evaluation_events.get_nowait()
    assert (event, request_id, model) == ("readiness", 4, "gemma3:1b")
    assert result.status == "CHECK_FAILED"
    app.root.assert_not_called()
    app.model_name.get.assert_not_called()
    app.ollama_status.set.assert_not_called()


def test_thread_start_failure_restores_controls(app):
    with patch("desktop_gui.Thread") as thread:
        thread.return_value.start.side_effect = RuntimeError("no thread")
        assert app.check_ollama() is False
    assert app.readiness_pending is False
    assert app.pending_readiness_command is None
    app.start_button.configure.assert_called_with(state="normal")
    app.check_ollama_button.configure.assert_called_with(state="normal")


def test_blank_model_start_and_invalid_dataset_start_do_not_launch_threads(app):
    with patch("desktop_gui.Thread") as thread, patch("desktop_gui.showerror"):
        app.model_name.get.return_value = " "
        assert app.check_and_start_evaluation() is False
        app.model_name.get.return_value = "gemma3:1b"
        app.dataset_path.get.return_value = "/missing/cases.json"
        assert app.check_and_start_evaluation() is False
    thread.assert_not_called()


@mark.parametrize(
    "state", ["evaluation_running", "shutdown_pending", "shutdown_unverified"]
)
def test_readiness_does_not_interfere_with_active_or_unverified_evaluation(app, state):
    setattr(app, state, True)
    with patch("desktop_gui.Thread") as thread:
        assert app.check_ollama() is False
        assert app.check_and_start_evaluation() is False
    thread.assert_not_called()


def test_auto_start_schedules_only_one_evaluation_poller(app):
    def start():
        app.evaluation_running = True
        app._schedule_event_poll()

    app.start_evaluation.side_effect = start
    begin_start(app)
    queue_result(app)
    app._drain_evaluation_events()
    # The original readiness callback plus one next evaluation callback.
    assert app.root.after.call_count == 2


def test_duplicate_ready_event_cannot_reenable_controls_during_evaluation(app):
    def start():
        app.evaluation_running = True
        app.start_button.configure(state="disabled")

    app.start_evaluation.side_effect = start
    begin_start(app)
    queue_result(app)
    queue_result(app)
    app._drain_evaluation_events()
    app.start_evaluation.assert_called_once()
    app.start_button.configure.assert_called_with(state="disabled")


def test_interface_wires_ui_start_to_preflight_without_startup_network(app):
    app.refresh_reports = MagicMock()
    with (
        patch("desktop_gui.Frame"),
        patch("desktop_gui.Label"),
        patch("desktop_gui.FocusFrame"),
        patch("desktop_gui.LabelFrame"),
        patch("desktop_gui.Entry"),
        patch("desktop_gui.Combobox"),
        patch("desktop_gui.Notebook"),
        patch("desktop_gui.Listbox"),
        patch("desktop_gui.StringVar"),
        patch("desktop_gui.BooleanVar"),
        patch("desktop_gui.Checkbutton"),
        patch("desktop_gui.ScrolledText"),
        patch("desktop_gui.Button") as button,
        patch("desktop_gui.Progressbar"),
        patch("desktop_gui.Thread") as thread,
        patch("desktop_gui.check_ollama_readiness") as check,
    ):
        app.build_interface()
    commands = {
        call.kwargs["text"]: call.kwargs.get("command")
        for call in button.call_args_list
    }
    assert commands["Start Evaluation"] == app.check_and_start_evaluation
    assert commands["Check Ollama"] == app.check_ollama
    assert commands["Setup Help"] == app.show_ollama_setup
    assert commands["Get Ollama (website)"] == app.open_ollama_download
    assert commands["Refresh Models"] == app.check_ollama
    assert commands["Stop Evaluation"] == app.stop_evaluation
    assert commands["Keyboard Help"] == app.show_keyboard_help
    assert commands["Read current view"] == app.read_current_view
    bindings = {call.args[0]: call.args[1] for call in app.root.bind.call_args_list}
    assert "<Control-Tab>" in bindings
    assert "<F6>" in bindings
    assert "<Tab>" in bindings
    assert "<Shift-Tab>" in bindings
    assert any(key.endswith("-Shift-Key-S>") for key in bindings)
    for number in (1, 2, 3):
        assert any(key.endswith(f"-Key-{number}>") for key in bindings)
    app.model_selector.bind.assert_any_call("<Return>", app._open_dropdown)
    app.report_list.bind.assert_any_call("<Return>", app.open_selected_report)
    thread.assert_not_called()
    check.assert_not_called()


def test_help_and_download_are_explicit_user_actions(app):
    with (
        patch("desktop_gui.open_browser") as browser,
        patch("desktop_gui.showinfo") as help_dialog,
        patch("desktop_gui.askyesno", return_value=True),
    ):
        app.show_ollama_setup()
        browser.assert_not_called()
        assert (
            "Reports and Compare work without Ollama" in help_dialog.call_args.args[1]
        )
        app.open_ollama_download()
    browser.assert_called_once_with("https://ollama.com/download/mac")


def test_reports_and_comparison_work_while_check_is_blocked(app, tmp_path):
    entered, release = Event(), Event()
    workers = []

    def check(model):
        entered.set()
        assert release.wait(timeout=5)
        return OllamaReadiness("UNAVAILABLE", model, "Open Ollama and retry.")

    def thread(**kwargs):
        worker = Thread(**kwargs)
        workers.append(worker)
        return worker

    report = {
        "metadata": {
            "model": "gemma3:1b",
            "dataset": "cases.json",
            "timestamp": "2026-10-25",
            "provenance": {
                "dataset_sha256": "a" * 64,
                "primary_scoring": "normalized-exact-v1",
                "alternative_scoring": None,
                "model_options": None,
                "model_version": None,
            },
        },
        "results": [
            {
                "id": "one",
                "question": "One?",
                "expected": "1",
                "generated": "1",
                "status": "PASS",
            }
        ],
    }
    paths = [tmp_path / "previous.json", tmp_path / "current.json"]
    for path in paths:
        path.write_text(dumps(report), encoding="utf-8")
    app.saved_reports = [str(path) for path in paths]
    app.previous_report.current.return_value = 0
    app.current_report.current.return_value = 1
    try:
        with (
            patch("desktop_gui.Thread", side_effect=thread),
            patch("desktop_gui.check_ollama_readiness", side_effect=check),
        ):
            assert app.check_ollama() is True
            assert entered.wait(timeout=2)
            assert app.load_report(str(paths[0])) is True
            assert app.compare_selected_reports() is True
            assert app.readiness_pending is True
            release.set()
            workers[0].join(timeout=2)
            assert not workers[0].is_alive()
        app._drain_evaluation_events()
        assert app.readiness_pending is False
        app.start_evaluation.assert_not_called()
    finally:
        release.set()
        for worker in workers:
            worker.join(timeout=2)


def test_empty_field_can_refresh_models_without_starting_or_changing_selection(app):
    app.model_name.get.return_value = ""
    with patch("desktop_gui.Thread"):
        assert app.check_ollama() is True
    result = OllamaReadiness("MODELS_AVAILABLE", "", "Choose a model.", ("gemma3:1b",))
    app._handle_ollama_result(app.readiness_request_id, "", result)
    app.model_selector.configure.assert_called_once_with(values=("gemma3:1b",))
    app.model_name.set.assert_not_called()
    app.start_evaluation.assert_not_called()


def test_empty_model_worker_requests_discovery_without_touching_widgets(app):
    with patch("desktop_gui.check_ollama_readiness") as check:
        app._check_ollama_worker(3, "")
    check.assert_called_once_with("", allow_empty=True)
    app.model_selector.configure.assert_not_called()


def test_missing_model_populates_choices_without_replacing_typed_name(app):
    begin_start(app)
    result = OllamaReadiness(
        "MODEL_MISSING", "gemma3:1b", "Choose another.", ("other:latest",)
    )
    app._handle_ollama_result(app.readiness_request_id, "gemma3:1b", result)
    app.model_selector.configure.assert_called_once_with(values=("other:latest",))
    app.model_name.set.assert_not_called()
    app.start_evaluation.assert_not_called()


def test_failed_refresh_clears_old_choices_and_allows_retry(app):
    with patch("desktop_gui.Thread"):
        app.check_ollama()
        queue_result(app, "UNAVAILABLE")
        app._drain_evaluation_events()
        app.model_selector.configure.assert_called_with(values=())
        app.refresh_models_button.configure.assert_called_with(state="normal")
        assert app.check_ollama() is True


def test_stale_refresh_cannot_replace_model_choices(app):
    begin_start(app)
    result = OllamaReadiness("READY", "gemma3:1b", "Ready", ("old:latest",))
    app._handle_ollama_result(app.readiness_request_id - 1, "gemma3:1b", result)
    app.model_selector.configure.assert_not_called()


def test_cancel_external_link_does_not_open_browser(app):
    with (
        patch("desktop_gui.askyesno", return_value=False) as confirm,
        patch("desktop_gui.open_browser") as browser,
    ):
        assert app.open_ollama_download() is False
    assert "https://ollama.com/download/mac" in confirm.call_args.args[1]
    assert "separate software" in confirm.call_args.args[1]
    browser.assert_not_called()


@mark.parametrize("outcome", [False, OSError("browser unavailable")])
def test_browser_failure_shows_address_for_manual_navigation(app, outcome):
    with (
        patch("desktop_gui.askyesno", return_value=True),
        patch(
            "desktop_gui.open_browser",
            **(
                {"side_effect": outcome}
                if isinstance(outcome, OSError)
                else {"return_value": outcome}
            ),
        ),
        patch("desktop_gui.showerror") as error,
    ):
        assert app.open_ollama_download() is False
    assert "https://ollama.com/download/mac" in error.call_args.args[1]
