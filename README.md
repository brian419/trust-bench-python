# TrustBench

**A Python-based learning project for reproducible AI response evaluation and reliability testing.**

TrustBench is an early-stage evaluation tool designed to grow from basic answer comparisons into a framework for investigating the correctness, consistency, and failure modes of AI-generated responses.

The command-line project supports both **offline evaluation of prerecorded JSON responses** and **live evaluation of a local language model through Ollama**. Development is incremental, emphasizing testable Python code and transparent measurement.

## Current status

**Milestones 1, 2, and 3: Complete (47 automated tests)**

Milestone 3 was merged into the default `main` branch on October 21, 2026. The instructions below work directly from a fresh clone of `main`; Milestones 4 and 5 are planned, not yet implemented.

Implemented:

- Run the original offline evaluator (`eval.py`) on prerecorded responses, including an optional dataset path.
- Run `eval_live.py` against a local Ollama model (`gemma3:1b`) using Python's standard-library HTTP client.
- Validate offline and live datasets before evaluation; the live dataset does not require a prerecorded `response` field.
- Compare answers using case-insensitive, leading/trailing-whitespace-normalized exact matching.
- Record per-case `PASS`, `FAIL`, or `ERROR`, distinguishing model/API failures from incorrect answers.
- Handle HTTP, connection, and timeout failures without counting them as scored failures; report `Accuracy: N/A` if no responses were scored.
- Capture UTC run timestamps, model and dataset names, raw generated responses, and per-request elapsed seconds.
- Save a structured JSON report for each live run to `reports/evaluation-<unique-id>.json` without overwriting previous reports.
- Handle invalid input and report-save failures with clear errors; test the evaluator and mocked model client with `pytest`.

**Scoring limitation:** “Accuracy” means *normalized exact-match rate among successfully scored responses in the provided dataset*. It is not a general measure of model accuracy, semantic equivalence, factuality, hallucinations, bias, safety, or reliability. Model request errors are counted separately and excluded from the accuracy denominator.

## Requirements

