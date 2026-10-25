"""Resources, persistent data and evaluator dispatch before building a Mac app."""

from io import BytesIO
from json import dumps, loads
from pathlib import Path
from queue import Queue
from subprocess import run
from sys import executable
from threading import Thread
from time import monotonic
from unittest.mock import patch

from pytest import fixture, mark, raises

from app_entry import main as app_main, run_evaluation_worker, WORKER_FLAG
from eval_live import main as evaluate
from evaluation_launcher import (
    build_live_command,
    run_live_command,
    stop_evaluation_group,
)
from runtime_paths import (
    is_packaged,
    reports_directory,
    resource_directory,
    user_data_directory,
)


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def write_dataset(path):
    path.write_text(
        dumps([{"id": "one", "question": "What is one?", "expected": "1"}]),
        encoding="utf-8",
    )
    return path


@fixture
def packaged_environment(tmp_path, monkeypatch):
    bundle = tmp_path / "TrustBench bundle"
    bundle.mkdir()
    user = tmp_path / "User With Spaces"
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("runtime_paths.platform", "darwin")
    monkeypatch.setattr("runtime_paths.Path.home", lambda: user)
    monkeypatch.setattr("runtime_paths.__file__", str(bundle / "runtime_paths.py"))
    monkeypatch.setattr("evaluation_launcher.PROJECT_ROOT", bundle)
    return bundle, user


@mark.parametrize("marker", [False, True])
def test_packaged_marker_is_read_dynamically(monkeypatch, marker):
    monkeypatch.setattr("sys.frozen", marker, raising=False)
    assert is_packaged() is marker


def test_source_without_frozen_marker_uses_existing_gui_report_location(
    tmp_path, monkeypatch
):
    monkeypatch.delattr("sys.frozen", raising=False)
    monkeypatch.chdir(tmp_path)
    assert is_packaged() is False
    assert resource_directory() == SOURCE_ROOT
    assert reports_directory() == SOURCE_ROOT / "reports"
    assert not (tmp_path / "reports").exists()


def test_packaged_reports_survive_resource_location_changes(
    tmp_path, monkeypatch, packaged_environment
):
    bundle, user = packaged_environment
    expected = user / "Library" / "Application Support" / "TrustBench" / "reports"
    assert reports_directory() == expected
    # Merely resolving paths or previewing settings must not create data.
    assert not expected.parent.exists()
    expected.mkdir(parents=True)
    old_report = expected / "evaluation-existing.json"
    old_report.write_text('{"existing":true}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "runtime_paths.__file__", str(tmp_path / "Updated App" / "runtime_paths.py")
    )
    assert reports_directory() == expected
    assert old_report.read_text(encoding="utf-8") == '{"existing":true}'
    assert not (bundle / "reports").exists()


def test_unimplemented_packaged_platform_is_explicit(monkeypatch):
    monkeypatch.setattr("runtime_paths.platform", "win32")
    with raises(ValueError, match="currently require macOS"):
        user_data_directory()


def test_packaged_command_uses_app_worker_and_writable_reports(packaged_environment):
    bundle, user = packaged_environment
    dataset = write_dataset(bundle / "example with spaces.json")
    app = "/Applications/TrustBench.app/Contents/MacOS/TrustBench"
    with patch("evaluation_launcher.executable", app):
        command = build_live_command(dataset.name, "  gemma3:1b  ")
    assert command == [
        app, WORKER_FLAG, "--dataset", str(dataset), "--model", "gemma3:1b",
        "--reports-dir", str(reports_directory()),
    ]
    assert not (user / "Library").exists()
    assert not (bundle / "reports").exists()


def test_packaged_launch_creates_only_user_working_directory(packaged_environment):
    bundle, user = packaged_environment
    with patch("evaluation_launcher.Popen") as popen:
        run_live_command(["TrustBench", WORKER_FLAG])
    settings = popen.call_args.kwargs
    assert settings["cwd"] == user_data_directory()
    assert settings["cwd"].is_dir()
    assert settings["env"]["PYTHONUNBUFFERED"] == "1"
    assert settings["start_new_session"] is True
    assert not (bundle / "reports").exists()


def test_packaged_launch_storage_error_is_propagated(packaged_environment):
    bundle, user = packaged_environment
    data = user_data_directory()
    data.parent.mkdir(parents=True)
    data.write_text("not a directory", encoding="utf-8")
    with patch("evaluation_launcher.Popen") as popen, raises(OSError):
        run_live_command(["TrustBench", WORKER_FLAG])
    popen.assert_not_called()
    assert not (bundle / "reports").exists()


