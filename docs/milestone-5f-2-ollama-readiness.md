# Milestone 5F-2: Ollama readiness and setup recovery

Status: implemented and agent-tested; Mac validation pending.
Branch: `feature/milestone-5f-macos-packaging`.
Implementation: [`57b466e`](https://github.com/brian419/trust-bench-python/commit/57b466e6d4c6d0f9c195af6ac04b4a66b484a11a).

## User behavior

The Evaluate tab now includes **Check Ollama**, **Setup Help** and **Get Ollama**,
plus a textual readiness status. Evaluation actions share a compact button row.
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
| INVALID_MODEL | Enter a nonempty model name before checking. |

**Get Ollama** opens the official macOS download page only when clicked.
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
native GUI rendering was tested by the agent. Mac manual validation remains
required. No app/DMG build, accessibility certification, release publication or
parent-branch merge is claimed by this checkpoint.

## Mac validation checklist

1. Pull this branch and run the full suite using Python 3.12.12; expect 520 tests.
2. Launch `python3 app_entry.py`. Confirm existing reports can be viewed and
   compared before any check, and the new controls fit the window.
3. With Ollama running and `gemma3:1b` present, choose **Check Ollama** and
   confirm ready status. It must not start inference.
4. Enter a deliberately nonexistent model such as
   `trustbench-readiness-missing:latest`, check it and confirm a missing-model
   message. Start Evaluation must not launch inference for that model.
5. Restore `gemma3:1b`, check/start again and complete a real evaluation.
   Confirm stop/restart and report saving still work.
6. If practical, quit the Ollama service/app and check again. Expect an
   unavailable-service message while report browsing/comparison still work.
   Reopen Ollama and retry in the same TrustBench window. No uninstall or model
   deletion is needed. If another Ollama server remains running, a successful
   check is expected.
7. Open Setup Help; optionally check that Get Ollama opens the official page
   without installing anything. Close TrustBench normally and, if possible,
   during a pending check; confirm no traceback or late window appears.

After this validation, continue to **5F-3: macOS app and DMG build**.

## Official references

- [List models API](https://docs.ollama.com/api/tags).
- [macOS setup](https://docs.ollama.com/macos).
- [CLI reference](https://docs.ollama.com/cli).
- [Local-model quickstart](https://docs.ollama.com/quickstart).
