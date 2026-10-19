# TrustBench

**A Python-based learning project for reproducible AI response evaluation and reliability testing.**

TrustBench is an early-stage evaluation tool designed to grow from basic answer comparisons into a framework for investigating the correctness, consistency, and failure modes of AI-generated responses.

The current implementation is a command-line prototype. It evaluates **pre-recorded responses stored in JSON**, rather than calling an AI model directly. The project is being built incrementally to explore software testing practices and, eventually, more rigorous approaches to evaluating AI systems.

## Current status

**Milestone 1: Complete** | **Milestone 2: Complete (27 automated tests)**

Implemented:

- Load a list of test cases from a local JSON file.
- Compare expected and recorded responses using case-insensitive matching with leading and trailing whitespace removed.
- Report a pass or fail result for each test case, identified by its ID.
- Count passing and failing test cases.
- Calculate the percentage of tests passed, rounded to two decimal places.
- Report `Accuracy: N/A` when the JSON list contains no test cases.
- Use reusable `compare_answers`, `calculate_accuracy`, and `validate_dataset` functions.
- Validate that the JSON input is a list of objects with string fields `id`, `question`, `expected`, and `response`.
- Report all dataset validation errors before scoring; exit with status 1 for invalid input, missing files, or malformed JSON.
- Accept an optional dataset filename as a command-line argument.
- Run 27 automated unit and CLI integration tests with `pytest`.

**Scope limitation:** The current score measures *normalized exact-match accuracy* on the supplied dataset. It does not assess semantic equivalence, factual correctness of open-ended answers, hallucination rates, bias, safety, or model performance in general.

## Requirements

- Python 3 (developed with Python 3.12.3)
- No third-party runtime dependencies; `pytest` is required only for running the automated tests.

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

The current suite contains **27 tests**, including CLI integration tests that create their own temporary input files.

## Input format

The program expects a JSON array of test-case objects containing the following required **string** fields:

| Field | Meaning |
| --- | --- |
| `id` | Identifier shown in the evaluation output |
| `question` | Prompt or question associated with the test (stored for context; not currently evaluated) |
| `expected` | Reference answer |
| `response` | Recorded response being evaluated |

The evaluator compares `expected` and `response` after applying Python's `lower()` and `strip()` string methods to both values. As a result, `"Paris"` matches `"  PARIS  "`, but `"Paris"` does not match `"The capital is Paris."`.

## Development roadmap

Milestone 2 is implemented. The remaining milestones are planned:

- **Milestone 2: Testable architecture (complete).** Reusable functions, `pytest` coverage, dataset validation, and controlled CLI errors.
- **Milestone 3: Model integration.** Add a configurable interface to run tests against an actual language model while recording responses and execution details.
- **Milestone 4: Evaluation methods.** Explore more rigorous assessments of factual grounding, answer consistency, and controlled prompt-injection scenarios, including cases requiring human review.
- **Milestone 5: Reproducibility and reporting.** Compare evaluation runs and generate structured reports with methods, outcomes, and limitations.

The scope of later milestones may change as the project develops.

## Evaluation principles

TrustBench aims to prioritize:

- **Transparent scoring:** Make explicit what each metric measures and what it does not.
- **Reproducible experiments:** Preserve test cases and document evaluation conditions.
- **Failure analysis:** Investigate incorrect or inconsistent outputs instead of reporting a single score without context.
- **Honest limitations:** Avoid treating simple answer matching as evidence of general AI safety or reliability.

## Project context

This is an independently developed learning and portfolio project focused on strengthening Python engineering, automated testing, and AI evaluation skills. The initial implementation is intentionally small so that each component can be understood, tested, and improved before expanding the scope.
