"""Build orchestration is testable without claiming a native macOS artifact."""

from io import StringIO
from json import loads
from pathlib import Path
from plistlib import dump as dump_plist
from shutil import copytree
from subprocess import CalledProcessError, CompletedProcess
from types import ModuleType
from unittest.mock import MagicMock, patch

from pytest import fixture, mark, raises

from app_identity import BUILD_NUMBER
from build_macos import (
    APP_VERSION,
    BUNDLE_ID,
    DATA_FILES,
    PYINSTALLER_VERSION,
    _verify_bundle,
    _worker_smoke_test,
    build_candidate,
    build_plan,
    check_build_environment,
    main,
)

SOURCE = Path(__file__).resolve().parents[1]


@fixture
def build_root(tmp_path, monkeypatch):
    root = tmp_path / "checkout with spaces"
    root.mkdir()
    for name in DATA_FILES:
        (root / name).write_bytes((SOURCE / name).read_bytes())
    (root / "macos").mkdir()
    (root / "macos" / "INSTALL.txt").write_text("Development candidate")
    (root / "macos" / "TrustBench.icns").write_bytes(
        (SOURCE / "macos" / "TrustBench.icns").read_bytes()
    )
    monkeypatch.setattr("build_macos.ROOT", root)
    return root


def test_plan_is_dependency_free_and_does_not_write_output(build_root, capsys):
    with patch("build_macos.check_build_environment") as check:
        assert main(["--plan"]) == 0
    check.assert_not_called()
    plan = loads(capsys.readouterr().out)
    assert plan["architecture"] == "x86_64"
    assert plan["publishes"] is plan["installs"] is False
    assert not (build_root / "dist").exists()


@mark.parametrize(
    "system, arch, python, message",
    [
        ("linux", "x86_64", "3.12.12", "require macOS"),
        ("darwin", "arm64", "3.12.12", "Intel"),
        ("darwin", "x86_64", "3.13.0", "3.12.12"),
    ],
)
def test_wrong_build_host_is_rejected_before_writes(
    system, arch, python, message, build_root
):
    with (
        patch("build_macos.platform", system),
        patch("build_macos.machine", return_value=arch),
        patch("build_macos.python_version", return_value=python),
    ):
        with raises(RuntimeError, match=message):
            check_build_environment()
    assert not (build_root / "dist").exists()


def test_packager_version_is_checked_before_tk_or_build(build_root):
    with (
        patch("build_macos.platform", "darwin"),
        patch("build_macos.machine", return_value="x86_64"),
        patch("build_macos.python_version", return_value="3.12.12"),
        patch("build_macos.version", return_value="unexpected"),
        patch("tkinter.Tk") as window,
    ):
        with raises(RuntimeError, match="PyInstaller"):
            check_build_environment()
    window.assert_not_called()


def test_mac_preflight_checks_and_closes_the_build_interpreters_tk(build_root):
    with (
        patch("build_macos.platform", "darwin"),
        patch("build_macos.machine", return_value="x86_64"),
        patch("build_macos.python_version", return_value="3.12.12"),
        patch("build_macos.version", return_value=PYINSTALLER_VERSION),
        patch("build_macos.mac_ver", return_value=("15.7.9", (), "x86_64")),
        patch("build_macos.Path.is_file", return_value=True),
        patch("tkinter.Tk") as window,
    ):
        window.return_value.tk.call.side_effect = ["8.6.17", "8.6.17"]
        result = check_build_environment()
    assert result["tk"] == "8.6.17"
    assert result["macos"] == "15.7.9"
    window.return_value.withdraw.assert_called_once()
    window.return_value.destroy.assert_called_once()


def test_missing_native_tool_fails_preflight_before_tk(build_root):
    with (
        patch("build_macos.platform", "darwin"),
        patch("build_macos.machine", return_value="x86_64"),
        patch("build_macos.python_version", return_value="3.12.12"),
        patch("build_macos.version", return_value=PYINSTALLER_VERSION),
        patch("build_macos.MAC_TOOLS", (str(build_root / "missing-hdiutil"),)),
        patch("tkinter.Tk") as window,
    ):
        with raises(RuntimeError, match="tool"):
            check_build_environment()
    window.assert_not_called()


def test_check_cli_returns_clear_failure_without_building():
    errors = StringIO()
    with (
        patch(
            "build_macos.check_build_environment", side_effect=RuntimeError("No Mac")
        ),
        patch("build_macos.stderr", errors),
    ):
        assert main(["--check"]) == 1
    assert "No Mac" in errors.getvalue()


