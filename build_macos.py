"""Build a local Intel macOS app/DMG candidate; never publish or install it."""

from argparse import ArgumentParser
from datetime import datetime, timezone
from hashlib import file_digest
from importlib.metadata import PackageNotFoundError, distributions, version
from json import dumps, loads
from pathlib import Path
from platform import mac_ver, machine, python_version
from plistlib import load as load_plist
from subprocess import CalledProcessError, TimeoutExpired, run
from sys import exit, platform, stderr
from tempfile import TemporaryDirectory
from uuid import uuid4

from app_identity import APP_VERSION, BUILD_NUMBER, BUNDLE_ID, PREVIEW_LABEL

ROOT = Path(__file__).resolve().parent
PYINSTALLER_VERSION = "6.22.3"
TARGET_PYTHON = "3.12.12"
TARGET_ARCH = "x86_64"
DATA_FILES = (
    "eval-read-live.json",
    "eval-read-reference.json",
    "eval-read-valid.json",
    "prompt-injection-cases.json",
    "scoring-examples.json",
)
MAC_TOOLS = (
    "/usr/bin/codesign",
    "/usr/bin/ditto",
    "/usr/bin/file",
    "/usr/bin/hdiutil",
    "/usr/bin/otool",
)


def build_plan() -> dict:
    return {
        "version": APP_VERSION,
        "build_number": BUILD_NUMBER,
        "label": PREVIEW_LABEL,
        "architecture": TARGET_ARCH,
        "python": TARGET_PYTHON,
        "pyinstaller": PYINSTALLER_VERSION,
        "spec": str(ROOT / "macos" / "TrustBench.spec"),
        "bundled_datasets": list(DATA_FILES),
        "outputs": "unique candidate directory under dist/macos/",
        "signing": "ad-hoc; not Developer ID signed or notarized",
        "publishes": False,
        "installs": False,
    }


def check_build_environment() -> dict:
    """Fail before creating output if this interpreter cannot build the target."""
    if platform != "darwin":
        raise RuntimeError("Native builds require macOS. Use --plan on other systems.")
    if machine() != TARGET_ARCH:
        raise RuntimeError("This checkpoint builds on an Intel x86_64 Mac only.")
    if python_version() != TARGET_PYTHON:
        raise RuntimeError(
            f"Use Python {TARGET_PYTHON} for the initial validated build."
        )
    try:
        installed = version("pyinstaller")
    except PackageNotFoundError as error:
        raise RuntimeError(
            "Install requirements-build-macos.txt in the build venv first."
        ) from error
    if installed != PYINSTALLER_VERSION:
        raise RuntimeError(
            f"Expected PyInstaller {PYINSTALLER_VERSION}, found {installed}."
        )
    for name in DATA_FILES:
        if not (ROOT / name).is_file():
            raise RuntimeError(f"Missing bundled dataset: {name}")
    if not (ROOT / "macos" / "TrustBench.icns").is_file():
        raise RuntimeError("Missing TrustBench application icon.")
    for tool in MAC_TOOLS:
        if not Path(tool).is_file():
            raise RuntimeError(f"Required macOS build tool is unavailable: {tool}")
    if not mac_ver()[0]:
        raise RuntimeError("Could not determine the build Mac's system version.")

    try:
        from tkinter import TclError, TclVersion, Tk, TkVersion
    except ImportError as error:
        raise RuntimeError(
            "Build Python must include Tkinter and its native libraries."
        ) from error

    if TclVersion < 8.6 or TkVersion < 8.6:
        raise RuntimeError("Build Python must include Tcl/Tk 8.6 or newer.")
    try:
        window = Tk()
    except TclError as error:
        raise RuntimeError(f"Build Python cannot initialize Tcl/Tk: {error}") from error
    try:
        window.withdraw()
        tcl_patch = window.tk.call("info", "patchlevel")
        tk_patch = window.tk.call("package", "provide", "Tk")
    finally:
        window.destroy()
    return {
        "python": python_version(),
        "architecture": machine(),
        "macos": mac_ver()[0],
        "tcl": str(tcl_patch),
        "tk": str(tk_patch),
        "pyinstaller": installed,
    }


def _checksum(path: Path) -> str:
    with path.open("rb") as source:
        return file_digest(source, "sha256").hexdigest()


