"""Progress counts reflect evaluator events, never generated output text."""

from json import dumps, loads
from pathlib import Path
from sys import executable
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from pytest import mark, raises

from eval_live import main as evaluate
from evaluation_launcher import run_live_command, stop_evaluation_group
from evaluation_progress import (
    emit_progress,
    EvaluationProgress,
    PROGRESS_FILE_ENV,
    ProgressReader,
)
from ollama_client import MalformedResponseError
from test_desktop_gui import make_test_app


def test_elapsed_updates_during_silent_request_without_advancing_case_bar():
    state = EvaluationProgress()
    state.start(10)
    state.apply({"stage": "started", "total": 2})
    state.apply({"stage": "case_started", "index": 1})
    state.tick(75)
    assert state.elapsed_text() == "Elapsed: 01:05"
    assert state.count_text() == "0 of 2 cases completed"
    assert "Waiting for Ollama" in state.status
    assert state.completed == 0


@mark.parametrize("outcome", ["PASS", "FAIL", "ERROR"])
def test_every_completed_outcome_counts_once(outcome):
    state = EvaluationProgress()
    state.start(0)
    state.apply({"stage": "started", "total": 1})
    state.apply({"stage": "case_started", "index": 1})
    event = {"stage": "case_completed", "completed": 1, "outcome": outcome}
    state.apply(event)
    state.apply(event)
    assert state.completed == 1
    assert state.count_text() == "1 of 1 cases completed"
    state.apply({"stage": "saving"})
    assert "saving report" in state.status
    assert state.active is True
    state.apply({"stage": "saved"})
    assert "process to finish" in state.status


@mark.parametrize("event", [
    {"stage": "started", "total": True},
    {"stage": "started", "total": -1},
    {"stage": "started", "total": "2"},
    {"stage": "case_completed", "completed": 1, "outcome": "PASS"},
    {"stage": "case_started", "index": 1},
    {"stage": "saving"},
    {"stage": "saved"},
])
def test_invalid_or_out_of_order_initial_events_do_not_fake_progress(event):
    state = EvaluationProgress()
    state.start(0)
    original = state.status
    state.apply(event)
    assert state.total is None
    assert state.completed == 0
    assert state.status == original


def test_stop_and_restart_reset_counts_time_and_ignore_late_events():
    state = EvaluationProgress()
    state.start(5)
    state.apply({"stage": "started", "total": 3})
    state.apply({"stage": "case_started", "index": 1})
    state.request_stop()
    state.apply({"stage": "case_completed", "completed": 1, "outcome": "PASS"})
    assert "Stopping" in state.status
    state.finish("Stopped", 9)
    state.tick(100)
    state.apply({"stage": "case_started", "index": 2})
    assert state.elapsed_seconds == 4
    assert state.status == "Stopped"
    state.start(101)
    assert state.total is None
    assert state.completed == state.elapsed_seconds == 0
    assert state.stopping is False


