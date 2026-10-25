from json import dumps
from queue import Queue
from subprocess import TimeoutExpired
from threading import Event, Lock, Thread
from unittest.mock import MagicMock, patch

from desktop_gui import PROJECT_ROOT, TrustBenchDesktop


def make_test_app():
    app = TrustBenchDesktop.__new__(TrustBenchDesktop)
    app.report_path = MagicMock()
    app.report_display = MagicMock()
    app.comparison_display = MagicMock()
    app.report_list = MagicMock()
    app.saved_reports = []
    app.previous_report = MagicMock()
    app.current_report = MagicMock()
    app.dataset_path = MagicMock()
    app.model_name = MagicMock()
    app.evaluation_display = MagicMock()
    app.root = MagicMock()
    app.start_button = MagicMock()
    app.stop_button = MagicMock()
    app.evaluation_running = False
    app.evaluation_events = Queue()
    app.latest_evaluation_report = None
    app.active_evaluation_process = None
    app.stop_requested = False
    app.shutdown_pending = False
    app.shutdown_unverified = False
    app.close_requested = False
    app.evaluation_finished = False
    app.shutdown_lock = Lock()
    app.shutdown_attempted = False
    app.shutdown_verified = False
    app.readiness_pending = False
    app.readiness_request_id = 0
    app.pending_readiness_command = None
    app.event_poll_scheduled = False
    app.event_poll_id = None
    app.window_closed = False
    app.check_ollama_button = MagicMock()
    app.ollama_status = MagicMock()
    return app


def test_load_report_success():
    app = make_test_app()

    with patch(
        "desktop_gui.generate_text_report",
        return_value="Formatted evaluation report",
    ):
        result = app.load_report("evaluation.json")

    assert result is True
    app.report_path.set.assert_called_once_with("evaluation.json")
    app.report_display.insert.assert_called_once_with(
        "end",
        "Formatted evaluation report",
    )


def test_load_report_error_preserves_display():
    app = make_test_app()

    with (
        patch(
            "desktop_gui.generate_text_report",
            side_effect=ValueError("Invalid report"),
        ),
        patch("desktop_gui.showerror") as error_dialog,
    ):
        result = app.load_report("invalid.json")

    assert result is False
    app.report_path.set.assert_not_called()
    app.report_display.delete.assert_not_called()
    error_dialog.assert_called_once_with(
        "Unable to Open Report",
        "Invalid report",
    )


def test_open_report_cancel():
    app = make_test_app()
    app.load_report = MagicMock()

    with patch(
        "desktop_gui.askopenfilename",
        return_value="",
    ):
        app.open_report()

    app.load_report.assert_not_called()


def test_open_report_selection():
    app = make_test_app()
    app.load_report = MagicMock()

    with patch(
        "desktop_gui.askopenfilename",
        return_value="evaluation.json",
    ):
        app.open_report()

    app.load_report.assert_called_once_with("evaluation.json")


def test_refresh_reports():
    app = make_test_app()

    with patch(
        "desktop_gui.list_saved_reports",
        return_value=[
            "reports/evaluation-first.json",
            "reports/evaluation-second.json",
        ],
    ) as browser:
        result = app.refresh_reports()

    assert result is True

    browser.assert_called_once_with(
        str(PROJECT_ROOT / "reports")
    )

    assert app.saved_reports == [
        "reports/evaluation-first.json",
        "reports/evaluation-second.json",
    ]

    app.report_list.delete.assert_called_once_with(0, "end")
    assert app.report_list.insert.call_count == 2


def test_open_selected_report():
    app = make_test_app()

    app.saved_reports = [
        "reports/evaluation-first.json",
        "reports/evaluation-second.json",
    ]

    app.report_list.curselection.return_value = (1,)
    app.load_report = MagicMock(return_value=True)

    result = app.open_selected_report()

    assert result is True
    app.load_report.assert_called_once_with("reports/evaluation-second.json")


def test_open_selected_report_without_selection():
    app = make_test_app()

    app.report_list.curselection.return_value = ()
    app.load_report = MagicMock()

    result = app.open_selected_report()

    assert result is False
    app.load_report.assert_not_called()


def test_compare_selected_reports_success():
    app = make_test_app()
    app.saved_reports = [
        "reports/previous.json",
        "reports/current.json",
    ]

    app.previous_report.current.return_value = 0
    app.current_report.current.return_value = 1

    with patch(
        "desktop_gui.generate_comparison_text",
        return_value="Comparison results",
    ) as compare:
        result = app.compare_selected_reports()

    assert result is True
    compare.assert_called_once_with(
        "reports/previous.json",
        "reports/current.json",
    )
    app.comparison_display.insert.assert_called_once_with(
        "end",
        "Comparison results",
    )
    app.report_display.insert.assert_not_called()