def _audit_bundle(app: Path) -> dict:
    """Check package contents and native dependency paths without modifying the app."""
    base = app.resolve()
    files = []
    links = []
    native = {}
    forbidden = {
        ".git",
        ".venv",
        ".venv-macos-build",
        "__pycache__",
        "reports",
        "tests",
    }
    magic = {
        b"\xfe\xed\xfa\xce",
        b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
        b"\xca\xfe\xba\xbf",
        b"\xbf\xba\xfe\xca",
    }
    for path in sorted(app.rglob("*")):
        relative = path.relative_to(app).as_posix()
        if (
            forbidden.intersection(path.relative_to(app).parts)
            or path.name == ".env"
            or path.name.startswith(".env.")
        ):
            raise RuntimeError(
                f"Unexpected development/user file in application: {relative}"
            )
        if path.is_symlink():
            if (
                path.readlink().is_absolute()
                or not path.exists()
                or not path.resolve().is_relative_to(base)
            ):
                raise RuntimeError(
                    f"Broken or external application symlink: {relative}"
                )
            links.append({"path": relative, "target": str(path.readlink())})
        elif path.is_file():
            files.append(
                {
                    "path": relative,
                    "bytes": path.stat().st_size,
                    "sha256": _checksum(path),
                }
            )
            with path.open("rb") as source:
                header = source.read(4)
            if header in magic:
                output = run(
                    ["/usr/bin/otool", "-L", str(path)],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
                dependencies = []
                for line in output.splitlines():
                    dependency = line.strip().split(" (", 1)[0]
                    if (
                        not line[:1].isspace()
                        or not dependency
                        or dependency.endswith(":")
                    ):
                        continue
                    if dependency.startswith("/") and not dependency.startswith(
                        ("/usr/lib/", "/System/Library/")
                    ):
                        raise RuntimeError(
                            f"External native dependency in {relative}: {dependency}"
                        )
                    dependencies.append(dependency)
                native[relative] = dependencies
    return {"files": files, "symlinks": links, "native_dependencies": native}


def _verify_bundle(app: Path) -> dict:
    binary = app / "Contents" / "MacOS" / "TrustBench"
    if not binary.is_file():
        raise RuntimeError("The built app is missing its executable.")
    with (app / "Contents" / "Info.plist").open("rb") as source:
        info = load_plist(source)
    if info.get("CFBundleIdentifier") != BUNDLE_ID:
        raise RuntimeError("Unexpected application bundle identifier.")
    if (
        info.get("CFBundleShortVersionString") != APP_VERSION
        or info.get("CFBundleVersion") != BUILD_NUMBER
    ):
        raise RuntimeError("Unexpected application version/build metadata.")
    resources = app / "Contents" / "Resources"
    if info.get("CFBundleIconFile") != "TrustBench.icns":
        raise RuntimeError("Unexpected application icon metadata.")
    icon = resources / "TrustBench.icns"
    if not icon.is_file() or _checksum(icon) != _checksum(
        ROOT / "macos" / "TrustBench.icns"
    ):
        raise RuntimeError("Bundled TrustBench icon is missing or changed.")
    for name in DATA_FILES:
        bundled = resources / name
        if not bundled.is_file() or _checksum(bundled) != _checksum(ROOT / name):
            raise RuntimeError(f"Bundled dataset is missing or changed: {name}")
    if not any(app.rglob("_tkinter*.so")):
        raise RuntimeError("The bundle is missing the Tkinter extension.")
    for script in ("init.tcl", "tk.tcl"):
        if not any(app.rglob(script)):
            raise RuntimeError(f"The bundle is missing Tcl/Tk runtime data: {script}")
    if not any(
        p.is_file() and (p.name == "Python" or p.name.startswith("libpython"))
        for p in app.rglob("*")
    ):
        raise RuntimeError("The bundle is missing the Python shared runtime.")
    architecture = run(
        ["/usr/bin/file", str(binary)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if TARGET_ARCH not in architecture:
        raise RuntimeError(
            "The application executable is not the Intel target architecture."
        )
    run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)], check=True)
    signature = run(
        ["/usr/bin/codesign", "--display", "--verbose=4", str(app)],
        check=True,
        capture_output=True,
        text=True,
    )
    if "Signature=adhoc" not in signature.stderr + signature.stdout:
        raise RuntimeError(
            "Unexpected signing state; this checkpoint expects an ad-hoc build."
        )
    return {
        "architecture": TARGET_ARCH,
        "signature": "ad-hoc verified",
        "notarized": False,
    }