def test_source_live_reports_can_be_redirected_without_changing_cwd(
    tmp_path, monkeypatch
):
    workspace = tmp_path / "outside checkout"
    workspace.mkdir()
    dataset = write_dataset(workspace / "cases.json")
    original = dataset.read_bytes()
    reports = tmp_path / "persistent reports"
    monkeypatch.chdir(workspace)
    with patch("eval_live.generate_response", return_value="1"):
        report = evaluate(str(dataset), report_dir=reports)
    saved = list(reports.glob("evaluation-*.json"))
    assert len(saved) == 1
    assert loads(saved[0].read_text(encoding="utf-8")) == report
    assert Path.cwd() == workspace
    assert not (workspace / "reports").exists()
    assert dataset.read_bytes() == original


def test_worker_creates_report_in_explicit_directory_without_gui(tmp_path):
    dataset = write_dataset(tmp_path / "cases.json")
    reports = tmp_path / "output"
    with (
        patch("ollama_client.urlopen", return_value=BytesIO(b'{"response":"1"}')),
        patch("desktop_gui.main") as gui,
    ):
        result = run_evaluation_worker([
            "--dataset", str(dataset), "--model", "gemma3:1b",
            "--reports-dir", str(reports),
        ])
    assert result == 0
    gui.assert_not_called()
    saved = list(reports.glob("evaluation-*.json"))
    assert len(saved) == 1
    report = loads(saved[0].read_text(encoding="utf-8"))
    assert report["summary"]["passed"] == 1
    assert report["metadata"]["dataset"] == str(dataset)


def test_worker_save_error_returns_failure_without_opening_gui(tmp_path):
    dataset = write_dataset(tmp_path / "cases.json")
    reports = tmp_path / "output"
    reports.write_text("not a directory", encoding="utf-8")
    with (
        patch("ollama_client.urlopen", return_value=BytesIO(b'{"response":"1"}')),
        patch("desktop_gui.main") as gui,
        raises(SystemExit) as error,
    ):
        run_evaluation_worker([
            "--dataset", str(dataset), "--model", "gemma3:1b",
            "--reports-dir", str(reports),
        ])
    assert error.value.code == 1
    assert reports.read_text(encoding="utf-8") == "not a directory"
    gui.assert_not_called()


def test_app_entry_still_opens_desktop_without_worker_arguments():
    with patch("desktop_gui.main") as gui:
        assert app_main([]) == 0
    gui.assert_called_once_with()


def test_worker_unexpected_exception_is_visible_and_nonzero(capfd):
    with (
        patch(
            "app_entry.run_evaluation_worker", side_effect=RuntimeError("worker failed")
        ),
        patch("desktop_gui.main") as gui,
    ):
        assert app_main([WORKER_FLAG]) == 1
    assert "RuntimeError: worker failed" in capfd.readouterr().err
    gui.assert_not_called()


@mark.parametrize("arguments", [["--unknown"], [WORKER_FLAG]])
def test_invalid_entry_arguments_never_launch_gui(arguments):
    with patch("desktop_gui.main") as gui, raises(SystemExit) as error:
        app_main(arguments)
    assert error.value.code == 2
    gui.assert_not_called()