def test_compare_requires_both_reports():
    app = make_test_app()

    app.previous_report.current.return_value = -1
    app.current_report.current.return_value = 0

    with patch("desktop_gui.showwarning") as warning:
        result = app.compare_selected_reports()

    assert result is False
    warning.assert_called_once()
    app.comparison_display.delete.assert_not_called()


def test_compare_rejects_same_report():
    app = make_test_app()

    app.previous_report.current.return_value = 0
    app.current_report.current.return_value = 0

    with patch("desktop_gui.showwarning") as warning:
        result = app.compare_selected_reports()

    assert result is False
    warning.assert_called_once()
    app.comparison_display.delete.assert_not_called()


def test_compare_error_preserves_display():
    app = make_test_app()
    app.saved_reports = [
        "reports/previous.json",
        "reports/current.json",
    ]

    app.previous_report.current.return_value = 0
    app.current_report.current.return_value = 1

    with (
        patch(
            "desktop_gui.generate_comparison_text",
            side_effect=ValueError("Reports are incompatible"),
        ),
        patch("desktop_gui.showerror") as error_dialog,
    ):
        result = app.compare_selected_reports()

    assert result is False
    app.comparison_display.delete.assert_not_called()
    error_dialog.assert_called_once_with(
        "Unable to Compare Reports",
        "Reports are incompatible",
    )


def test_build_interface_creates_separate_tabs():
    app = make_test_app()
    app.root = MagicMock()

    report_view = MagicMock()
    comparison_view = MagicMock()
    evaluation_view = MagicMock()

    with (
        patch("desktop_gui.Frame"),
        patch("desktop_gui.Label"),
        patch("desktop_gui.LabelFrame"),
        patch("desktop_gui.Button"),
        patch("desktop_gui.Combobox"),
        patch("desktop_gui.Entry"),
        patch("desktop_gui.Notebook") as notebook,
        patch("desktop_gui.Listbox"),
        patch("desktop_gui.StringVar"),
        patch(
            "desktop_gui.ScrolledText",
            side_effect=[report_view, comparison_view, evaluation_view],
        ) as text_widgets,
        patch.object(app, "refresh_reports"),
    ):
        app.build_interface()

        assert notebook.return_value.add.call_count == 3

    labels = [call.kwargs["text"] for call in notebook.return_value.add.call_args_list]

    assert labels == ["Reports", "Compare", "Evaluate"]

    assert text_widgets.call_count == 3
    assert app.report_display is report_view
    assert app.comparison_display is comparison_view
    assert app.report_display is not app.comparison_display
    assert app.evaluation_display is evaluation_view


def test_preview_evaluation_success():
    app = make_test_app()

    app.dataset_path.get.return_value = "eval-read-live.json"
    app.model_name.get.return_value = "gemma3:1b"

    with patch(
        "desktop_gui.build_live_command",
        return_value=["python3", "trustbench.py", "live"],
    ) as builder:
        result = app.preview_evaluation()

    assert result is True

    builder.assert_called_once_with(
        "eval-read-live.json",
        "gemma3:1b",
    )

    app.evaluation_display.insert.assert_called_once_with(
        "end",
        "python3 trustbench.py live",
    )


def test_preview_evaluation_invalid_settings():
    app = make_test_app()

    app.dataset_path.get.return_value = ""
    app.model_name.get.return_value = "gemma3:1b"

    with (
        patch(
            "desktop_gui.build_live_command",
            side_effect=ValueError("Choose an evaluation dataset."),
        ),
        patch("desktop_gui.showerror") as error_dialog,
    ):
        result = app.preview_evaluation()

    assert result is False
    app.evaluation_display.delete.assert_not_called()

    error_dialog.assert_called_once_with(
        "Invalid Evaluation Settings",
        "Choose an evaluation dataset.",
    )


def test_browse_dataset_cancel():
    app = make_test_app()

    with patch(
        "desktop_gui.askopenfilename",
        return_value="",
    ):
        app.browse_dataset()

    app.dataset_path.set.assert_not_called()