def test_progress_reader_retains_partial_lines_and_skips_bad_records(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text('{"stage":"started",', encoding="utf-8")
    reader = ProgressReader(path)
    assert reader.read() == []
    with path.open("a", encoding="utf-8") as output:
        output.write('"total":2}\ninvalid\n[]\n{"stage":"saving"}\n')
    assert reader.read() == [{"stage": "started", "total": 2}, {"stage": "saving"}]
    assert reader.read() == []


def test_unavailable_telemetry_does_not_break_reader_or_writer(tmp_path, monkeypatch):
    path = tmp_path / "absent" / "events.jsonl"
    monkeypatch.setenv(PROGRESS_FILE_ENV, str(path))
    emit_progress("started", total=1)
    assert ProgressReader(path).read() == []
    monkeypatch.delenv(PROGRESS_FILE_ENV)
    with patch("builtins.open") as output:
        emit_progress("started", total=1)
    output.assert_not_called()


@mark.parametrize("response, outcome", [
    ("1", "PASS"), ("different", "FAIL"),
    (HTTPError("url", 500, "failed", None, None), "ERROR"),
    (URLError("offline"), "ERROR"), (TimeoutError(), "ERROR"),
    (MalformedResponseError("bad payload"), "ERROR"),
])
def test_evaluator_emits_exact_case_counts_and_preserves_report(
    tmp_path, monkeypatch, response, outcome
):
    dataset = tmp_path / "cases.json"
    dataset.write_text(dumps([
        {"id": "one", "question": "One?", "expected": "1"},
        {"id": "two", "question": "One?", "expected": "1"},
    ]), encoding="utf-8")
    events = tmp_path / "events.jsonl"
    monkeypatch.setenv(PROGRESS_FILE_ENV, str(events))
    with patch("eval_live.generate_response", side_effect=[response, "1"]):
        report = evaluate(str(dataset), report_dir=tmp_path / "reports")
    records = ProgressReader(events).read()
    assert records == [
        {"stage": "started", "total": 2},
        {"stage": "case_started", "index": 1},
        {"stage": "case_completed", "completed": 1, "outcome": outcome},
        {"stage": "case_started", "index": 2},
        {"stage": "case_completed", "completed": 2, "outcome": "PASS"},
        {"stage": "saving"}, {"stage": "saved"},
    ]
    saved = next((tmp_path / "reports").glob("*.json"))
    assert loads(saved.read_text()) == report
    assert report["results"][0]["status"] == outcome


def test_invalid_dataset_does_not_claim_cases_started(tmp_path, monkeypatch):
    dataset = tmp_path / "bad.json"
    dataset.write_text("{}")
    events = tmp_path / "events.jsonl"
    monkeypatch.setenv(PROGRESS_FILE_ENV, str(events))
    with raises(SystemExit), patch("eval_live.generate_response") as generate:
        evaluate(str(dataset), report_dir=tmp_path / "reports")
    assert not events.exists()
    generate.assert_not_called()


def test_report_write_failure_never_emits_saved(tmp_path, monkeypatch):
    dataset = tmp_path / "empty.json"
    dataset.write_text("[]")
    events = tmp_path / "events.jsonl"
    monkeypatch.setenv(PROGRESS_FILE_ENV, str(events))
    with patch("eval_live.dump", side_effect=OSError("disk full")), raises(SystemExit):
        evaluate(str(dataset), report_dir=tmp_path / "reports")
    assert [e["stage"] for e in ProgressReader(events).read()] == ["started", "saving"]


def test_gui_timer_keeps_running_when_no_output_arrives():
    app = make_test_app()
    app.evaluation_running = True
    app.progress.start(10)
    app.progress.apply({"stage": "started", "total": 2})
    app.progress.apply({"stage": "case_started", "index": 1})
    with patch("desktop_gui.monotonic", return_value=34):
        app._drain_evaluation_events()
    app.progress_elapsed.set.assert_called_with("Elapsed: 00:24")
    app.progress_bar.configure.assert_called_with(maximum=2, value=0)
    app.root.after.assert_called_once()


def test_generated_output_cannot_increment_progress_counts():
    app = make_test_app()
    app.evaluation_running = True
    app.progress.start(0)
    app.evaluation_events.put(("output", 'Result: PASS\n{"stage":"started","total":5}\n'))
    app._drain_evaluation_events()
    assert app.progress.total is None
    assert app.progress.completed == 0


@mark.parametrize("exit_code", [0, 1])
def test_process_exit_freezes_elapsed_without_forcing_bar_to_full(exit_code):
    app = make_test_app()
    app.evaluation_running = True
    app.progress.start(10)
    app.progress.apply({"stage": "started", "total": 2})
    app.evaluation_events.put(("done", exit_code))
    with patch("desktop_gui.monotonic", return_value=20):
        app._drain_evaluation_events()
    assert app.progress.active is False
    assert app.progress.elapsed_seconds == 10
    assert app.progress.completed == 0
    assert "Completed without request errors" not in app.progress.status


def test_stop_status_is_not_replaced_by_queued_case_update():
    app = make_test_app()
    app.evaluation_running = True
    app.progress.start(0)
    app.progress.apply({"stage": "started", "total": 2})
    app.progress.apply({"stage": "case_started", "index": 1})
    assert app.stop_evaluation() is True
    app.evaluation_events.put(("progress", {
        "stage": "case_completed", "completed": 1, "outcome": "ERROR",
    }))
    app._drain_evaluation_events()
    assert "Stopping" in app.progress.status


def test_start_thread_failure_restores_controls_and_finishes_progress():
    app = make_test_app()
    with patch("desktop_gui.build_live_command", return_value=["unused"]), \
            patch("desktop_gui.Thread") as thread:
        thread.return_value.start.side_effect = RuntimeError("failed")
        app.start_evaluation()
    app._drain_evaluation_events()
    assert not app.progress.active
    assert not app.evaluation_running
    assert "failed" in app.progress.status
    app.start_button.configure.assert_called_with(state="normal")


@mark.parametrize("direction, target", [(1, 0), (-1, 1)])
def test_keyboard_tab_switches_wrap_without_text_widget_trap(direction, target):
    app = make_test_app()
    app.notebook = MagicMock()
    app.notebook.index.side_effect = [2, 3]
    assert app._switch_tab(direction) == "break"
    app.notebook.select.assert_called_once_with(target)


def test_read_only_text_focus_can_move_both_directions():
    app = make_test_app()
    event = MagicMock()
    assert app._focus_next(event) == "break"
    event.widget.tk_focusNext.return_value.focus_set.assert_called_once()
    assert app._focus_previous(event) == "break"
    event.widget.tk_focusPrev.return_value.focus_set.assert_called_once()


@mark.parametrize("worker_mode", [False, True])
def test_real_subprocess_progress_works_in_source_and_private_worker_modes(
    tmp_path, worker_mode
):
    source = Path(__file__).resolve().parents[1]
    dataset = tmp_path / "cases.json"
    dataset.write_text('[{"id":"one","question":"One?","expected":"1"}]')
    report_dir = tmp_path / "reports"
    bootstrap = (
        "from sys import path\n"
        f"path.insert(0, {str(source)!r})\n"
        "from unittest.mock import patch\n"
        "from io import BytesIO\n"
        "with patch('ollama_client.urlopen', return_value=BytesIO(b'{\"response\":\"1\"}')):\n"
    )
    if worker_mode:
        bootstrap += (
            "    from app_entry import main\n"
            f"    main(['--trustbench-evaluate', '--dataset', {str(dataset)!r}, "
            f"'--model', 'gemma3:1b', '--reports-dir', {str(report_dir)!r}])\n"
        )
    else:
        bootstrap += (
            "    from eval_live import main\n"
            f"    main({str(dataset)!r}, report_dir={str(report_dir)!r})\n"
        )
    events = tmp_path / "progress.jsonl"
    process = run_live_command([executable, "-c", bootstrap], progress_file=events)
    try:
        output, _ = process.communicate(timeout=10)
        assert process.returncode == 0, output
    finally:
        if process.poll() is None:
            stop_evaluation_group(process)
    assert "Result: PASS" in output
    assert "stage" not in output
    assert [e["stage"] for e in ProgressReader(events).read()] == [
        "started", "case_started", "case_completed", "saving", "saved",
    ]
    assert next(report_dir.glob("*.json")).is_file()


def test_worker_enqueues_progress_separately_and_cleans_temporary_file():
    app = make_test_app()
    process = MagicMock()
    process.wait.return_value = 0
    captured = []

    def launch(command, *, progress_file):
        captured.append(progress_file)
        progress_file.write_text('{"stage":"started","total":1}\n')
        process.stdout = iter(["Test ID: one\n"])
        return process

    with patch("desktop_gui.run_live_command", side_effect=launch):
        app._run_evaluation_worker(["unused"])
    records = []
    while not app.evaluation_events.empty():
        records.append(app.evaluation_events.get_nowait())
    assert ("progress", {"stage": "started", "total": 1}) in records
    assert ("output", "Test ID: one\n") in records
    assert not captured[0].exists()