def test_spec_executes_as_onedir_windowed_intel_with_explicit_data_only():
    analysis = MagicMock()
    calls = {
        name: MagicMock() for name in ("Analysis", "PYZ", "EXE", "COLLECT", "BUNDLE")
    }
    calls["Analysis"].return_value = analysis
    exec(
        compile(
            (SOURCE / "macos" / "TrustBench.spec").read_text(),
            "TrustBench.spec",
            "exec",
        ),
        calls,
    )
    settings = calls["EXE"].call_args.kwargs
    assert settings["target_arch"] == "x86_64"
    assert settings["console"] is False
    assert settings["argv_emulation"] is False
    assert settings["exclude_binaries"] is True
    assert settings["bootloader_ignore_signals"] is False
    data = calls["Analysis"].call_args.kwargs["datas"]
    assert {Path(source).name for source, destination in data} == set(DATA_FILES)
    assert all(destination == "." for source, destination in data)
    assert not any(
        "reports/" in source or ".venv" in source for source, destination in data
    )
    assert calls["BUNDLE"].call_args.kwargs["bundle_identifier"] == BUNDLE_ID


def make_bundle(root):
    app = root / "TrustBench.app"
    resources = app / "Contents" / "Resources"
    resources.mkdir(parents=True)
    binary = app / "Contents" / "MacOS" / "TrustBench"
    binary.parent.mkdir()
    binary.write_bytes(b"fake executable")
    with (app / "Contents" / "Info.plist").open("wb") as output:
        dump_plist(
            {
                "CFBundleIdentifier": BUNDLE_ID,
                "CFBundleShortVersionString": APP_VERSION,
                "CFBundleVersion": BUILD_NUMBER,
                "CFBundleIconFile": "TrustBench.icns",
            },
            output,
        )
    (resources / "TrustBench.icns").write_bytes(
        (root / "macos" / "TrustBench.icns").read_bytes()
    )
    for name in DATA_FILES:
        (resources / name).write_bytes((root / name).read_bytes())
    for name in ("_tkinter.so", "init.tcl", "tk.tcl", "libpython3.12.dylib"):
        (resources / name).touch()
    return app


def verification_run(command, **kwargs):
    if command[0].endswith("file"):
        return CompletedProcess(
            command, 0, stdout="Mach-O 64-bit executable x86_64", stderr=""
        )
    return CompletedProcess(command, 0, stdout="", stderr="Signature=adhoc\n")


def test_bundle_verification_checks_resources_runtime_architecture_and_signature(
    build_root,
):
    app = make_bundle(build_root)
    with patch("build_macos.run", side_effect=verification_run) as command:
        result = _verify_bundle(app)
    assert result == {
        "architecture": "x86_64",
        "signature": "ad-hoc verified",
        "notarized": False,
    }
    assert any(
        "--deep" in call.args[0] and "--strict" in call.args[0]
        for call in command.call_args_list
    )


@mark.parametrize(
    "missing",
    [
        "_tkinter.so",
        "init.tcl",
        "tk.tcl",
        "libpython3.12.dylib",
        "eval-read-live.json",
        "TrustBench.icns",
    ],
)
def test_missing_bundle_component_blocks_candidate(build_root, missing):
    app = make_bundle(build_root)
    (app / "Contents" / "Resources" / missing).unlink()
    with raises(RuntimeError):
        _verify_bundle(app)


def test_changed_dataset_is_not_accepted_as_bundled_resource(build_root):
    app = make_bundle(build_root)
    (app / "Contents" / "Resources" / DATA_FILES[0]).write_text("[]")
    with raises(RuntimeError, match="changed"):
        _verify_bundle(app)


def test_codesign_failure_is_not_reported_as_verified(build_root):
    app = make_bundle(build_root)

    def command(args, **kwargs):
        if "--verify" in args:
            raise CalledProcessError(1, args)
        return verification_run(args, **kwargs)

    with patch("build_macos.run", side_effect=command), raises(CalledProcessError):
        _verify_bundle(app)


def test_frozen_smoke_command_uses_private_worker_and_temporary_data(build_root):
    seen = []

    def worker(command, **kwargs):
        reports = Path(command[command.index("--reports-dir") + 1])
        dataset = Path(command[command.index("--dataset") + 1])
        assert loads(dataset.read_text()) == []
        assert kwargs["cwd"] == dataset.parent
        assert kwargs["timeout"] == 30
        assert "--trustbench-evaluate" in command
        reports.mkdir()
        (reports / "evaluation-smoke.json").write_text(
            '{"results":[],"summary":{"errors":0}}'
        )
        seen.append(dataset.parent)
        return CompletedProcess(
            command, 0, stdout="Report saved to: temporary.json", stderr=""
        )

    with patch("build_macos.run", side_effect=worker):
        assert _worker_smoke_test(build_root / "TrustBench.app")["ollama_requests"] == 0
    assert not seen[0].exists()


