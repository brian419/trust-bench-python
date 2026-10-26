# Milestone 5F-3: local Intel macOS app and DMG build

Status: **local Intel Mac build and installed-app checks passed; broader release validation pending**.
Branch: `feature/milestone-5f-macos-packaging`.
Starting evidence: 681 tests passed in 9.50 seconds on the user's Mac/Python
3.12.12, with app-controlled spoken guidance explicitly approved.

## Build scope

`build_macos.py` prepares an Intel `TrustBench.app` and an HFS+ compressed DMG
using PyInstaller 6.22.3 and built-in macOS tools. The app bundles Python,
Tkinter/Tcl/Tk and an explicit allowlist of five example datasets. It does not
bundle user reports, source history, virtual environments, Ollama or model files.
The entry point remains `app_entry.py`; GUI evaluation uses its private worker.
The source CLI, evaluation behavior and all existing functionality are retained.

This is an internal `0.5.0` build candidate, not a published release. The spec
targets x86_64, disables argv emulation to avoid Tk event interference, and uses
a directory app bundle rather than one-file self-extraction. PyInstaller's
default ad-hoc signing is checked explicitly; no Developer ID, paid enrollment,
notarization, release upload or installation is performed. The initial icon is
the packager default; branding is not claimed complete.

The bundle's minimum macOS version is conservatively set to the build host's
version. Only the user's Intel Mac is the immediate validation target. Apple
Silicon, older macOS versions, Linux and Windows are not supported-build claims
from this checkpoint.

## Developer commands on the Mac

From the repository on the packaging branch:

```bash
git pull --ff-only origin feature/milestone-5f-macos-packaging
~/.pyenv/versions/3.12.12/bin/python3 -m pytest -q
git status

~/.pyenv/versions/3.12.12/bin/python3 -m venv .venv-macos-build
.venv-macos-build/bin/python -m pip install -r requirements-build-macos.txt
.venv-macos-build/bin/python build_macos.py --check
```

Expect **702 automated tests**. The separate build venv keeps build packages out
of application runtime requirements and the existing test environment. No GitHub
Actions jobs or paid services are used. Pip needs internet to fetch build tools.

`--check` verifies macOS, Intel architecture, Python 3.12.12, the pinned packager,
datasets and native tools, and initializes/destroys a hidden Tk window to check
the selected interpreter's actual GUI runtime. If it fails, share the output;
do not replace or rebuild the working development Python speculatively.

After the check succeeds:

```bash
.venv-macos-build/bin/python build_macos.py
```

The script prints `Build candidate saved to: ...` only after all build stages
finish. A `--plan` mode also works without Mac tools or PyInstaller and makes no
output-directory writes. Do not use an installed frozen app as the build Python.

## Outputs and checks

Every attempt gets a unique directory under `dist/macos/` and matching scratch
work under `build/macos/`. Earlier candidates and user data are not overwritten
or removed. These directories and the build venv are ignored by Git.

A successful candidate directory contains:

- `TrustBench.app` and PyInstaller's accompanying directory build output.
- `TrustBench-0.5.0-macos-x86_64.dmg` with the app, an Applications symlink and INSTALL.txt.
- `SHA256SUMS.txt` covering the DMG.
- `build-record.json` with commit/dirty state, build environment and package
  versions, dataset hashes, verification/smoke results and explicit pending flags.
- `build-requirements.lock.txt` recording resolved package versions for that build.

The packager version is pinned in the repository; its transitive resolution is
recorded with each candidate. This is a repeatable build procedure, not a claim
of byte-identical artifacts across different environments or build times.

Before creating the DMG, the script checks the executable, Info.plist identifier,
dataset hashes, Python shared runtime, Tkinter extension and Tcl/Tk script data.
It checks Intel executable architecture and verifies the ad-hoc code signature.

It then runs the actual frozen worker with an empty temporary dataset and an
explicit temporary report directory, from outside the repository. This needs
no Ollama requests and must save one valid empty report through the captured
output pipe. The temporary directory is removed afterward. This exercises worker
dispatch and report output, not real inference or GUI behavior.

The app is staged with macOS `ditto` to preserve symlinks and metadata, and its
signature/resources are checked again. `hdiutil` creates/verifies the DMG.
Neither the source reports nor the installed user's data are used during these
automated checks. A failed build may leave its unique partial output/work folder
for inspection; the completion record is not written on failure.