def test_start_evaluation_starts_worker():
    app = make_test_app()
    app.dataset_path.get.return_value = "questions.json"
    app.model_name.get.return_value = "gemma3:1b"

    command = ["python3", "trustbench.py", "live"]

    with (
        patch(
            "desktop_gui.build_live_command",
            return_value=command,
        ),
        patch("desktop_gui.Thread") as thread,
    ):
        result = app.start_evaluation()

    assert result is True
    assert app.evaluation_running is True

    app.start_button.configure.assert_called_with(state="disabled")

    thread.assert_called_once_with(
        target=app._run_evaluation_worker,
        args=(command,),
        daemon=True,
    )
    thread.return_value.start.assert_called_once()
    app.root.after.assert_called_once()


def test_start_evaluation_prevents_duplicate():
    app = make_test_app()
    app.evaluation_running = True

    with patch("desktop_gui.build_live_command") as builder:
        result = app.start_evaluation()

    assert result is False
    builder.assert_not_called()


def test_evaluation_worker_collects_output():
    app = make_test_app()

    process = MagicMock()
    process.stdout = iter(["Running...\n", "Finished.\n"])
    process.wait.return_value = 0

    with patch(
        "desktop_gui.run_live_command",
        return_value=process,
    ):
        app._run_evaluation_worker(["python3", "trustbench.py"])

    assert app.evaluation_events.get_nowait() == (
        "process",
        process,
    )

    assert app.evaluation_events.get_nowait() == (
        "output",
        "Running...\n",
    )

    assert app.evaluation_events.get_nowait() == (
        "output",
        "Finished.\n",
    )

    assert app.evaluation_events.get_nowait() == ("done", 0)

    assert app.evaluation_events.empty()


def test_evaluation_worker_captures_report_path():
    app = make_test_app()

    process = MagicMock()
    process.stdout = iter(
        [
            "Starting evaluation...\n",
            "Report saved to: reports/evaluation-example.json\n",
            "Passed: 2\n",
        ]
    )
    process.wait.return_value = 0

    with patch(
        "desktop_gui.run_live_command",
        return_value=process,
    ):
        app._run_evaluation_worker(["python3", "trustbench.py", "live"])

    events = []

    while not app.evaluation_events.empty():
        events.append(app.evaluation_events.get_nowait())

    assert (
        "report_path",
        "reports/evaluation-example.json",
    ) in events

    assert events[-1] == ("done", 0)


def test_drain_evaluation_completion():
    app = make_test_app()
    app.evaluation_running = True

    app.evaluation_events.put(("output", "Running...\n"))
    app.evaluation_events.put(("done", 0))
    app.refresh_reports = MagicMock()

    app._drain_evaluation_events()

    assert app.evaluation_running is False
    app.start_button.configure.assert_called_with(state="normal")
    app.refresh_reports.assert_called_once()
    app.root.after.assert_not_called()
    assert app.evaluation_display.insert.call_count == 2


def test_completion_reports_request_errors(tmp_path):
    app = make_test_app()
    path = tmp_path / "evaluation-errors.json"

    path.write_text(
        dumps(
            {
                "metadata": {},
                "results": [
                    {"id": "one", "status": "ERROR"},
                    {"id": "two", "status": "ERROR"},
                ],
            }
        ),
        encoding="utf-8",
    )

    app.latest_evaluation_report = str(path)

    message = app._evaluation_completion_message(0)

    assert "Completed with request errors" in message
    assert "Request errors: 2" in message
    assert "Passed: 0" in message


def test_completion_reports_clean_run(tmp_path):
    app = make_test_app()
    path = tmp_path / "evaluation-clean.json"

    path.write_text(
        dumps(
            {
                "metadata": {},
                "results": [
                    {"id": "one", "status": "PASS"},
                    {"id": "two", "status": "FAIL"},
                ],
            }
        ),
        encoding="utf-8",
    )

    app.latest_evaluation_report = str(path)

    message = app._evaluation_completion_message(0)

    assert "Completed without request errors" in message
    assert "Passed: 1" in message
    assert "Failed: 1" in message
    assert "Request errors: 0" in message


def test_completion_nonzero_exit():
    app = make_test_app()

    message = app._evaluation_completion_message(1)

    assert "exited with code 1" in message


def test_stop_evaluation_without_active_run():
    app = make_test_app()

    with patch.object(app, "_begin_evaluation_shutdown") as shutdown:
        result = app.stop_evaluation()

    assert result is False
    assert app.stop_requested is False
    shutdown.assert_not_called()
    app.stop_button.configure.assert_not_called()