def test_source_cli_accepts_explicit_dataset_outside_checkout(tmp_path):
    dataset = tmp_path / "offline.json"
    dataset.write_text(dumps([{
        "id": "one", "question": "What is one?", "expected": "1", "response": "1"
    }]), encoding="utf-8")
    completed = run(
        [executable, str(SOURCE_ROOT / "trustbench.py"), "offline",
         "--dataset", str(dataset)],
        cwd=tmp_path, capture_output=True, text=True, timeout=5,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Passed 1 test" in completed.stdout


def test_gui_uses_bundle_resources_and_user_reports_at_frozen_startup(
    tmp_path, packaged_environment
):
    bundle, user = packaged_environment
    dataset = write_dataset(bundle / "eval-read-live.json")
    reports = reports_directory()
    reports.mkdir(parents=True)
    legacy = reports / "evaluation-legacy.json"
    original = dumps({
        "metadata": {
            "model": "gemma3:1b", "dataset": "cases.json",
            "timestamp": "2026-10-25T21:00:00+00:00",
        },
        "results": [],
    })
    legacy.write_text(original, encoding="utf-8")
    script = (
        "from json import dumps\n"
        "from pathlib import Path\n"
        "from sys import modules, path\n"
        "from unittest.mock import patch\n"
        f"path.insert(0, {str(SOURCE_ROOT)!r})\n"
        "modules['sys'].frozen = True\n"
        "with (\n"
        "    patch('runtime_paths.platform', 'darwin'),\n"
        f"    patch('runtime_paths.__file__', {str(bundle / 'runtime_paths.py')!r}),\n"
        f"    patch('runtime_paths.Path.home', return_value=Path({str(user)!r})),\n"
        "    patch('ollama_client.urlopen',\n"
        "          side_effect=AssertionError('offline only')),\n"
        "):\n"
        "    from desktop_gui import PROJECT_ROOT, REPORTS_DIRECTORY\n"
        "    from generate_report import generate_text_report\n"
        "    from report_browser import list_saved_reports\n"
        "    print(dumps({\n"
        "        'resources': str(PROJECT_ROOT),\n"
        "        'reports': str(REPORTS_DIRECTORY),\n"
        "        'saved': list_saved_reports(str(REPORTS_DIRECTORY)),\n"
        f"        'view': generate_text_report({str(legacy)!r}),\n"
        "    }))\n"
    )
    completed = run(
        [executable, "-c", script], cwd=tmp_path,
        capture_output=True, text=True, timeout=5,
    )
    assert completed.returncode == 0, completed.stderr
    settings = loads(completed.stdout)
    assert settings["resources"] == str(bundle)
    assert (Path(settings["resources"]) / dataset.name).is_file()
    assert settings["reports"] == str(reports)
    assert settings["saved"] == [str(legacy)]
    assert "Total cases: 0" in settings["view"]
    assert legacy.read_text(encoding="utf-8") == original
    assert not (bundle / "reports").exists()


def test_real_worker_streams_stops_and_restarts_without_gui_or_bundle_writes(
    tmp_path, packaged_environment
):
    bundle, user = packaged_environment
    dataset = write_dataset(bundle / "eval-read-live.json")
    reports = reports_directory()
    blocker = tmp_path / "block request"
    blocker.touch()
    # This runs the actual entry/worker/evaluator with mocked HTTP in a child.
    # Missing Python stream objects simulate a windowed executable. Tkinter is
    # deliberately unavailable, so accidentally opening the GUI fails the test.
    bootstrap = (
        "from io import BytesIO\n"
        "from pathlib import Path\n"
        "from sys import argv, exit, modules, path\n"
        "from time import monotonic, sleep\n"
        "from unittest.mock import patch\n"
        f"path.insert(0, {str(SOURCE_ROOT)!r})\n"
        "modules['tkinter'] = None\n"
        "def response(*args, **kwargs):\n"
        "    deadline = monotonic() + 15\n"
        f"    while Path({str(blocker)!r}).exists() and monotonic() < deadline:\n"
        "        sleep(0.01)\n"
        "    return BytesIO(b'{\"response\":\"1\"}')\n"
        "from app_entry import main\n"
        "modules['sys'].stdout = None\n"
        "modules['sys'].stderr = None\n"
        "with patch('ollama_client.urlopen', side_effect=response):\n"
        "    exit(main(argv[1:]))\n"
    )
    worker_args = build_live_command(str(dataset), "gemma3:1b")[1:]
    assert worker_args[0] == WORKER_FLAG
    command = [executable, "-c", bootstrap, *worker_args]
    process = run_live_command(command)
    output_lines = Queue()

    def read_output():
        for line in process.stdout:
            output_lines.put(line)
        output_lines.put("")

    reader = Thread(target=read_output, daemon=True)
    reader.start()
    try:
        lines = []
        deadline = monotonic() + 5
        while monotonic() < deadline:
            line = output_lines.get(timeout=max(0.01, deadline - monotonic()))
            lines.append(line)
            if line.startswith("Test ID:") or not line:
                break
        assert any(line.startswith("Test ID:") for line in lines), "".join(lines)
        assert process.poll() is None
        assert stop_evaluation_group(process) is True
        assert process.wait(timeout=3) in {-15, -9}
        assert not list(reports.glob("evaluation-*.json"))
    finally:
        blocker.unlink(missing_ok=True)
        if process.poll() is None:
            stop_evaluation_group(process)
            process.wait(timeout=3)
        reader.join(timeout=3)
        process.stdout.close()

    restarted = run_live_command(command)
    try:
        output, _ = restarted.communicate(timeout=5)
        assert restarted.returncode == 0, output
        assert "Report saved to: " in output
        saved = list(reports.glob("evaluation-*.json"))
        assert len(saved) == 1
        report = loads(saved[0].read_text(encoding="utf-8"))
        assert report["summary"] == {
            "passed": 1, "failed": 0, "errors": 0, "accuracy": 100.0,
        }
        assert not (bundle / "reports").exists()
        assert not (user_data_directory() / "eval-read-live.json").exists()
    finally:
        if restarted.poll() is None:
            stop_evaluation_group(restarted)
            restarted.wait(timeout=3)
        restarted.stdout.close()
