# Navigation and optional spoken guidance checkpoint

Branch: `feature/milestone-5f-macos-packaging`.
Status: implemented and agent-tested; native Mac validation pending.

## Starting evidence

The user passed **577 tests in 8.52 and 7.79 seconds** on macOS/Python 3.12.12
at `7e1efb5`. Progress, elapsed time, stop/restart reset, resizing and normal
closure had already been manually verified. New feedback identified confusing
list instructions, hard-to-discover tab switching, Enter/Return terminology,
focus loss after alerts and a request for app-controlled optional speech.

## Navigation changes

- Saved reports remain one Tab stop. Persistent text and the focus hint explain
  Up/Down Arrow selection/scrolling, Enter/Return to open, and Tab to leave.
- Direct shortcuts are visible: Command+1 Reports, Command+2 Compare and
  Command+3 Evaluate on macOS; Control+1/2/3 on other platforms. Control+Tab
  and Control+Shift+Tab cycle workflows without traversing all their controls.
- Selecting a workflow focuses its list/first field after mapping. A generation
  check prevents rapid tab changes from applying stale focus callbacks.
- F1 or Keyboard Help explains navigation and speech controls.
- Dropdown hints consistently say Down Arrow opens, arrows move, Enter/Return
  confirms and Escape cancels. Native popup behavior is preserved. Space can
  still open readonly report choices, but Enter/Return confirms the choice;
  Space remains ordinary typing in the editable model field.
- Main keyboard Return and keypad Enter have equivalent app bindings. Space
  still activates buttons. Existing enabled/disabled guards remain in place.
- Every application dialog goes through one helper: errors, warnings, help,
  external-site confirmation and file selection. The main window is its parent.
  On dismissal, application focus is restored to the originating usable control,
  or to the selected workflow's entry control if the origin is hidden/disabled.
  No force-focus or delayed foreground stealing is used.

The speech controls and clearer hints need additional room. The initial window
height is capped against screen height and the minimum height is 680 pixels;
check the layout on the target Mac. Existing detailed output remains available.

## Optional spoken guidance

The Spoken guidance checkbox is off at every launch. It uses macOS's installed
`/usr/bin/say` and needs no system VoiceOver setting change. It speaks focused
control hints, selected report/model names, dialog messages and evaluation status
changes. It does not read every elapsed-time tick. Read current view explicitly
reads up to 3600 characters of visible report/comparison/output text with an
excerpt notice when longer. Merely opening a report does not read its contents
aloud. Speech may be audible to nearby people when enabled.

The visual interface remains complete with speech off. This feature is app
speech guidance, not Apple's VoiceOver, and does not provide a full accessibility
tree, screen-reader navigation or proven general screen-reader compatibility.
It complements, rather than replaces, native accessibility testing.

No paid service, audio recording, microphone permission or third-party package
is introduced. The app requests no model/voice installation and does not change
system sound preferences. On unsupported systems, enabling the option reports
that local macOS speech is unavailable; visual/keyboard operation continues.

Speech uses a dedicated background worker, never Tk calls from that worker.
Text is sent through stdin to a fixed executable/argument list, without a shell.
Announcements are bounded at 4000 characters. Focus announcements are debounced
250 ms; only the newest pending request is retained and newer speech interrupts
older speech. Generation IDs discard stale requests. Disable and window closure
cancel GUI timers, discard pending text and terminate only the owned speech
process; the worker reaps it. Process/worker failures switch speech off without
affecting evaluation, and a main-thread check explains the failure visually.

## Executed verification

The full suite passed **606 tests** on Linux/Python 3.12.14, including **29 new
regression cases**, with the previous 577 tests retained. Compilation, explicit
imports, import usage/order and changed-line whitespace were checked.

Tests cover direct tab entry for all workflows, stale/closed tab callbacks,
parent/focus restoration for dialog kinds and failures, missing-origin fallback,
dismissed comparison warnings, terminology/help, speech off by default,
debouncing, immediate dialog speech, disable/close cleanup, failure recovery,
bounded view reading for every tab and suppression of repeated timer narration.

Backend tests run real worker threads with mocked speech subprocesses, verify
fixed executable/stdin input, interrupt/reap behavior, failure handling and
latest-only queue bounds. GUI tests use mocked Tk widgets. Linux has no actual
macOS speech backend; no audible-speech or native-Aqua validation is claimed.

## Mac validation checklist

1. Pull this branch; run the full suite with Python 3.12.12; expect 606 tests.
2. Launch `python3 app_entry.py`. Speech must be off and silent. Check layout
   and resizing with the new global controls and keyboard tips.
3. Use Command+1/2/3 from lists, fields, buttons and output text. Each should
   jump directly to its workflow. Control+Tab/Control+Shift+Tab should cycle.
4. In Reports, Tab reaches the list once. Use Up/Down Arrow to choose and scroll,
   Enter/Return to open, and Tab to leave. Read the onscreen instructions.
5. In Compare/Evaluate, Down Arrow or Enter/Return opens each dropdown, arrows
   move, Enter/Return selects, Escape cancels. Check keypad Enter if available.
6. Trigger missing-selection warnings in Compare and invalid-setting errors in
   Evaluate. Dismiss with Enter/Return, then immediately Tab/Shift-Tab and verify
   focus stays usable. Also cancel file pickers, close help and cancel the
   external-site confirmation. Check the same behavior across all workflows.
7. Enable Spoken guidance using its checkbox. Confirm focus hints, chosen model
   or report names, errors and changed evaluation status are spoken. Move quickly
   through controls: old speech should be replaced, not accumulate.
8. Use Read current view on each workflow. Confirm it reads the displayed text
   or an explicitly identified excerpt. Turn speech off during reading and
   confirm it stops; it must stay silent as you continue using the app.
9. Re-enable speech, start/stop/restart an evaluation, and close the window while
   speaking. Confirm no continued speech, traceback or evaluation process is left
   behind. Relaunch and confirm speech is off again.

System VoiceOver testing remains separate and unfinished. Repeat keyboard,
dialog and audible-speech checks in the eventual packaged app before release.
No app/DMG build, merge or public release is included in this checkpoint.

## References

- [Apple speech synthesis](https://developer.apple.com/documentation/avfoundation/speech-synthesis).
- [Apple speech complementing assistive technologies](https://developer.apple.com/videos/play/wwdc2020/10022/).
- [Apple keyboard navigation](https://support.apple.com/guide/mac-help/use-full-keyboard-access-mchlc06d1059/mac).
- [Tk combobox bindings](https://github.com/tcltk/tk/blob/core-8-6-branch/library/ttk/combobox.tcl).