def test_stop_evaluation_with_active_process():
    app = make_test_app()
    app.evaluation_running = True
    process = MagicMock()
    app.active_evaluation_process = process

    app._begin_evaluation_shutdown = MagicMock()

    result = app.stop_evaluation()

    assert result is True
    assert app.stop_requested is True

    app._begin_evaluation_shutdown.assert_called_once_with(process)
    app.stop_button.configure.assert_called_with(state="disabled")


def test_stop_evaluation_before_process_registration():
    app = make_test_app()
    app.evaluation_running = True
    app._begin_evaluation_shutdown = MagicMock()

    assert app.stop_evaluation() is True

    app._begin_evaluation_shutdown.assert_not_called()

    process = MagicMock()
    app.evaluation_events.put(("process", process))
    app._drain_evaluation_events()

    app._begin_evaluation_shutdown.assert_called_once_with(process)


def test_evaluation_completion_clears_active_process():
    app = make_test_app()
    app.evaluation_running = True
    app.active_evaluation_process = MagicMock()
    app.refresh_reports = MagicMock()

    app.evaluation_events.put(("done", 1))
    app._drain_evaluation_events()

    assert app.evaluation_running is False
    assert app.active_evaluation_process is None

    app.start_button.configure.assert_called_with(state="normal")
    app.stop_button.configure.assert_called_with(state="disabled")


def test_shutdown_runs_in_background_thread():
    app = make_test_app()
    process = MagicMock()

    with patch("desktop_gui.Thread") as thread:
        app._begin_evaluation_shutdown(process)

    assert app.shutdown_pending is True
    thread.assert_called_once_with(
        target=app._shutdown_evaluation_worker,
        args=(process,),
        daemon=True,
    )
    thread.return_value.start.assert_called_once()


def test_shutdown_worker_queues_result():
    app = make_test_app()
    process = MagicMock()

    with patch(
        "desktop_gui.stop_evaluation_group",
        return_value=True,
    ) as stop:
        app._shutdown_evaluation_worker(process)

    stop.assert_called_once_with(process)

    assert app.evaluation_events.get_nowait() == (
        "shutdown_complete",
        True,
    )


def test_shutdown_completion_reenables_start():
    app = make_test_app()
    app.evaluation_running = False
    app.shutdown_pending = True

    app.evaluation_events.put(("shutdown_complete", True))
    app._drain_evaluation_events()

    assert app.shutdown_pending is False
    app.start_button.configure.assert_called_with(state="normal")
    app.root.after.assert_not_called()


def test_unverified_shutdown_disables_restart():
    app = make_test_app()
    app.shutdown_pending = True
    app.evaluation_running = False

    app.evaluation_events.put(("shutdown_complete", False))
    app._drain_evaluation_events()

    assert app.shutdown_unverified is True
    assert app.shutdown_pending is False
    app.start_button.configure.assert_called_with(state="disabled")


def test_shutdown_error_disables_restart():
    app = make_test_app()
    app.shutdown_pending = True

    app.evaluation_events.put(("shutdown_error", "Permission denied"))
    app._drain_evaluation_events()

    assert app.shutdown_unverified is True
    assert app.shutdown_pending is False
    app.start_button.configure.assert_called_with(state="disabled")


def test_unverified_shutdown_blocks_new_evaluation():
    app = make_test_app()
    app.shutdown_unverified = True

    with patch("desktop_gui.build_live_command") as builder:
        result = app.start_evaluation()

    assert result is False
    builder.assert_not_called()


def test_worker_error_preserves_unverified_shutdown():
    app = make_test_app()
    app.evaluation_running = True
    app.shutdown_unverified = True

    app.evaluation_events.put(("error", "Evaluation output could not be read"))

    app._drain_evaluation_events()

    assert app.evaluation_running is False
    assert app.shutdown_unverified is True

    app.start_button.configure.assert_called_with(state="disabled")


def test_window_close_without_active_evaluation():
    app = make_test_app()

    app.on_window_close()

    app.root.destroy.assert_called_once()


def test_window_close_requests_evaluation_stop():
    app = make_test_app()
    app.evaluation_running = True
    app.stop_evaluation = MagicMock(return_value=True)

    app.on_window_close()

    assert app.close_requested is True
    app.stop_evaluation.assert_called_once()
    app.root.destroy.assert_not_called()


