# Pre-build evaluation progress and accessibility checkpoint

Branch: `feature/milestone-5f-macos-packaging`.
Status: implemented and agent-tested; Mac progress and accessibility validation pending.
No app/DMG build or release is claimed.

## User evidence and motivation

The user passed **532 tests in 6.18 seconds** on macOS/Python 3.12.12.
They verified installed-model refresh, empty-field recovery, selection without
typing, command preview, real evaluation, stop/restart and controls fitting the
window. Screenshots show the official external-link confirmation and a completed
evaluation. Service-unavailable recovery and screen-reader operation were not
reported as tested.

During quiet model requests, Evaluation Output did not make continued activity
clear. The smaller-window screenshot also showed limited output height. This
checkpoint addresses that feedback before building the app.

## Implemented behavior

- A persistent status area sits between evaluation controls and Evaluation Output.
- It shows the current activity, completed-case count/bar and elapsed time.
- Waiting names the current case number. A quiet request does not freeze the timer.
- PASS, FAIL and ERROR each count as one finished case, never as an accuracy bar.
- The case bar measures completed cases, not percentage of runtime or tokens.
- No completion-time estimate or model-internal "thinking" state is invented.
- All cases finished is followed by report preparation/saving and process completion.
- The final message uses existing report-verification logic. A zero exit without a
  verified report does not claim a verified successful evaluation.
- Stop requests retain a stopping message while cleanup is pending; unverified
  shutdown remains visibly distinct and continues to prevent restarting.
- A new run resets counts and elapsed time. Terminal states freeze elapsed time.
- No continuous activity animation is introduced. Text and counts provide status
  without depending on motion or color.
- Dataset entry and Browse Dataset share a row. The initial window is taller,
  capped against screen height; output still expands on resize.
- Notebook keyboard traversal is enabled. Tab/Shift-Tab leave read-only report,
  comparison and evaluation text areas. Control-Tab/Control-Shift-Tab switch tabs
  even when one of those text areas has focus. Progress updates never grab focus.

Existing detailed output, CLI options, public function call patterns, report
schemas, scoring and process-group cancellation remain available. There are no
new third-party dependencies. Explicit from-imports remain the convention.

## Progress transport

The desktop worker creates a unique temporary directory for each run, passes
its event-file path through a copied child environment, and removes it when
the worker finishes. The source CLI subprocess chain inherits that environment;
the private packaged worker receives it as well. No new CLI option is needed.

The evaluator emits small JSONL records for dataset validation, case start,
case completion, report saving and report saved. Human-readable stdout remains
unchanged. The desktop worker reads appended events alongside output and sends
them through the existing main-thread queue. Partial lines are retained and
invalid records are ignored. Case updates are validated for order/range and
duplicate completions do not advance the count.

The GUI does not parse generated responses or Result text to count progress.
Telemetry errors do not prevent scoring or report saving. Missing telemetry
leaves totals unavailable rather than fabricating them. The channel is an
internal reliability mechanism, not a security boundary against local code.
Elapsed time indicates how long the run has been active; it does not prove the
model is healthy or guarantee it will finish.

## Executed tests

- **566 passed in 2.06 seconds**, Linux/Python 3.12.14, including 34 new cases.
- All 532 preceding tests remain present and pass.
- Real child-process tests cover progress through source evaluation and the
  private worker, with mocked HTTP and real report writing; no GUI is opened.
- Tests cover PASS/FAIL and HTTP/network/timeout/malformed-response errors,
  exact counts, invalid datasets, failed report writes, partial JSONL records,
  unavailable telemetry, separate output/progress queues and temporary cleanup.
- State/GUI tests cover silent waits, no fake progress from generated text,
  stopping, restart reset, terminal timing, thread-start failure and keyboard focus.
- Compilation and explicit-import/unused-import checks pass.

Tk widgets were mocked in GUI tests. Native layout, keyboard behavior and
VoiceOver require actual macOS validation. No real Ollama inference was run by
the agent for this checkpoint.

## Mac validation

1. Pull the branch and run the full suite with Python 3.12.12; expect 566 tests.
2. Launch `python3 app_entry.py`. Confirm status, bar, counts, timer, controls
   and output remain usable in the initial window and after resizing.
3. Run `eval-read-live.json` with `gemma3:1b` selected from the dropdown. Confirm
   a waiting message and advancing elapsed time during a quiet request. Cases
   should advance only when completed, with a final report/completion message.
4. Stop a running evaluation, then start another. Confirm stopping/cleanup is
   shown, a new run starts at zero, and its report is saved normally. Close the
   window both idle and during a run; check for tracebacks or leftover processes.
5. Use Tab/Shift-Tab to reach inputs, dropdown, actions and report controls.
   Confirm visible focus and that read-only output does not trap the keyboard.
   Use Control-Tab/Control-Shift-Tab to switch tabs from within text areas.
6. Enable VoiceOver in macOS Accessibility settings and attempt to identify
   fields, choose a model, start/stop, read status and access saved reports.
   Record exactly which elements are missing or confusing. Do not infer support
   merely from visual labels or successful keyboard operation.
7. If practical, quit Ollama and refresh/check, then reopen it and retry in the
   same window. Reports and Compare should remain usable throughout.

## Remaining accessibility work and research

Apple recommends consistent progress placement, accurate context and allowing
cancellation. Its accessibility guidance calls for testing real assistive
technologies and system settings. Python 3.12 supplies a determinate Progressbar
and keyboard traversal without extra runtime packages.

Next priorities are VoiceOver exposure, visible/logical keyboard focus, adjustable
text size and layout, contrast in light/dark appearances, and checks with increased
contrast/reduced-motion settings. These are test targets, not current support
claims. Findings may require more than visual changes; evaluate the actual
Tkinter runtime before deciding how to address gaps. Repeat the checks in the
eventual packaged app because its bundled GUI runtime may differ.

Sources:

- [Apple progress indicators](https://developer.apple.com/design/human-interface-guidelines/progress-indicators).
- [Apple accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility).
- [Apple accessibility testing](https://developer.apple.com/documentation/accessibility/performing-accessibility-testing-for-your-app).
- [Apple VoiceOver evaluation criteria](https://developer.apple.com/help/app-store-connect/manage-app-accessibility/voiceover-evaluation-criteria).
- [Python 3.12 ttk Progressbar and keyboard traversal](https://docs.python.org/3.12/library/tkinter.ttk.html).