- Python 3 (developed with Python 3.12.3)
- No third-party Python runtime dependencies. `pytest` is needed only to run tests.
- For **live** evaluation only: [Ollama](https://ollama.com/) running locally with the `gemma3:1b` model available. This workflow does not require paid API access or an API key.

## Getting started

Clone the repository and enter the project directory:

```bash
git clone https://github.com/brian419/trust-bench-python.git
cd trust-bench-python
```

The repository includes `eval-read-valid.json`, which is used by default. Its contents are:

```json
[
  {
    "id": "test_001",
    "question": "What is the capital of France?",
    "expected": "Paris",
    "response": "  PARIS  "
  },
  {
    "id": "test_002",
    "question": "What is 15 multiplied by 4?",
    "expected": "60",
    "response": "45"
  },
  {
    "id": "test_003",
    "question": "What is the capital of Japan?",
    "expected": "Tokyo",
    "response": "tokyo"
  }
]
```

Run the evaluator from the project root (using the included default dataset):

```bash
python3 eval.py
```

Expected output:

```text
Test ID: test_001 ; PASS: The answers match!
Test ID: test_002 ; FAIL: The answers don't match!
Test ID: test_003 ; PASS: The answers match!
Passed 2 tests
Failed 1 test
Accuracy: 66.67
```

An empty but valid JSON list (`[]`) produces:

```text
Passed 0 tests
Failed 0 tests
Accuracy: N/A
```

A completely blank or malformed JSON file is rejected with a readable error message and nonzero exit status rather than an unhandled traceback. Invalid dataset structures are rejected before scoring.

To evaluate another dataset, supply its path:

```bash
python3 eval.py path/to/dataset.json
```

The repository includes two intentional failure examples:

- `eval-read-invalid.json`: valid JSON with invalid test-case structure.
- `eval-read-malformed.json`: invalid JSON syntax.

You can try them with `python3 eval.py <filename>` to inspect the errors. These commands intentionally exit with status 1.

### Running the automated tests

Install the development test dependency in your Python environment:

```bash
python3 -m pip install pytest
python3 -m pytest -v
```

The current suite contains **47 tests**, including offline CLI tests, mocked Ollama requests, error-handling tests, request-timing regression tests, and JSON report persistence tests. Model calls are mocked in the automated tests, so no Ollama server is needed to run them.

## Offline input format

`eval.py` expects a JSON array of test-case objects containing the following required **string** fields:

| Field | Meaning |
| --- | --- |
| `id` | Identifier shown in the evaluation output |
| `question` | Prompt or question stored as context in offline evaluation |
| `expected` | Reference answer |
| `response` | Recorded response being evaluated |

The evaluator compares `expected` and `response` after applying Python's `lower()` and `strip()` string methods to both values. As a result, `"Paris"` matches `"  PARIS  "`, but `"Paris"` does not match `"The capital is Paris."`.

## Live evaluation with Ollama (Milestone 3)

Live evaluation makes HTTP requests to a locally running model. It does not use a paid hosted AI API.

1. Install [Ollama](https://ollama.com/) for your operating system and start its local service.
2. Download the model once (this download requires internet access):

   ```bash
   ollama pull gemma3:1b
   ```

3. From the repository root, run:

   ```bash
   python3 eval_live.py
   ```

The client sends non-streaming requests to `http://localhost:11434/api/generate` using the model name `gemma3:1b`. The current script uses the fixed dataset file `eval-read-live.json` and fixed model name in its source; **live model selection and arbitrary dataset paths are not yet CLI options**. Ollama runs the model locally, but model download and local execution still consume bandwidth, disk space, and computer resources.

### Live dataset format

The live dataset is a JSON array with string fields `id`, `question`, and `expected`. Unlike offline fixtures, live cases **do not need `response`**: the model supplies its answer during the run.

```json
[
  {
    "id": "test_001",
    "question": "What is the capital of France? Answer with only the English city name.",
    "expected": "Paris"
  },
  {
    "id": "test_002",
    "question": "What is 6 multiplied by 2? Answer with only the number.",
    "expected": "12"
  }
]
```

Each generated answer is compared to `expected` using the same `lower().strip()` comparison as offline mode. For example, `" Paris"` matches `"Paris"`, but a longer explanatory sentence usually does not.

### Live results and JSON reports

Each live run prints per-case results and writes **one new** report under `reports/`. The folder is excluded from Git using `.gitignore`; reports stay local unless you explicitly share them.

A report includes:

- `metadata`: model name, dataset filename, and UTC ISO 8601 run timestamp.
- `summary`: counts of passed, failed, and errored requests, plus `accuracy` (a percentage, or JSON `null` if no requests were scored).
- `results`: test ID, question, expected answer, generated response, status, and `duration_seconds`; error cases contain `generated: null` and an `error` message.

A `PASS` or `FAIL` counts toward the accuracy denominator; an `ERROR` (HTTP, connection, or timeout failure) does not. An evaluation with no scored answers reports `Accuracy: N/A`. Request durations measure elapsed time for each model request, not total CLI runtime. Output can vary between runs even for the same prompts.

Report filenames use unique identifiers, so earlier reports are preserved. A directory/file-system problem while saving produces an error message and exits with code 1. The current implementation does not compare reports across runs or track all model configuration parameters or dataset revisions; those are future improvements.

## Development roadmap

- **Milestone 1: Basic evaluation (complete).** Read prerecorded answers from JSON, normalize and score them.
- **Milestone 2: Testable architecture (complete).** Reusable functions, pytest tests, dataset validation, and controlled CLI errors.
- **Milestone 3: Local model integration (complete).** Ollama HTTP inference, live scoring, request failure handling, elapsed-time tracking, and saved JSON run reports.
- **Milestone 4: Responsible AI evaluation methods (planned).** Explore factual grounding, consistency, controlled prompt-injection scenarios, and cases requiring human review.
- **Milestone 5: Advanced reproducibility and comparisons (planned).** Build on the basic JSON reporting from Milestone 3 to compare runs, record more configuration/version metadata, and produce cautious aggregate analyses.

See [`milestones.md`](milestones.md) for detailed status and acceptance evidence.

## Evaluation principles

TrustBench aims to prioritize:

- **Transparent scoring:** Make explicit what each metric measures and what it does not.
- **Reproducible experiments:** Preserve test cases and document evaluation conditions.
- **Failure analysis:** Investigate incorrect or inconsistent outputs instead of reporting a single score without context.
- **Honest limitations:** Avoid treating simple answer matching as evidence of general AI safety or reliability.

## Project context

This is an independently developed learning and portfolio project focused on strengthening Python engineering, automated testing, and AI evaluation skills. The initial implementation is intentionally small so that each component can be understood, tested, and improved before expanding the scope.