def test_window_close_waits_for_shutdown_completion():
    app = make_test_app()
    app.close_requested = True
    app.evaluation_running = True
    app.shutdown_pending = True

    app._finish_window_close()
    app.root.destroy.assert_not_called()

    app.evaluation_running = False
    app._finish_window_close()
    app.root.destroy.assert_not_called()

    app.shutdown_pending = False
    app._finish_window_close()

    app.root.destroy.assert_called_once()
    assert app.close_requested is False


def test_window_close_rejects_unverified_shutdown():
    app = make_test_app()
    app.close_requested = True
    app.shutdown_unverified = True

    with patch("desktop_gui.showwarning") as warning:
        app._finish_window_close()

    app.root.destroy.assert_not_called()
    assert app.close_requested is False
    warning.assert_called_once()


def test_stop_ignored_after_worker_finishes():
    app = make_test_app()
    app.evaluation_running = True
    app.evaluation_finished = True
    app.active_evaluation_process = MagicMock()

    with patch.object(app, "_begin_evaluation_shutdown") as shutdown:
        result = app.stop_evaluation()

    assert result is False
    assert app.stop_requested is False
    shutdown.assert_not_called()


def test_pending_stop_does_not_signal_finished_worker():
    app = make_test_app()
    app.evaluation_running = True
    app.stop_requested = True
    app.evaluation_finished = True

    process = MagicMock()
    app.evaluation_events.put(("process", process))

    with patch.object(app, "_begin_evaluation_shutdown") as shutdown:
        app._drain_evaluation_events()

    shutdown.assert_not_called()
    assert app.active_evaluation_process is process


def test_close_request_blocks_new_evaluation():
    app = make_test_app()
    app.close_requested = True

    with patch("desktop_gui.build_live_command") as builder:
        result = app.start_evaluation()

    assert result is False
    builder.assert_not_called()


def test_unverified_shutdown_displays_accurate_message():
    app = make_test_app()
    app.shutdown_pending = True
    app.evaluation_running = False

    app.evaluation_events.put(("shutdown_complete", False))
    app._drain_evaluation_events()

    messages = [call.args[1] for call in app.evaluation_display.insert.call_args_list]

    assert any("Shutdown could not be verified" in text for text in messages)
    assert any("may still be running" in text for text in messages)
    assert app.shutdown_unverified is True
    app.start_button.configure.assert_called_with(state="disabled")


def test_worker_startup_failure_does_not_attempt_shutdown():
    app = make_test_app()

    with (
        patch(
            "desktop_gui.run_live_command",
            side_effect=OSError("Executable not found"),
        ),
        patch("desktop_gui.stop_evaluation_group") as stop,
    ):
        app._run_evaluation_worker(["missing-python"])

    assert app.evaluation_events.get_nowait() == (
        "error",
        "Executable not found",
    )

    assert app.evaluation_events.empty()
    stop.assert_not_called()


def test_worker_read_failure_cleans_up_started_process():
    app = make_test_app()

    process = MagicMock()

    def broken_output():
        yield "Evaluation started\n"
        raise OSError("Output stream failed")

    process.stdout = broken_output()
    process.wait.return_value = -15

    with (
        patch(
            "desktop_gui.run_live_command",
            return_value=process,
        ),
        patch(
            "desktop_gui.stop_evaluation_group",
            return_value=True,
        ) as stop,
    ):
        app._run_evaluation_worker(["python3", "trustbench.py", "live"])

    events = []

    while not app.evaluation_events.empty():
        events.append(app.evaluation_events.get_nowait())

    assert events == [
        ("process", process),
        ("output", "Evaluation started\n"),
        ("shutdown_complete", True),
        ("error", "Output stream failed"),
    ]

    stop.assert_called_once_with(process)
    process.wait.assert_called_once_with(timeout=1.0)


def test_worker_unverified_cleanup_blocks_restart_and_close():
    app = make_test_app()
    app.evaluation_running = True
    app.close_requested = True

    process = MagicMock()

    def broken_output():
        raise OSError("Output stream failed")
        yield

    process.stdout = broken_output()

    with (
        patch(
            "desktop_gui.run_live_command",
            return_value=process,
        ),
        patch(
            "desktop_gui.stop_evaluation_group",
            return_value=False,
        ) as stop,
        patch("desktop_gui.showwarning") as warning,
    ):
        app._run_evaluation_worker(["python3", "trustbench.py", "live"])
        app._drain_evaluation_events()

    stop.assert_called_once_with(process)

    assert app.evaluation_running is False
    assert app.shutdown_unverified is True
    assert app.close_requested is False

    app.start_button.configure.assert_called_with(state="disabled")
    app.root.destroy.assert_not_called()
    warning.assert_called_once()


