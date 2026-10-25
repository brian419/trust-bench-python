# Milestone 5A–5E review before packaging

Date: October 25, 2026.
Reviewed integration: `921fc26` on `feature/milestone-5`.
The user approved integration of `refactor/standardize-imports`; the feature
branch was fast-forwarded from `3b1ef80` to `921fc26`. `main` was not changed.

## Fix checkpoint

All four findings below are addressed by [`eb8a0f9`](https://github.com/brian419/trust-bench-python/commit/eb8a0f9d597be6171a24247997ead5ce237fc476)
on `feature/milestone-5`. This section supersedes the original open-finding
status; the original observations remain below as review history.

| Finding | Implemented correction | Regression evidence |
| --- | --- | --- |
| Invalid report statuses | Check status types before set/dictionary membership in report generation and summary helpers; report invalid data through existing ValueError handling. | List/dictionary statuses are rejected cleanly by helpers and CLI; GUI preserves the existing display and cannot claim verified completion. |
| Unknown required scoring | Validate nonempty string identifiers before comparison; return UNVERIFIED for invalid metadata. | Required identifiers are checked for live, injection and consistency reports, on either operand and when both contain the same invalid value. Legitimate optional nulls remain accepted. |
| Malformed Ollama responses | Add the narrow MalformedResponseError client exception; validate JSON object/string response shape and handle that error in all three request runners. | Invalid JSON/encoding/payload shapes are rejected. Live, consistency and injection workflows continue after a malformed response and save ERROR records. Live reference scoring retains ERROR classification and duration. Empty response strings and unrelated exceptions retain their previous semantics. |
| Buffered GUI output | Copy the launch environment and set PYTHONUNBUFFERED=1 so the actual evaluator inherits it through the CLI wrapper. | A real launcher-to-CLI-to-evaluator test receives a progress line before evaluator exit; the caller environment remains unchanged and existing settings are preserved. |

**Executed validation:** The unchanged starting snapshot passed 389 tests. The
initial 55-case regression module then exposed 52 failures before implementation
(3 preservation cases passed). The final suite, including 61 new regression
cases, passed **450 tests in 1.44 seconds** on Linux with Python 3.12.14.
`python3 -m compileall -q .`, whitespace checks and the explicit-import audit
also passed. No third-party dependencies were added. Tests used temporary files,
mocked HTTP responses and local subprocesses; they did not require paid services
or model inference.

**User validation pending:** Pull the fix and run the 450-test suite on macOS
with Python 3.12.12. Recheck live GUI progress, stop/restart and normal closure,
then open and compare completed saved reports. The earlier Mac evidence below
applies to the pre-fix runtime, not this fix checkpoint.

5F packaging, accessibility, installation and sharing remain open. Fix
implementation is complete; Mac revalidation is the next checkpoint.

## Original review outcome

The import refactor is integrated and its planned regression and manual checks
are complete. The broader 5A–5E review found four issues to address before
packaging. No runtime fixes are included in this review commit. There is no
evidence from this review that these are import-refactor regressions.

## Findings

All four findings are priority P2: reproducible correctness or usability issues
to fix before a release, rather than observed failures of the validated Mac
happy paths.

### 1. Invalid report statuses escape normal error handling

Locations: [generate_report.py](../generate_report.py#L53),
[report_summary.py](../report_summary.py#L25), and GUI report-loading/completion
callers in [desktop_gui.py](../desktop_gui.py).

A saved live report with `status: []` or `status: {}` raises an unhandled
`TypeError` during set/dictionary membership checks. The report-generation CLI
and GUI catch `ValueError` and OS errors, so this bypasses their intended
invalid-report messages. A user-selected or damaged JSON report can therefore
produce a traceback instead of a normal error.

Executed probe: otherwise valid live reports with each of those statuses passed
to `generate_text_report` raised `TypeError: unhashable type: 'list'` and
`TypeError: unhashable type: 'dict'`.

Fix: validate that statuses are strings before membership checks in report
generation and shared summary helpers. Raise `ValueError`; preserve the previous
GUI display on failure. Add CLI/helper/GUI regression coverage for JSON container
statuses, not just unknown status strings.

### 2. Unknown primary scoring can be accepted as comparable

Location: [report_compatibility.py](../report_compatibility.py),
`compare_scoring_rules`.

The code checks scoring-key presence and equality but does not validate the
required identifiers. Two live reports with matching input fingerprints and
`primary_scoring: null` / `alternative_scoring: null` receive `PARTIAL_MATCH`.
Matching absence of a required scoring definition does not establish that
scoring rules agree.

Executed probe: two such reports with valid identical SHA-256 fingerprints and
model names returned `PARTIAL_MATCH` from `compare_report_compatibility`.

Fix: validate required scoring and prompt-format identifiers by report type
before comparing them. Return `UNVERIFIED` for null, blank or non-string required
identifiers. Preserve legitimate optional nulls, especially live
`alternative_scoring` and the currently unscored consistency
`scoring_method`. Keep cross-model comparisons and existing warning semantics.
Add tests proving comparisons are blocked when required scoring is unknown.

### 3. Malformed Ollama responses can abort runs without reports

Locations: [ollama_client.py](../ollama_client.py#L30) and request exception
handlers in [eval_live.py](../eval_live.py), [consistency_runner.py](../consistency_runner.py),
and [run_prompt_injection.py](../run_prompt_injection.py).

The client directly indexes decoded JSON without checking that the payload is
an object with a string response. Current runners handle HTTP, URL and timeout
errors, but not malformed-response failures. A malformed service response can
abort the run before its report is saved, rather than recording a request error.

Executed client probes with mocked HTTP response bodies:
- Invalid JSON: `JSONDecodeError`.
- Empty JSON object: `KeyError: 'response'`.
- `{"response": null}`: returns `None`, which is not a valid response string.

The client probes were executed; loss of the report follows from inspection of
the runners' uncaught exception paths, not a live broken-server experiment.

Fix: define a narrow malformed-response failure at the client boundary and
handle it as a per-case request error in all three runners. Preserve successful
responses, HTTP/connection/timeout behavior, and the separation of ERROR from
FAIL. Test invalid JSON, non-object payloads, absent response fields and
non-string responses, including report persistence and continuation.

### 4. GUI subprocess output can remain buffered until exit

Locations: [evaluation_launcher.py](../evaluation_launcher.py#L33) and
[trustbench.py](../trustbench.py#L135).

The GUI pipes stdout but does not enable unbuffered Python output.
`bufsize=1` configures the parent's pipe wrapper; it does not make the
child evaluator flush its prints. The wrapper launches a second interpreter,
so enabling `-u` only on the wrapper would not by itself fix that evaluator.
Longer runs can appear quiet and then display output in a batch.

Executed probe with `PYTHONUNBUFFERED` absent: launch a child through
`run_live_command` that prints a line and then sleeps for 0.8 seconds.
The pipe was not readable after 0.25 seconds; the first line arrived after
approximately 0.81 seconds. This exercises the launcher, not real Ollama timing.

Fix: make unbuffered output reach the actual evaluator, for example by passing
a copied child environment with `PYTHONUNBUFFERED=1` through the GUI launch
chain. Preserve process-group handling and existing CLI behavior. Add a bounded
integration test demonstrating receipt of a flushed line before child exit.

## Evidence and coverage

- All 63 merged Python files matched the GitHub snapshot before review.
- Existing full suite on the review snapshot: **389 passed in 0.99 seconds**
  on Linux with Python 3.12.14.
- Earlier user evidence on the same runtime source: **389 passed in 5.63 seconds**
  on macOS with Python 3.12.12.
- User manual validation covered all five evaluation CLI workflows, readable
  report generation, standalone saved-report comparison, and real macOS GUI
  report browsing, command preview, live Ollama completion, stop/restart,
  comparison validation messages, and idle-window closure.
- Focused probes above used temporary files, mocked HTTP responses and a local
  child process. They did not use paid services or real model inference.
- Existing tests cover many normal and error paths, but do not demonstrate the
  four cases above. A passing suite does not close those findings.

## Scope boundaries and 5F preparation

Keep these release tasks distinct from the four fixes:

- Establish supported platforms. The current launcher imports POSIX
  `os.killpg` and uses process groups; Windows support cannot be assumed.
  macOS has manual evidence; Linux GUI use still needs manual validation.
- Verify keyboard-only workflows, focus order, accessible labels and
  readable contrast with the actual Tkinter build.
- Decide packaging and data locations. CLI defaults currently assume the
  repository working directory, while the GUI uses a source-tree project root.
  A packaged app needs deliberate resource, writable report and subprocess
  entry-point handling; wrapping the existing launcher alone is insufficient.
- Provide clean-install instructions for Python/Tcl/Tk, Ollama/model setup,
  offline report access, and explicit supported-platform limitations.
- Keep exact model-digest capture, broader GUI modes, non-live report summaries,
  configurable consistency/injection experiments and a shared service-layer
  extraction as separately scoped work. They are documented limitations, not
  automatically required new features for the first package.
- Do not claim signing, installer behavior, screen-reader accessibility,
  Windows support or release readiness without the corresponding validation.

Current order: the four fixes and automated regression checks are complete;
revalidate affected Mac workflows, then implement and validate 5F. Do not merge
Milestone 5 into `main` or publish a release as part of this review.
