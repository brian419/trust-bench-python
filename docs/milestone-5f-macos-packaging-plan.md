# Milestone 5F: macOS packaging and accessibility

Branch: `feature/milestone-5f-macos-packaging`  
Base: `feature/milestone-5` at `c70826a`

## Current status

**Complete for the local Intel macOS preview.** Build 5004 from `472e176`
completed native package checks and was installed and accepted on macOS 15.7.9.
Final checks confirmed the approved TB icon, live evaluation, report saving,
Reports/Compare, and Expand Output/Show Settings during a running evaluation.
Earlier installed-app checks covered cancellation/restart, keyboard/spoken
guidance, report persistence and Ollama recovery.

**724 tests passed on macOS/Python 3.12.12 and Linux/Python 3.12.14.**

## Scope

Deliver an Intel macOS preview while preserving the CLI, source-run GUI,
evaluation behavior, report formats and explicit-import convention.

- Bundle Python, Tcl/Tk and example datasets in TrustBench.app.
- Provide a DMG with drag-to-Applications installation.
- Keep reports outside the app in Application Support.
- Keep Ollama and models as separate installations.
- Preserve Reports and Compare when Ollama is unavailable.
- Provide keyboard navigation, visible focus, progress and optional spoken guidance.
- Document installation, updates, supported configuration and evaluation limits.

Validation targets the existing Intel Mac running macOS 15.7.9. Other hardware
and operating systems remain unverified. Linux and Windows are later work.

The preview is ad-hoc signed; Apple Developer ID signing and notarization are
outside the current scope. Public release and branch integration are separate
decisions.

## Checkpoints

| Checkpoint | Status |
| --- | --- |
| 5F-1: Resources, report storage and packaged worker | Implemented; validated in build 5001 |
| 5F-2: Ollama readiness, setup and model discovery | Implemented; service recovery validated |
| 5F-3: App and DMG build | Build 5004 package and installed-app checks passed |
| 5F-4: Progress, keyboard access and spoken guidance | Implemented and manually validated |
| 5F-5: Installation and sharing documentation | Preview documentation and local validation complete |

Installed-app validation covered launch from Applications, evaluation/report
saving, report viewing/comparison, stop/restart, keyboard/spoken guidance,
report persistence after reopening, and Ollama unavailable/recovery.

## Completion evidence

- Source: `472e176`, application version 0.5.0 preview, build 5004.
- Candidate: `TrustBench-0.5.0-x86_64-20261026T130126Z-16adb796`.
- Environment: Intel macOS 15.7.9, Python 3.12.12, Tcl/Tk 8.6.18,
  PyInstaller 6.22.3.
- Native resource, signature, dependency audit, frozen-worker and DMG checks passed.
- A packaged `gemma3:1b` evaluation completed with 2 PASS and 0 request errors.
  Its report was saved, opened in Reports and compared with an earlier run.
- Screenshots and final acceptance confirmed the larger output view and approved icon.

No implementation or local-preview validation work remains in 5F. The branch
is ready for the planned code-quality follow-up and integration review.

If a downloadable preview is published later, review the project license and
bundled third-party notices, verify the downloaded copy's installation behavior,
and attach the validated DMG and checksum. Publication is not required to retain
or demonstrate the working local package. Signing/notarization is not a
completion requirement for this preview.

## Follow-up

After the final Mac check, record 5F completion and begin a separate code-quality
branch with Ruff configuration, an initial audit and reviewed cleanup. Preserve
the explicit-import convention and run the regression suite before integration.
Ruff adoption is separate from this packaging milestone.

## Documentation

- [Installation and support](macos-preview-guide.md)
- [Build commands and validation evidence](milestone-5f-3-macos-build.md)
- [Draft release notes](releases/0.5.0-preview.md)
- [Runtime foundation](milestone-5f-1-runtime-foundation.md)
- [Ollama readiness](milestone-5f-2-ollama-readiness.md)
- [Progress and keyboard access](milestone-5f-progress-accessibility.md)

## Completion criteria

- Existing CLI and source GUI functionality remain tested.
- The refreshed app launches from Applications with its bundled runtime.
- Evaluation, cancellation/restart and report persistence work in that artifact.
- Keyboard and optional spoken guidance remain usable.
- Build evidence and documentation identify the tested configuration and current
  signing status.
- The branch is ready for review before any approved integration.
