"""Regressions for preview identity, package audit and custom icon wiring."""

from pathlib import Path
from plistlib import dumps as plist_dumps
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

from pytest import mark, raises

from app_identity import APP_VERSION, BUILD_NUMBER, BUNDLE_ID, PREVIEW_LABEL
from build_macos import _audit_bundle, _verify_bundle, build_plan
from desktop_gui import TrustBenchDesktop

ROOT = Path(__file__).resolve().parents[1]


def test_identity_is_shared_by_build_plan_and_app_help():
    plan = build_plan()
    assert plan["version"] == APP_VERSION
    assert plan["build_number"] == BUILD_NUMBER
    assert "preview" in plan["label"]
    app = object.__new__(TrustBenchDesktop)
    app._dialog = MagicMock()
    app.show_keyboard_help()
    assert PREVIEW_LABEL in app._dialog.call_args.args[2]


def test_icns_container_has_multiple_png_representations_and_is_wired_into_spec():
    icon = (ROOT / "macos" / "TrustBench.icns").read_bytes()
    assert icon[:4] == b"icns" and int.from_bytes(icon[4:8], "big") == len(icon)
    offset = 8
    types = set()
    while offset < len(icon):
        kind, length = (
            icon[offset : offset + 4],
            int.from_bytes(icon[offset + 4 : offset + 8], "big"),
        )
        assert length > 8 and offset + length <= len(icon)
        types.add(kind)
        offset += length
    assert offset == len(icon)
    assert {b"ic07", b"ic08", b"ic09", b"ic10"} <= types
    calls = {
        name: MagicMock() for name in ("Analysis", "PYZ", "EXE", "COLLECT", "BUNDLE")
    }
    exec(
        compile(
            (ROOT / "macos" / "TrustBench.spec").read_text(), "TrustBench.spec", "exec"
        ),
        calls,
    )
    assert calls["BUNDLE"].call_args.kwargs["icon"] == str(
        ROOT / "macos" / "TrustBench.icns"
    )


@mark.parametrize(
    "name",
    [
        "reports/private.json",
        ".git/config",
        ".venv/bin/python",
        ".venv-macos-build/secret",
        "tests/test_user.py",
        ".env",
        ".env.local",
    ],
)
def test_audit_rejects_unintended_user_and_development_files(tmp_path, name):
    app = tmp_path / "TrustBench.app"
    file = app / "Contents" / "Resources" / name
    file.parent.mkdir(parents=True)
    file.write_text("private")
    with raises(RuntimeError, match="Unexpected development/user file"):
        _audit_bundle(app)


@mark.parametrize("external_exists", [False, True])
def test_audit_rejects_broken_or_external_symlinks(tmp_path, external_exists):
    app = tmp_path / "TrustBench.app"
    app.mkdir()
    target = tmp_path / "external"
    if external_exists:
        target.write_text("outside")
    (app / "link").symlink_to(target)
    with raises(RuntimeError, match="symlink"):
        _audit_bundle(app)


def test_audit_inventories_internal_links_and_hashes_without_writing(tmp_path):
    app = tmp_path / "TrustBench.app"
    app.mkdir()
    (app / "data").write_text("hello")
    (app / "link").symlink_to("data")
    audit = _audit_bundle(app)
    assert audit["files"][0]["bytes"] == 5
    assert len(audit["files"][0]["sha256"]) == 64
    assert audit["symlinks"] == [{"path": "link", "target": "data"}]
    assert audit["native_dependencies"] == {}
    assert {p.name for p in app.iterdir()} == {"data", "link"}


def test_audit_rejects_absolute_internal_link_that_breaks_when_app_is_moved(tmp_path):
    app = tmp_path / "TrustBench.app"
    app.mkdir()
    (app / "data").write_text("hello")
    (app / "link").symlink_to(app / "data")
    with raises(RuntimeError, match="symlink"):
        _audit_bundle(app)


@mark.parametrize(
    "dependency",
    [
        "/Users/developer/custom/lib.dylib",
        "/opt/homebrew/lib/libtcl.dylib",
        "/Library/Frameworks/Python.framework/Python",
    ],
)
def test_audit_rejects_absolute_non_system_native_dependencies(tmp_path, dependency):
    app = tmp_path / "TrustBench.app"
    app.mkdir()
    binary = app / "TrustBench"
    binary.write_bytes(b"\xcf\xfa\xed\xfe" + b"mock MachO")
    result = CompletedProcess(
        [], 0, stdout=f"{binary}:\n\t{dependency} (compatibility version 1.0.0)\n"
    )
    with (
        patch("build_macos.run", return_value=result),
        raises(RuntimeError, match="External native dependency"),
    ):
        _audit_bundle(app)


def test_audit_accepts_bundled_and_system_dependencies(tmp_path):
    app = tmp_path / "TrustBench.app"
    app.mkdir()
    binary = app / "TrustBench"
    binary.write_bytes(b"\xcf\xfa\xed\xfe")
    dependencies = [
        "@rpath/Python.framework/Python",
        "@loader_path/libtcl.dylib",
        "/usr/lib/libSystem.B.dylib",
        "/System/Library/Frameworks/AppKit.framework/AppKit",
    ]
    result = CompletedProcess(
        [],
        0,
        stdout=f"{binary}:\n"
        + "".join(f"\t{d} (compatibility version 1.0.0)\n" for d in dependencies),
    )
    with patch("build_macos.run", return_value=result) as command:
        audit = _audit_bundle(app)
    command.assert_called_once_with(
        ["/usr/bin/otool", "-L", str(binary)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert audit["native_dependencies"]["TrustBench"] == dependencies


@mark.parametrize(
    "field,value",
    [
        ("CFBundleVersion", "old"),
        ("CFBundleShortVersionString", "wrong"),
        ("CFBundleIconFile", "default.icns"),
    ],
)
def test_bundle_rejects_inconsistent_identity_before_signature(tmp_path, field, value):
    app = tmp_path / "TrustBench.app"
    contents = app / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    (contents / "MacOS" / "TrustBench").touch()
    info = {
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleVersion": BUILD_NUMBER,
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleIconFile": "TrustBench.icns",
    }
    info[field] = value
    (contents / "Info.plist").write_bytes(plist_dumps(info))
    with patch("build_macos.run") as command, raises(RuntimeError, match="metadata"):
        _verify_bundle(app)
    command.assert_not_called()
