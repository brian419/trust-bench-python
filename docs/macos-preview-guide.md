# TrustBench for macOS

TrustBench provides a desktop interface for running local AI evaluations,
viewing saved reports and comparing evaluation results.

## Preview requirements

- Intel Mac running macOS 15.7.9, the configuration used for validation.
- Ollama and a downloaded local model for live evaluations.

The app includes Python, Tcl/Tk and example datasets. Python and Git do not need
to be installed separately. Reports and Compare work without Ollama.

Other macOS versions and Apple Silicon have not been verified. A public download
is not yet available; see the [build guide](milestone-5f-3-macos-build.md) to
create a local candidate.

## Installation

1. Open the TrustBench DMG.
2. Drag **TrustBench.app** into **Applications**.
3. Eject the disk image and launch TrustBench from Applications.

The preview is ad-hoc signed and is not signed with Apple Developer ID or
notarized. macOS may display a security warning when opening a downloaded copy.
See [Apple's guidance on opening apps safely](https://support.apple.com/102445).

## Run an evaluation

1. Open Ollama and ensure a local model is installed.
2. In TrustBench, select **Evaluate**, then **Refresh Models**.
3. Choose a model, such as `gemma3:1b`, and a dataset.
4. Select **Start Evaluation**. Progress and output appear in the window.

**Setup Help** explains Ollama setup. **Check Ollama** checks the selected model,
and **Stop Evaluation** ends a running evaluation. Ollama and models are
installed separately.

## Saved reports

Reports are stored in:

```text
~/Library/Application Support/TrustBench/reports
```

Use **Reports** to view an evaluation and **Compare** to compare two saved
evaluations. An empty report list is normal before the first completed run.

Reports created from the source checkout stay in its `reports/` directory.
**Open Evaluation Report** can view a file elsewhere. To include older reports
in the Reports and Compare lists, copy their evaluation JSON files into the
application's report directory.

Reports may contain prompts, expected and generated answers, model names,
dataset paths and timestamps. Review their contents before sharing them.
Live prompts are sent to the local Ollama service at `localhost:11434`.

## Keyboard and spoken guidance

Use Tab/Shift-Tab to move between controls. Arrow keys browse reports and
dropdown choices; Enter/Return confirms a selection. **Keyboard Help** lists
shortcuts for each workflow.

Optional **Spoken guidance** reads controls, choices and evaluation status.
It is off at startup and is separate from macOS VoiceOver.

## Update or uninstall

Quit TrustBench before replacing the app in Applications. Saved reports remain
in the separate report directory; back up important reports before updating.

To uninstall, move TrustBench.app to Trash. Reports remain available until
their data folder is removed separately.

## Report a problem

Include the app version/build from Finder Get Info, your macOS version, the
action attempted and the error message. Check logs and reports for private data
before attaching them to an issue.

[Source code and issues](https://github.com/brian419/trust-bench-python)
