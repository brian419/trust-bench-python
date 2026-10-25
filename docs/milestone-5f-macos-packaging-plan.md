# Milestone 5F: macOS packaging, accessibility and sharing

Status: 5F-1 is source-validated on macOS (468 tests). 5F-2 readiness/setup
recovery is implemented and agent-tested (520 tests); Mac validation is pending.
No app/DMG build is claimed. 5F-3 through 5F-5 remain open.
Branch: `feature/milestone-5f-macos-packaging`.
Base: `feature/milestone-5` at `c70826ab340288d1cd393e802acb787bd82ed6c4`.
Baseline: 450 tests passed on the user's Mac with Python 3.12.12, with
completed Ollama evaluation, cancellation/restart, report comparison and
normal closure validated.

## Agreed release scope

- Target a downloadable macOS desktop application for general users.
- Provide one official TrustBench download location using GitHub Releases,
  with an intended DMG containing TrustBench.app.
- Bundle Python and required GUI components. End users should not need Python,
  Git, a source checkout or terminal commands to launch TrustBench.
- Build and manually validate Intel macOS first using the user's Mac.
  Apple Silicon compatibility must be established separately; do not claim
  a tested universal build without evidence.
- Preserve the existing CLI, source-run application, public callables, datasets,
  scoring behavior, reports and explicit-import convention.
- Keep reports in a writable user location outside the installed application,
  so an application update does not remove them.
- Linux is a later target. Windows is deferred for separate discussion.
- Keep work on this branch until integration is approved. Do not merge into
  main or publish a release during implementation checkpoints.

## Ollama decision and required follow-up

For this first release, Ollama and downloaded models remain separate
installations. TrustBench does not bundle either of them. Reading and comparing
existing reports must work without Ollama.

This is a release requirement to implement and validate, not a dependency
problem to ignore until after packaging:

- Distinguish a reachable local Ollama service from an unavailable service and
  distinguish an unavailable requested model from a ready model.
- Give actionable setup guidance from the GUI when live evaluation is not ready.
  An unavailable service alone does not prove that Ollama is not installed.
- Preserve working report browsing and comparison when Ollama is unavailable.
- Recheck readiness after the user completes setup; do not require editing code
  or restarting the entire application merely to retry.
- Keep installation and model downloads explicit user actions, with their
  storage requirements explained in the setup documentation.
- Validate the first-run experience with Ollama absent/unreachable, the service
  running without the requested model, and the service/model ready.
- Before release, explicitly review whether the separate dependency setup is
  understandable for a new user. Address confusing instructions or failed
  recovery during 5F, rather than silently accepting them.
- After wider user feedback, revisit whether a more integrated setup is needed.
  Bundling Ollama/models would be separately scoped work, with distribution,
  size, update, licensing and resource implications reviewed then.

## Incremental implementation checkpoints

### 5F-1: Application resources, report storage and packaged execution

**Implemented in `ec4396b`; 468 tests passed on Linux/Python 3.12.14.**
See the [runtime checkpoint](milestone-5f-1-runtime-foundation.md) for paths,
worker dispatch, executed evidence and the remaining Mac/build validation.

Audit and separate bundled read-only resources from writable user reports.
Choose a macOS user-data location and preserve existing source-run paths and
older reports. Provide a deliberate way to open/import older reports without
silently deleting or relocating them.

Make evaluator launch work in a packaged application. A bundled
`sys.executable` is the application executable, so it must not be treated as an
ordinary Python interpreter that can run an arbitrary source-script path.
Choose and test an explicit packaged evaluation entry path while preserving
process-group cancellation, real-time output, restart and the source CLI.

Test working directories outside the repository, resource lookup, writable
report paths, retained source behavior and process dispatch.

### 5F-2: Ollama readiness and first-run guidance

**Implemented in `57b466e`; 520 tests passed on Linux/Python 3.12.14.**
See the [5F-2 checkpoint](milestone-5f-2-ollama-readiness.md) for behavior,
thread/lifecycle tests and the pending Mac validation. Opening TrustBench and
using Reports/Compare do not require an Ollama check.

Implement the readiness and recovery requirements above using bounded local
checks. Keep HTTP/model work off Tkinter's event thread. Do not make report-only
workflows depend on the model service. Preserve existing evaluation request
errors and scoring semantics.

### 5F-3: macOS app and DMG build

Prepare reproducible local build configuration and commands for the macOS app
and DMG. Keep packaging tools as build-time dependencies where appropriate.
Check the selected packager's current official documentation during
implementation.

Validate the built app on the user's Intel Mac, outside the checkout and from
Applications, with no reliance on the development virtual environment.
Verify Python/Tcl/Tk/resource inclusion and process cleanup. State signing and
notarization status accurately; do not require paid enrollment as an unstated
prerequisite. Test any platform security prompts and document the actual result.

### 5F-4: Accessibility and user-facing clarity

Check keyboard navigation, focus visibility, control activation, report
selection/viewing and comparison, text readability and error recovery.
Include real macOS accessibility checks before claiming accessibility support.

Clarify running/completed/stopped states. Current progress is per-case text in
Evaluation Output; there is no separate progress bar. Decide whether clearer
status/count text is needed during this review without changing scoring.

### 5F-5: Clean-install and sharing validation

Test the DMG install and app launch, absent Ollama/model guidance, live
evaluation, stop/restart, saved reports, comparisons, normal closure and update
persistence. Preserve the full regression suite and add focused tests for new
behavior.

Prepare download/setup instructions, supported-platform details, release notes,
checksums and explicit limitations. Confirm the release download permissions
match the intended audience before publishing. A single official TrustBench
download does not mean Ollama or models are included in that download.

## Completion gates

- All existing CLI/source functionality remains available and tested.
- The macOS app launches without a Python/Git installation or a source checkout.
- Bundled resources load independently of the working directory.
- Reports persist outside the app across updates.
- Ollama/model setup guidance and retry behavior are validated.
- Report-only workflows work without Ollama.
- Packaged live evaluation streams output and supports verified stop/restart.
- Mac build, accessibility and clean-install evidence is recorded honestly.
- A concrete release candidate is reviewable before any release publication.

No packaged app, DMG, release, signing or accessibility result is claimed by
this planning checkpoint.