def test_worker_cleanup_error_blocks_restart_and_close():
    app = make_test_app()
    app.evaluation_running = True
    app.close_requested = True

    process = MagicMock()

    def broken_output():
        raise OSError("Output stream failed")
        yield

    process.stdout = broken_output()

    with (
        patch(
            "desktop_gui.run_live_command",
            return_value=process,
        ),
        patch(
            "desktop_gui.stop_evaluation_group",
            side_effect=OSError("Permission denied"),
        ) as stop,
        patch("desktop_gui.showwarning") as warning,
    ):
        app._run_evaluation_worker(["python3", "trustbench.py", "live"])
        app._drain_evaluation_events()

    stop.assert_called_once_with(process)

    assert app.evaluation_running is False
    assert app.shutdown_unverified is True
    assert app.close_requested is False

    app.start_button.configure.assert_called_with(state="disabled")
    app.root.destroy.assert_not_called()
    warning.assert_called_once()


def test_shutdown_is_attempted_only_once():
    app = make_test_app()
    process = MagicMock()

    with patch(
        "desktop_gui.stop_evaluation_group",
        return_value=True,
    ) as stop:
        first = app._stop_process_once(process)
        second = app._stop_process_once(process)

    assert first is True
    assert second is True
    assert app.shutdown_attempted is True
    assert app.shutdown_verified is True

    stop.assert_called_once_with(process)

    assert app.evaluation_events.get_nowait() == (
        "shutdown_complete",
        True,
    )
    assert app.evaluation_events.empty()


def test_failed_shutdown_is_not_attempted_twice():
    app = make_test_app()
    process = MagicMock()

    with patch(
        "desktop_gui.stop_evaluation_group",
        side_effect=OSError("Permission denied"),
    ) as stop:
        first = app._stop_process_once(process)
        second = app._stop_process_once(process)

    assert first is False
    assert second is False
    assert app.shutdown_attempted is True
    assert app.shutdown_verified is False

    stop.assert_called_once_with(process)

    assert app.evaluation_events.get_nowait() == (
        "shutdown_error",
        "Permission denied",
    )
    assert app.evaluation_events.empty()


def test_concurrent_shutdown_requests_run_only_once():
    app = make_test_app()
    process = MagicMock()

    shutdown_started = Event()
    allow_shutdown_to_finish = Event()
    results = []

    def slow_shutdown(target):
        shutdown_started.set()

        if not allow_shutdown_to_finish.wait(timeout=2.0):
            raise RuntimeError("Test shutdown was not released")

        return True

    def request_shutdown():
        result = app._stop_process_once(process)
        results.append(result)

    with patch(
        "desktop_gui.stop_evaluation_group",
        side_effect=slow_shutdown,
    ) as stop:
        first_thread = Thread(target=request_shutdown)
        second_thread = Thread(target=request_shutdown)

        try:
            first_thread.start()

            assert shutdown_started.wait(timeout=2.0)

            second_thread.start()

            # Both threads now request shutdown while the
            # first shutdown operation is still unfinished.
        finally:
            allow_shutdown_to_finish.set()
            first_thread.join(timeout=3.0)

            if second_thread.ident is not None:
                second_thread.join(timeout=3.0)

    assert not first_thread.is_alive()
    assert not second_thread.is_alive()

    assert sorted(results) == [True, True]

    stop.assert_called_once_with(process)

    assert app.shutdown_attempted is True
    assert app.shutdown_verified is True

    assert app.evaluation_events.get_nowait() == (
        "shutdown_complete",
        True,
    )
    assert app.evaluation_events.empty()


def test_worker_preserves_original_error_when_wait_fails():
    app = make_test_app()
    process = MagicMock()

    def broken_output():
        raise OSError("Output stream failed")
        yield

    process.stdout = broken_output()
    process.wait.side_effect = TimeoutExpired(cmd=["python3"], timeout=1.0)

    with (
        patch("desktop_gui.run_live_command", return_value=process),
        patch("desktop_gui.stop_evaluation_group", return_value=True),
    ):
        app._run_evaluation_worker(["python3"])

    events = []

    while not app.evaluation_events.empty():
        events.append(app.evaluation_events.get_nowait())

    assert events[0] == ("process", process)
    assert events[1][0] == "shutdown_complete"
    assert events[2][0] == "shutdown_error"
    assert events[3] == ("error", "Output stream failed")