def test_smoke_failure_stops_dmg_stage(build_root):
    fake_api = ModuleType("PyInstaller.__main__")
    fake_api.run = MagicMock()
    with (
        patch.dict(
            "sys.modules",
            {
                "PyInstaller": ModuleType("PyInstaller"),
                "PyInstaller.__main__": fake_api,
            },
        ),
        patch("build_macos.check_build_environment", return_value={}),
        patch("build_macos._verify_bundle", return_value={}),
        patch(
            "build_macos._worker_smoke_test", side_effect=RuntimeError("worker failed")
        ),
        patch("build_macos.run") as command,
    ):
        with raises(RuntimeError, match="worker failed"):
            build_candidate()
    command.assert_not_called()


def test_failed_package_audit_stops_worker_and_dmg_creation(build_root):
    fake_api = ModuleType("PyInstaller.__main__")
    fake_api.run = MagicMock()
    with (
        patch.dict(
            "sys.modules",
            {
                "PyInstaller": ModuleType("PyInstaller"),
                "PyInstaller.__main__": fake_api,
            },
        ),
        patch("build_macos.check_build_environment", return_value={}),
        patch("build_macos._verify_bundle", return_value={}),
        patch(
            "build_macos._audit_bundle", side_effect=RuntimeError("external dependency")
        ),
        patch("build_macos._worker_smoke_test") as smoke,
        patch("build_macos.run") as command,
    ):
        with raises(RuntimeError, match="external dependency"):
            build_candidate()
    smoke.assert_not_called()
    command.assert_not_called()


def test_candidate_staging_checksum_and_record_never_publish_or_overwrite(build_root):
    fake_api = ModuleType("PyInstaller.__main__")

    def freeze(arguments):
        output = Path(arguments[arguments.index("--distpath") + 1])
        app = output / "TrustBench.app"
        app.mkdir()
        (app / "resource").write_text("preserved")
        (app / "link").symlink_to("resource")

    fake_api.run = MagicMock(side_effect=freeze)
    commands = []

    def command(args, **kwargs):
        commands.append(args)
        if args[0].endswith("ditto"):
            copytree(args[1], args[2], symlinks=True)
        if "create" in args:
            Path(args[-1]).write_bytes(b"fake dmg")
        return CompletedProcess(args, 0)

    with (
        patch.dict(
            "sys.modules",
            {
                "PyInstaller": ModuleType("PyInstaller"),
                "PyInstaller.__main__": fake_api,
            },
        ),
        patch(
            "build_macos.check_build_environment", return_value={"python": "3.12.12"}
        ),
        patch(
            "build_macos._verify_bundle", return_value={"signature": "ad-hoc verified"}
        ),
        patch(
            "build_macos._worker_smoke_test", return_value={"frozen_worker": "passed"}
        ),
        patch(
            "build_macos._source_evidence",
            return_value={"commit": "test", "dirty": False},
        ),
        patch("build_macos.distributions", return_value=[]),
        patch("build_macos.run", side_effect=command),
    ):
        first = build_candidate()
        second = build_candidate()
    assert first != second and first.is_dir() and second.is_dir()
    record = loads((first / "build-record.json").read_text())
    assert record["published"] is record["installed_app_validated"] is False
    assert record["app_version"] == APP_VERSION
    audit = loads((first / "bundle-audit.json").read_text())
    assert audit["files"][0]["path"] == "resource"
    assert record["bundle_audit"]["files"] == 1
    assert record["dmg"]["sha256"] in (first / "SHA256SUMS.txt").read_text()
    create = next(args for args in commands if "create" in args)
    stage = Path(create[create.index("-srcfolder") + 1])
    assert (stage / "Applications").readlink() == Path("/Applications")
    assert (stage / "TrustBench.app" / "link").is_symlink()
    assert not any("install" in args or "publish" in args for args in commands)
    assert fake_api.run.call_args.args[0][-1].endswith("TrustBench.spec")


def test_build_requirement_is_separate_and_pinned():
    assert (
        f"PyInstaller=={PYINSTALLER_VERSION}"
        in (SOURCE / "requirements-build-macos.txt").read_text()
    )
    assert build_plan()["bundled_datasets"] == list(DATA_FILES)