## Native app validation after a successful build

1. Open the new DMG in Finder. Confirm TrustBench.app, Applications and INSTALL.txt
   appear. Drag the app into Applications, then eject the image. If a prior app
   already exists there, preserve it separately before replacing it for testing.
2. Launch from Applications with Finder, outside VS Code and the checkout. Confirm
   the app starts without activating a venv or supplying a Python command. If it
   is blocked, record the exact macOS message; do not disable Gatekeeper globally.
   Local build behavior does not establish downloaded/quarantined app behavior.
3. Expect the installed app's Reports list to start empty if no packaged runs
   exist. Source reports remain in the checkout. Open Evaluation Report can view
   them elsewhere. To list/compare chosen older reports, copy only the desired
   evaluation JSON files into the packaged reports directory; no migration is automatic.
4. In Evaluate, confirm the bundled default dataset is selected and model refresh
   works. Complete a real `gemma3:1b` evaluation. Confirm progress, live output and
   the resulting report appear. Generate another report and compare the two.
5. Stop an active run, then start another. Close during a run and check process
   cleanup. Reopen and confirm previously saved reports remain available.
6. Check keyboard focus, tab shortcuts, dialog recovery, optional spoken guidance,
   spoken report browsing and Read current view in the actual packaged runtime.
7. Check Reports/Compare without Ollama, unavailable-service guidance and recovery,
   and the missing-model path. Ollama/models remain separate installations.

Packaged reports live at:

```text
~/Library/Application Support/TrustBench/reports
```

To inspect a startup failure from Terminal after installation, run the executable
from a different working directory and share the output:

```bash
cd /tmp
/Applications/TrustBench.app/Contents/MacOS/TrustBench
```

Keep the build output and manual observations together. The record intentionally
marks `native_gui_validated` and `installed_app_validated` false; its worker smoke
pass alone must not be presented as completion of the checklist above.

## Agent verification and limits

**702 tests passed** on Linux/Python 3.12.14, including **21 new build cases**.
The previous 681 tests remain present. Tests cover host/version/tool guards,
Tk preflight cleanup, executable spec settings, explicit data inclusion, missing
or modified bundle resources, signing failure, temporary worker dispatch, failure
before DMG creation, symlink staging, checksums, records and unique output paths.
Mac native tools, PyInstaller execution and GUI creation are mocked in these tests.
`--plan`, compilation and explicit-import checks were executed. The pinned
PyInstaller 6.22.3 distribution was also successfully downloaded for inspection.

No native Mac app or DMG was built in the Linux agent environment. No actual
signature, DMG mount, installed app, native speech, clean install or public
download was validated here. Sharing, signing/notarization decisions, remaining
accessibility checks and release preparation follow native build validation.

## Official build references

- [PyInstaller spec files](https://pyinstaller.org/en/stable/spec-files.html).
- [macOS architecture, signing and event handling](https://pyinstaller.org/en/stable/feature-notes.html).
- [PyInstaller usage options](https://pyinstaller.org/en/stable/usage.html).
- [Bundled resource lookup](https://pyinstaller.org/en/stable/runtime-information.html).
- [Symlink preservation](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html).

## User-verified native checkpoint, October 26, 2026 (UTC)

At source commit `789887c`, the user passed **702 tests in 13.75 seconds** on
Intel macOS 15.7.9 / Python 3.12.12, with Tcl/Tk 8.6.18 and PyInstaller 6.22.3.
The build completed all scripted checks and produced a verified DMG in candidate
`TrustBench-0.5.0-x86_64-20261026T033014Z-941e8f3d`.

The user installed the app in Applications and confirmed launching without a
Python command, real evaluation and report saving, Reports viewing and Compare.
The user additionally confirmed all four follow-up checks: stop/restart,
keyboard navigation and spoken guidance, report persistence after closing and
reopening, and unavailable-Ollama guidance followed by recovery after restarting
Ollama. These are user-reported results for this installed candidate on one Mac.
The original build record remains unchanged and retains its pre-validation flags.

A fresh macOS account, another machine/architecture, downloaded/quarantined
installation, Developer ID signing/notarization and public distribution remain
unverified. No release was published or branch merged at this checkpoint.
