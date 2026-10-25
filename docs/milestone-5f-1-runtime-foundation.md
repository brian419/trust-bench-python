# Milestone 5F-1: runtime foundation

Status: implementation, agent checks and Mac source validation complete.
An actual macOS bundle still requires the later 5F-3 build validation.
Branch: `feature/milestone-5f-macos-packaging`.
Implementation: [`ec4396b`](https://github.com/brian419/trust-bench-python/commit/ec4396b7114f9f60f52406ab8a7b1ff880d9de0b).

This checkpoint prepares the runtime for a future macOS app. It does not
produce a built .app, DMG, signed installer or release.

## Resource and report locations

| Context | Datasets/resources | Default report destination |
| --- | --- | --- |
| Existing source GUI | Source module directory | Source checkout reports/ |
| Existing source CLI | Existing defaults and explicit dataset arguments are preserved | Current working directory reports/ |
| Future packaged GUI | Bundled module directory | ~/Library/Application Support/TrustBench/reports/ |

`runtime_paths.py` resolves resources using its module location, independently
of the current working directory. A packaged-mode marker selects the macOS
user-data location. The first supported packaged path policy is macOS; Linux
and Windows packaging remain later work. Source use is not restricted to macOS.

Resolving resources, browsing reports and previewing a command do not create
the user-data directory. Starting a packaged evaluation creates its user-data
working directory; the evaluator creates the reports directory when saving.

Changing the installed app/resource location leaves the same user-report
location in place. Existing source reports are not moved, copied or deleted.
Use the existing **Open Evaluation Report** button to read an older report
where it already lives. This is opening a file, not an automatic migration or
import into the packaged report list.

## Worker entry point

`app_entry.py` is the intended future bundle entry point. Without special
arguments it opens the existing desktop GUI. It can also be run from source:

```bash
python3 app_entry.py
```

The launcher's packaged branch invokes the app executable with the private
`--trustbench-evaluate` flag, explicit dataset/model arguments and an explicit
`--reports-dir`. It does not treat the app executable as a Python interpreter,
run a source-script path inside the bundle, or launch another GUI as its worker.

Worker dispatch happens before importing the desktop GUI. It calls the shared
live evaluator in that child process. Output/error pipe descriptors are
duplicated into line-buffered UTF-8 streams, including when a windowed runtime
has no Python stdout/stderr objects. Unexpected worker errors remain visible
in the error pipe with a nonzero exit status.

`eval_live.main` adds an optional `report_dir` keyword; its existing default,
parameters, scoring, CLI flags and relative source report behavior are retained.
The worker passes an absolute output location. Source GUI launches keep the
existing unified CLI subprocess chain. Both launch paths keep the same
process-group cleanup and unbuffered environment behavior.

The runtime assumptions follow PyInstaller's official guidance:
- [Module-relative resources and the bundled executable](https://pyinstaller.org/en/stable/runtime-information.html).
- [Subprocess and windowed-runtime considerations](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html).

Packaging configuration, data inclusion and actual bootloader behavior still
need the native macOS build checks in 5F-3. These unit/subprocess checks are not
a substitute for testing a real app bundle.

## Executed checks

The original **450 tests passed** after the runtime changes. The final suite
passed **468 tests in 1.53 seconds** on Linux with Python 3.12.14.
`python3 -m compileall -q .`, whitespace checks and an import audit of all
67 Python files also passed. No dependencies were added.

The 18 new cases cover:
- Frozen-marker detection and unchanged source report locations outside the
  checkout's working directory.
- Stable user-report locations across changed bundle/resource paths.
- Packaged command construction, paths with spaces, deferred directory creation,
  and storage-creation failures.
- An explicit evaluator report directory without changing cwd or input bytes.
- Worker success, failure, normal GUI dispatch and rejected arguments.
- A real source CLI call from outside the checkout with an explicit dataset.
- Fresh simulated frozen GUI imports that select bundled resources and user
  reports, plus offline listing/viewing of an older report without modifying it.
- A real worker subprocess with mocked local HTTP, no available Tkinter module
  and absent Python stdout/stderr objects. It emits progress before exit,
  stops as a process group, restarts, and writes a completed report only to the
  selected user-report directory.

Frozen mode and bundle locations were simulated for these checks. No macOS
bundle has been built or run in the agent environment. HTTP responses were
mocked; no paid service or real inference was needed.

## Mac source validation and next step

On October 25, 2026, the user pulled `b3ce0a8` and ran the full suite with
Python 3.12.12 on macOS: **468 passed in 5.56 seconds**, with a clean working
tree. The user then launched `app_entry.py` and explicitly confirmed all five
smoke checks:

- The normal TrustBench window opened.
- Existing reports appeared and opened in the formatted viewer.
- A real `eval-read-live.json` / `gemma3:1b` evaluation completed and saved
  `evaluation-3374aa567c434de4b1775766a88f48d4.json`.
- Stop followed by a fresh start worked.
- Normal window closure produced no traceback.

The completed run had 1 PASS, 1 FAIL and 0 request errors. It expected the English
name `Paris` but received `Parigi`; the normalized exact-match scorer correctly
recorded FAIL. This is a model output/format observation, not a runtime error or
a general accuracy measurement.

Screenshots also show the new report opened in the Reports tab and a comparison
against `evaluation-bc339d445631492f8f18a13ee683340c.json`: 1 unchanged case,
1 FAIL-to-PASS status change, no regressions or new errors, and expected
missing-model-metadata warnings. Those changes describe the selected
previous/current ordering, not a chronological claim of model improvement.

5F-1 is complete for its source/runtime checkpoint. Source validation uses the
checkout reports/ directory; the Application Support path and frozen settings
have simulated test coverage and still require validation in a native app build.

Next is **5F-2: Ollama readiness, setup guidance and recovery**. App/DMG builds,
accessibility validation and release preparation remain open. Neither parent
branch was merged and no release was published as part of this checkpoint.
