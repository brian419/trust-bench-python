# Speech focus, choice narration and model discovery

Branch: `feature/milestone-5f-macos-packaging`.
Status: implemented and agent-tested; native Mac validation pending.

The user passed **620 tests in 8.23 seconds** with macOS/Python 3.12.12 at
`99cf924`. F6 and Command+Shift+S worked, and speech was audible. Remaining
feedback concerned subtle checkbox focus, repeated "Keyboard focus" speech,
silent highlighted report choices and an empty model list on a fresh launch.
The previous turn was interrupted before implementation; these changes are the
completed follow-up.

## Behavior

The speech checkbox has a separate 3-pixel blue frame while focused and explicitly
says `Spoken guidance: Off [focused]` or `On [focused]`. Focus loss restores its
normal frame and label. A BooleanVar trace keeps its On/Off text in sync with
keyboard toggles and speech failure recovery. Moving focus does not change the
enabled state. The option still starts off at each launch.

Visual keyboard hints retain detailed instructions. Speech uses only the short
control name, state or selected value. It does not repeat "Keyboard focus" or
button-use instructions on every Tab press. Help remains available for instructions.

The prior ComboboxSelected handler only announced confirmed choices. With speech
enabled, opening any of the previous/current report or model selectors now uses
an app-owned choice window with an observable Listbox. Highlight changes announce
the item number and value while browsing, before changing the original field.
Quick navigation retains the newest announcement using existing speech debouncing.
Arrow keys and pointer movement browse. Enter/Return, keypad Enter or Space
confirms; Escape, clicking outside or closing the window cancels. The original
field changes only on confirmation, with a normal ComboboxSelected event.
If the available list changed meanwhile, confirmation resolves the chosen value
against the current list; a removed value is rejected instead of selecting a
different report at the same index. Late events after closure are ignored.

The choice window uses a local grab, restores focus and cleans up its pending
focus callback on closure. Tab/Shift-Tab leave it. F6, help, workflow shortcuts
and the speech toggle remain available inside the chooser. Disabling speech,
backend failure or closing TrustBench closes it. Native dropdown behavior remains
in use when speech is off. This is app speech support, not certification of
VoiceOver or general screen-reader accessibility.

The screenshot of an empty model list showed the initial instruction to refresh;
there had not yet been a service check in that app session. Model choices were
not persisted across launches. The app now requests the local model list in a
background thread on the first Evaluate visit. Opening an empty model selector
also triggers a refresh, including retry after an earlier empty list. Duplicate
pending checks are suppressed. Completed checks populate the existing selector,
preserve the current model name and never start evaluation unless the user
separately requested Start Evaluation. Reports-only startup still makes no
service request. The manual Refresh Models action remains available.

No model installation, model download, paid service or new dependency is added.
Scoring, CLI behavior, report schemas, cancellation and process cleanup are unchanged.

## Executed verification

**643 tests passed** on Linux/Python 3.12.14, including **23 new cases**; the
previous 620 tests remain present. New coverage includes focus frame/state,
concise narration, explicit selected values, first-Evaluate discovery, pending
check suppression, empty-list refresh, selection preservation, all three spoken
selectors, native speech-off behavior, highlighted versus committed values,
confirm/cancel/cleanup, reordered or removed options and late events.

GUI widgets and Ollama replies were mocked. No native Mac chooser rendering,
actual model discovery or audible speech was tested by the agent. Mac checks:

1. Pull and run the full suite with Python 3.12.12; expect 643 tests.
2. Launch `python3 app_entry.py`. Press F6 (or Fn-F6), confirm a visible frame
   and focused Off label; toggle speech and confirm the label changes to On.
3. Tab through controls with speech on. It should read concise names/values
   without the "Keyboard focus" prefix or repeated activation instructions.
4. Open Previous report and Current report. Pause briefly on each arrow-key
   highlight and confirm its name is spoken before committing. Try Enter/Return,
   Space and Escape; verify cancellation preserves the previous selection.
5. On a fresh launch, open Evaluate with Ollama running. Wait for its background
   check, then confirm installed model choices appear without clicking Refresh
   Models. Confirm Refresh Models and manual model entry still work.
6. Check unavailable-service messaging and retry if practical. Recheck evaluation,
   stop/restart, report viewing/comparison, speech disable and normal closure.

No merge, app/DMG build or release is part of this checkpoint.
