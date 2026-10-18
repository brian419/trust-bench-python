# TrustBench

**A Python-based learning project for reproducible AI response evaluation and reliability testing.**

TrustBench is an early-stage evaluation tool designed to grow from basic answer comparisons into a framework for investigating the correctness, consistency, and failure modes of AI-generated responses.

The current implementation is a command-line prototype. It evaluates **pre-recorded responses stored in JSON**, rather than calling an AI model directly. The project is being built incrementally to explore software testing practices and, eventually, more rigorous approaches to evaluating AI systems.

## Current status

**Milestone 1: Complete** | **Milestone 2: Planned**

Implemented:

- Load a list of test cases from a local JSON file.
- Compare expected and recorded responses using case-insensitive matching with leading and trailing whitespace removed.
- Report a pass or fail result for each test case, identified by its ID.
- Count passing and failing test cases.
- Calculate the percentage of tests passed, rounded to two decimal places.
- Report `Accuracy: N/A` when the JSON list contains no test cases.

**Scope limitation:** The current score measures *normalized exact-match accuracy* on the supplied dataset. It does not assess semantic equivalence, factual correctness of open-ended answers, hallucination rates, bias, safety, or model performance in general.

## Requirements

- Python 3 (developed with Python 3.12.3)
- No external Python dependencies for Milestone 1

## Getting started

Clone the repository and enter the project directory:

```bash
git clone https://github.com/brian419/trust-bench-python.git
cd trust-bench-python
```

Create an `eval-read.json` file in the project root if one is not already present:

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

Run the evaluator from the project root:

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

> **Note:** A completely blank file is not valid JSON and currently raises a `JSONDecodeError`. Input validation and clearer error messages are planned improvements.

## Input format

The program currently expects `eval-read.json` to contain a JSON array of test case objects with these fields:

| Field | Meaning |
| --- | --- |
| `id` | Identifier shown in the evaluation output |
| `question` | Prompt or question associated with the test (stored for context; not currently evaluated) |
| `expected` | Reference answer |
| `response` | Recorded response being evaluated |

The evaluator compares `expected` and `response` after applying Python's `lower()` and `strip()` string methods to both values. As a result, `"Paris"` matches `"  PARIS  "`, but `"Paris"` does not match `"The capital is Paris."`.

## Development roadmap

The following items are **planned, not implemented**:

- **Milestone 2: Testable architecture.** Extract reusable comparison functions, introduce automated unit tests with `pytest`, and improve handling of missing or malformed input.
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
