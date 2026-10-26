# TrustBench

**Local AI response evaluation and reliability testing in Python.**

TrustBench is a desktop and command-line project for testing language-model responses against defined expectations, examining failures, and comparing evaluation runs. It combines offline scoring with local model inference through [Ollama](https://ollama.com/), without requiring a paid API.

The project focuses on transparent scoring, reproducible inputs, and useful failure analysis rather than a single broad claim about model quality.

## What it does

- **Evaluate responses:** Score saved answers or generate responses from a locally running Ollama model.
- **Review results:** Separate correct matches, mismatches, and model request errors; inspect generated answers and timing.
- **Compare runs:** Compare saved live-evaluation reports by case ID, with input/scoring compatibility checks and metadata warnings.
- **Investigate behavior:** Run small reference-based, accepted-answer, repeated-response, and controlled prompt-injection experiments.
- **Use a desktop interface:** Browse reports, compare runs, and launch live evaluations with progress, keyboard navigation, and optional spoken guidance.

TrustBench uses normalized exact matching (case-insensitive, ignoring surrounding whitespace) as its baseline. Curated accepted alternatives and human review are separate from that baseline.

## Desktop app

The **0.5.0 preview** provides a native Tkinter application with three workflows:

| Tab | What you can do |
| --- | --- |
| **Reports** | Browse saved evaluations or open a report from another location |
| **Compare** | Compare two compatible saved live-evaluation reports |
| **Evaluate** | Select a dataset and local Ollama model, run an evaluation, and view progress and output |

The Intel macOS preview was built and manually tested on **macOS 15.7.9** with Python **3.12.12**. Testing included installation, report viewing, comparisons, model discovery, and a successful two-case live evaluation. Apple Silicon and other operating systems have not been manually validated. **No public installer is currently published.**

For requirements, installation, report locations, and accessibility controls, see the [macOS preview guide](docs/macos-preview-guide.md). Developers can follow the [macOS build instructions](docs/milestone-5f-3-macos-build.md).

The preview is ad-hoc signed, not Apple Developer ID signed or notarized.

## Get started from source

**Requirements:** Python 3.12; Tcl/Tk support for the desktop GUI. [Ollama](https://ollama.com/) and a downloaded model are needed only for live inference. Offline scoring, saved-report inspection, and automated tests do not require Ollama.

```bash
git clone https://github.com/brian419/trust-bench-python.git
cd trust-bench-python
```

Run the desktop interface:

```bash
python3 desktop_gui.py
```

Or use the unified CLI:

```bash
python3 trustbench.py --help
python3 trustbench.py offline
python3 trustbench.py scorers
```

To evaluate a local model, start Ollama and download a model:

```bash
ollama pull gemma3:1b
python3 trustbench.py live --model gemma3:1b --dataset eval-read-live.json
```

Additional CLI experiments:

```bash
python3 trustbench.py consistency
python3 trustbench.py injection
```

Live, consistency, and injection workflows use local Ollama. Evaluation reports are saved as JSON; source-run reports are written to the Git-ignored `reports/` directory. The installed macOS app uses `~/Library/Application Support/TrustBench/reports`.

## Reports and scoring

Each live evaluation records the dataset and model, timestamp, per-case expected and generated answers, status, and request duration. Results distinguish:

- **PASS:** Response matches the expected answer under the configured scoring rule.
- **FAIL:** Response does not match the expected answer.
- **ERROR:** Model request failed; it is counted separately from scored responses.

For the default live scorer, **accuracy means normalized exact-match percentage among successfully scored responses**. An equivalent paraphrase can fail; a high score on a small dataset does not demonstrate general factuality, safety, fairness, or robustness.

Saved-run comparison reports improvements, regressions, recovered requests, and new errors when the underlying reports can be compared. Compatibility warnings identify missing or differing metadata; recorded hashes and options do not guarantee identical model behavior.

Reference URLs and human labels are curated evidence, not automatic fact verification. Prompt-injection experiments are small, synthetic single-prompt tests—not security-boundary validation or a comprehensive robustness benchmark.

## Development and verification

The project uses Python's standard library for runtime functionality, `pytest` for automated tests, and [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q
ruff check .
ruff format --check .
```

**Verified on October 26, 2026:** 724 automated tests passing, Ruff lint and formatting checks passing, and an Intel macOS app/DMG build with a successful local Ollama smoke test. The tested live evaluation completed 2/2 cases without request errors; that is a smoke test, not a model-performance benchmark.

## Project documentation

- [macOS preview guide](docs/macos-preview-guide.md) — install, evaluate, manage reports, and keyboard controls
- [Development milestones](milestones.md) — design decisions, experiments, and validation history
- [macOS build guide](docs/milestone-5f-3-macos-build.md) — local packaging procedure
- [Preview release notes](docs/releases/0.5.0-preview.md) — preview scope and distribution status

TrustBench is an independent software engineering and AI evaluation portfolio project. It is a local research and testing tool, not a certified AI safety or production monitoring platform.
