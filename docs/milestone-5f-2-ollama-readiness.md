# Milestone 5F-2: Ollama readiness and setup recovery

Status: readiness and model-selection checkpoints source-validated on macOS.
Service-unavailable recovery remains unverified manually. The subsequent progress
and keyboard checkpoint has its own pending Mac validation.
Branch: `feature/milestone-5f-macos-packaging`.
Implementation: [`57b466e`](https://github.com/brian419/trust-bench-python/commit/57b466e6d4c6d0f9c195af6ac04b4a66b484a11a).

## User behavior

The Evaluate tab includes an editable model dropdown, **Refresh Models**,
**Check Ollama**, **Setup Help** and **Get Ollama (website)**, plus a textual status.
Refresh Models and Check Ollama both populate the dropdown from the returned
model list. Exact spelling, namespaces and tags are preserved; duplicates are
removed and choices sorted. Neither action changes the selected/typed name or
starts inference. An empty field can refresh the list. Start still requires a
nonempty name and a fresh check. Evaluation actions share a compact button row.
All existing evaluation, report and comparison controls remain available.

No service request is made just by opening TrustBench. **Check Ollama** inspects
availability without inference. **Start Evaluation** validates the dataset and
model, performs a fresh background readiness check, and launches only after a
ready result for the unchanged settings.

| Status | Meaning and recovery |
| --- | --- |
| Not checked / checking | Choose Check Ollama or Start Evaluation; wait for the background result. |
| READY | The local service lists the requested model; an evaluation can start. |
| UNAVAILABLE | The local service could not be reached/read before a socket failure or timeout. Open Ollama if installed, or use Get Ollama to install it, then check again. This does not prove Ollama is uninstalled. |
| MODEL_MISSING | The service returned a valid model list without the selected model/tag. Download the model explicitly in Ollama or use the displayed ollama pull command, then check again. |
| CHECK_FAILED | An HTTP failure or unreadable model list prevents verification. Open/update Ollama and retry; do not infer that the model is missing. |
| MODELS_AVAILABLE | An empty-field discovery returned choices. Select one before starting. |
| NO_MODELS | Empty-field discovery returned no models. Download a model in Ollama and refresh. |
| INVALID_MODEL | Direct readiness calls require a nonempty name unless discovery is explicitly requested. GUI Start requires a nonempty name. |

**Get Ollama (website)** displays the full official HTTPS destination in a
confirmation before opening the browser. The same address is visible in the
Evaluate tab: `https://ollama.com/download/mac`. Cancel performs no navigation.
A browser failure shows the address for manual navigation. Setup Help directs
users to **Download manually** on the official website. This transparency is
not a guarantee about third-party software safety.
**Setup Help** explains the separate installation, choosing/downloading a local
model, the `gemma3:1b` default and optional terminal setup. Downloads require
internet and disk space. TrustBench does not install Ollama, start its service,
download models or execute the displayed setup commands automatically.

Reports and Compare remain usable without Ollama and while a check is pending.
A failed check leaves previous report displays intact. The user can retry after
fixing setup without restarting TrustBench.

## Request and lifecycle details

`ollama_readiness.py` sends one read-only GET to the same local service used by
inference: `http://localhost:11434/api/tags`. It uses a **2-second socket
timeout** and a **1 MiB response-size limit**. These are per-I/O safeguards,
not a hard total wall-clock deadline for a server that continually trickles data.

Model names are matched using the returned name/model fields. An omitted tag
is treated as `:latest`, including namespaced model names. Explicit tags such
as `gemma3:1b` are not treated as interchangeable with `:latest`. A listed
model does not guarantee that a later inference can load/run successfully;
existing evaluation HTTP/timeout/error reporting still applies.

HTTP and JSON work runs on a background daemon thread. Only queue events reach
the Tkinter thread. Results have request IDs and snapshots of settings; stale,
duplicate or changed-setting results cannot launch the wrong evaluation.
Each UI start uses a fresh check rather than trusting a cached READY status.

Checks cannot overlap active/unverified evaluations. The event poller avoids
duplicate callbacks when readiness transitions into evaluation. Closing while a
check is pending cancels its scheduled callback and ignores late results.
Unexpected check or thread-start failures restore controls for retry.

The existing source CLI, worker protocol, evaluator/scoring APIs, report fields,
process-group shutdown and source/packaged data paths are unchanged. The
existing `start_evaluation` callable remains the launch routine; the UI button
uses `check_and_start_evaluation` for its readiness step.

## Executed verification

- The starting branch passed **468 tests**.
- The full updated suite passed **520 tests in 1.91 seconds** on Linux with
  Python 3.12.14, including **52 new regression cases**.
- `python3 -m compileall -q .`, whitespace checks and the explicit-import audit
  across all 70 Python files passed. No dependencies were added.
- Backend tests cover model aliases, different tags, missing models, invalid
  input, connection/timeouts, HTTP failure, malformed/oversized replies, quoted
  setup hints and recovery from unavailable to missing to ready.
- GUI tests cover waiting before launch, failed checks/retry, check-only,
  startup without network requests, fresh checks for each start, stale settings,
  duplicate results, poll scheduling, thread failure, closing during a check,
  and explicit browser/help actions.
- A real background-thread test deliberately blocks the readiness call while
  actual report reading and comparison run successfully on the main thread.

HTTP responses were mocked. No actual local Ollama service, model download or
native GUI rendering was tested by the agent. The original Mac checkpoint is
recorded below; current progress/keyboard Mac validation is tracked separately. No app/DMG build, accessibility certification, release publication or
parent-branch merge is claimed by this checkpoint.

## Mac evidence and follow-up validation

The user ran the original checkpoint at `b637373` on macOS/Python 3.12.12:
**520 passed in 6.57 seconds**, clean working tree. Screenshots and reported
manual results confirm ready and missing-model messages, setup help, the
Ollama website, working Reports/Compare, command preview, real evaluation,
stop/restart and normal closure without traceback. The live run saved
`evaluation-fd508abe494642ce8c2ab10fb322f777.json` with 2 PASS, 0 FAIL and
0 request errors. Service-unavailable recovery and closing during a pending
check were not reported as manually tested.

The user subsequently passed **532 tests in 6.18 seconds** on macOS/Python
3.12.12 and manually verified dropdown refresh (including an empty field),
selection without typing, preview, evaluation, stop/restart and fitting controls.
Screenshots confirm the visible external-link confirmation. Cancellation of that
dialog and service-unavailable recovery were not explicitly reported.
See the [next progress/keyboard checkpoint](milestone-5f-progress-accessibility.md)
for the current 566-test suite and pending Mac checks.

The user identified model-name typing and external-link trust as usability
issues. The follow-up adds dropdown discovery and explicit website destination
information. The agent ran **532 tests in 1.76 seconds** on Linux/Python 3.12.14,
including 12 additional cases for exact model names, discovery with an empty
field, empty lists, failed/stale refreshes, selection preservation, cancellation
and browser failure. No project dependencies were added.

Setup checks to retain for packaged-app validation:

1. Pull the branch, run the full suite with Python 3.12.12; expect 566 tests with the progress checkpoint.
2. Launch `python3 app_entry.py`. Choose Refresh Models, then select
   `gemma3:1b` from the dropdown without typing its name. Preview/start and
   confirm normal report saving. Check controls still fit the window.
3. Clear the field and refresh: choices should still appear without selecting
   or running a model automatically. Type a missing model, refresh/check and
   confirm available choices remain selectable and Start blocks the missing one.
4. Open Get Ollama (website): confirm the full HTTPS address is shown. Cancel
   must leave the browser alone; accepting opens the official site. Check that
   Setup Help explains Download manually and dropdown selection.
5. If practical, quit Ollama and refresh. Expect an unavailable message and
   cleared choices while Reports/Compare remain usable. Reopen and retry in
   the same window. An independently running Ollama service can still respond.
6. Confirm stop/restart and normal closure; if practical, close during a check
   and confirm no traceback.

After validation, continue to **5F-3: macOS app and DMG build**.

## Official references

- [List models API](https://docs.ollama.com/api/tags).
- [macOS setup](https://docs.ollama.com/macos).
- [CLI reference](https://docs.ollama.com/cli).
- [Local-model quickstart](https://docs.ollama.com/quickstart).