def _worker_smoke_test(app: Path) -> dict:
    """Exercise the frozen entry point without a GUI, Ollama or user-data writes."""
    with TemporaryDirectory(prefix="trustbench-bundle-check-") as directory:
        temporary = Path(directory)
        dataset = temporary / "empty.json"
        dataset.write_text("[]", encoding="utf-8")
        reports = temporary / "reports"
        completed = run(
            [
                str(app / "Contents" / "MacOS" / "TrustBench"),
                "--trustbench-evaluate",
                "--dataset",
                str(dataset),
                "--model",
                "gemma3:1b",
                "--reports-dir",
                str(reports),
            ],
            cwd=temporary,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        saved = list(reports.glob("evaluation-*.json"))
        if len(saved) != 1 or "Report saved to:" not in completed.stdout:
            raise RuntimeError("The frozen worker did not report one saved evaluation.")
        report = loads(saved[0].read_text(encoding="utf-8"))
        if report.get("results") != [] or report.get("summary", {}).get("errors") != 0:
            raise RuntimeError("Unexpected frozen worker smoke-test report.")
        return {"frozen_worker": "passed", "cases": 0, "ollama_requests": 0}


def _source_evidence() -> dict:
    try:
        commit = run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            run(
                ["git", "status", "--porcelain"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        return {"commit": commit, "dirty": dirty}
    except (OSError, CalledProcessError):
        return {"commit": "unknown", "dirty": None}


def build_candidate() -> Path:
    environment = check_build_environment()
    from PyInstaller.__main__ import run as run_pyinstaller

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = f"TrustBench-{APP_VERSION}-{TARGET_ARCH}-{stamp}-{uuid4().hex[:8]}"
    output = ROOT / "dist" / "macos" / candidate
    work = ROOT / "build" / "macos" / candidate
    output.mkdir(parents=True, exist_ok=False)
    work.mkdir(parents=True, exist_ok=False)
    run_pyinstaller(
        [
            "--clean",
            "--distpath",
            str(output),
            "--workpath",
            str(work),
            str(ROOT / "macos" / "TrustBench.spec"),
        ]
    )
    app = output / "TrustBench.app"
    verification = _verify_bundle(app)
    audit = _audit_bundle(app)
    smoke = _worker_smoke_test(app)
    stage = work / "dmg-content"
    stage.mkdir()
    run(["/usr/bin/ditto", str(app), str(stage / "TrustBench.app")], check=True)
    (stage / "Applications").symlink_to("/Applications", target_is_directory=True)
    (stage / "INSTALL.txt").write_text(
        (ROOT / "macos" / "INSTALL.txt").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _verify_bundle(stage / "TrustBench.app")
    _audit_bundle(stage / "TrustBench.app")
    dmg = output / f"TrustBench-{APP_VERSION}-macos-{TARGET_ARCH}.dmg"
    run(
        [
            "/usr/bin/hdiutil",
            "create",
            "-volname",
            "TrustBench",
            "-srcfolder",
            str(stage),
            "-fs",
            "HFS+",
            "-format",
            "UDZO",
            str(dmg),
        ],
        check=True,
    )
    run(["/usr/bin/hdiutil", "verify", str(dmg)], check=True)
    checksum = _checksum(dmg)
    (output / "SHA256SUMS.txt").write_text(
        f"{checksum}  {dmg.name}\n", encoding="utf-8"
    )
    record = {
        "app_version": APP_VERSION,
        "build_number": BUILD_NUMBER,
        "label": PREVIEW_LABEL,
        "source": _source_evidence(),
        "environment": environment,
        "verification": verification,
        "smoke_test": smoke,
        "dmg": {"filename": dmg.name, "sha256": checksum},
        "datasets": {name: _checksum(ROOT / name) for name in DATA_FILES},
        "build_packages": {
            d.metadata["Name"]: d.version for d in distributions() if d.metadata["Name"]
        },
        "native_gui_validated": False,
        "installed_app_validated": False,
        "published": False,
        "support_scope": {
            "preview_architecture": "x86_64",
            "preview_macos": "15.7.9",
            "broader_compatibility_verified": False,
        },
        "bundle_audit": {
            "files": len(audit["files"]),
            "symlinks": len(audit["symlinks"]),
            "native_binaries": len(audit["native_dependencies"]),
        },
    }
    packages = record["build_packages"]
    (output / "build-requirements.lock.txt").write_text(
        "".join(
            f"{name}=={packages[name]}\n" for name in sorted(packages, key=str.casefold)
        ),
        encoding="utf-8",
    )
    (output / "build-record.json").write_text(
        dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    (output / "bundle-audit.json").write_text(
        dumps(audit, indent=2) + "\n", encoding="utf-8"
    )
    return output


def main(arguments=None) -> int:
    parser = ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--plan",
        action="store_true",
        help="Show the plan without dependencies or writes.",
    )
    modes.add_argument(
        "--check",
        action="store_true",
        help="Check the Mac build environment without building.",
    )
    args = parser.parse_args(arguments)
    try:
        if args.plan:
            print(dumps(build_plan(), indent=2))
        elif args.check:
            print(dumps(check_build_environment(), indent=2))
        else:
            print("Build candidate saved to:", build_candidate())
    except (CalledProcessError, OSError, RuntimeError, TimeoutExpired) as error:
        print(f"Build failed: {error}", file=stderr)
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
