# Milestone 5F: macOS packaging and accessibility

Branch: `feature/milestone-5f-macos-packaging`  
Base: `feature/milestone-5` at `c70826a`

## Current status

Implementation is complete for the local Intel preview. Build 5001 passed
installed-app workflow checks. Build 5002 passed the Mac package checks, and
screenshots confirmed installation, launch, version display and a retained report.
Build 5003 replaces the chart icon with a TB monogram and test-result cells;
its native build and final installed-app check remain pending.

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
| 5F-3: App and DMG build | Build 5002 package checks passed; build 5003 icon refresh pending |
| 5F-4: Progress, keyboard access and spoken guidance | Implemented and manually validated; repeat a short check after rebuilding |
| 5F-5: Installation and sharing documentation | Preview guide and release draft prepared; final artifact evidence pending |

Installed-app validation covered launch from Applications, evaluation/report
saving, report viewing/comparison, stop/restart, keyboard/spoken guidance,
report persistence after reopening, and Ollama unavailable/recovery.

## Remaining work

1. Pull the icon update and rerun the 724-test suite on macOS/Python 3.12.12.
2. Build candidate 5003. Review the build output, checksum, build record and
   `bundle-audit.json` for failures or unexpected files/dependencies.
3. Install the refreshed candidate and confirm its icon/version, evaluation,
   Reports/Compare, stop/restart, keyboard/spoken guidance and retained reports.
4. Record the exact candidate, source commit and results; update the validation
   summary and release notes accordingly.

These steps complete validation of the local Intel preview.

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
