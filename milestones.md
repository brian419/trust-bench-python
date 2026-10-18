# TrustBench Development Milestones

TrustBench is an independent Python learning and portfolio project exploring reproducible evaluation of AI-generated responses. Development is incremental: implement a small feature, understand its behavior, test it, and then extend it.

**Current status:** Milestone 1 complete; Milestone 2A next. Milestones 2–5 are plans, not implemented capabilities.

## Guiding principles

- **Write and understand the implementation.** Use official documentation, experiments, and code review to learn; do not treat generated code as evidence of independently acquired skills.
- **Preserve functionality.** Keep the working Milestone 1 output and behavior when refactoring, unless a behavior change is explicitly required and tested.
- **Be precise about metrics.** The current “accuracy” is normalized exact-match rate on a small sample of prerecorded answers, not a measurement of a model's overall accuracy, factuality, safety, or fairness.
- **Build reproducibly.** Document inputs, dependencies, assumptions, expected results, and known limitations.
- **Mark work complete only after testing.** Do not represent planned work as implemented in the README or on a resume.

## Milestone overview

| Milestone | Goal | Status |
| --- | --- | --- |
| 1 | Basic evaluation and normalization | **Complete (manual verification)** |
| 2A | Reusable Python functions | **Next** |
| 2B | Automated unit tests with pytest | Planned |
| 2C | Input validation and error handling | Planned |
| 3 | Run evaluations against a real AI model | Planned |
| 4 | Responsible AI evaluation methods | Planned |
| 5 | Reproducibility, comparison, and reporting | Planned |

---

## Milestone 1: Basic evaluation and normalization

**Status: Complete.** The working prototype lives in `eval.py` and reads `eval-read.json`.

### Implemented

- [x] Read an array of test cases from a JSON file using Python's standard library.
- [x] Iterate through the cases and compare each `expected` answer with its prerecorded `response`.
- [x] Normalize both strings with `.lower()` and `.strip()` before comparing.
- [x] Print a PASS/FAIL result alongside each test ID.
- [x] Count passing and failing cases, including correct singular/plural output.
- [x] Calculate and round the pass percentage to two decimal places.
- [x] Return `Accuracy: N/A` for a valid empty list (`[]`) rather than dividing by zero.

### Manually verified cases

- Equal answers such as `Paris` and `Paris` pass.
- Whitespace and case differences such as `Paris` and `  PARIS  ` pass.
- Different answers such as `60` and `45` fail.
- The three-case sample produces 2 passes, 1 failure, and 66.67 accuracy.
- A valid empty JSON array produces 0 passes, 0 failures, and `Accuracy: N/A`.

### Current limitations

- Recorded responses only. The program does **not** call an AI model.
- Matching remains exact after normalization: `Paris` and `The capital is Paris.` do not match.
- A blank or malformed JSON file currently raises a `JSONDecodeError`; other invalid structures can also raise exceptions.
- No automated tests, validation framework, evaluation database, or model comparison yet.

**Acceptance:** Existing functionality and the above manually verified behaviors are preserved on the stable branch.

---

## Milestone 2: Testable architecture and automated testing

**Goal:** Make the existing evaluator easier to test and safer to run, without losing Milestone 1 features.

### Milestone 2A: Reusable Python functions

**Status: Next.** Focus on Python function definitions, parameters, return values, and separation of concerns.

#### Assignment

- [ ] Create `compare_answers(expected, response)`, returning a Boolean.
- [ ] Move the existing whitespace/case normalization into that function.
- [ ] Call the function from the current evaluation loop rather than duplicating comparison logic.
- [ ] Preserve individual test messages, totals, rounded percentage, and `N/A` for empty arrays.
- [ ] Manually test equal, case-different, whitespace-different, and unequal answer pairs.

#### Acceptance criteria

- `compare_answers("Paris", "  PARIS  ")` returns `True`.
- `compare_answers("60", "45")` returns `False`.
- `compare_answers("Tokyo", "tokyo")` returns `True`.
- Running `python3 eval.py` with the Milestone 1 dataset still reports 2 passed, 1 failed, and 66.67 accuracy.
- The empty-array case still reports `Accuracy: N/A`.

**Learning references:** [Python functions](https://docs.python.org/3/tutorial/controlflow.html#defining-functions), [Python string methods](https://docs.python.org/3/library/stdtypes.html#string-methods).

### Milestone 2B: Automated unit tests with pytest

**Status: Planned.** Learn what a unit test verifies and how to isolate code so it can be tested without manually editing JSON inputs.

#### Assignment

- [ ] Install `pytest` in a project-specific virtual environment and document the setup.
- [ ] Add a `tests/` directory with tests for `compare_answers`.
- [ ] Verify exact matches, case differences, leading/trailing whitespace, and nonmatches.
- [ ] Test the empty-dataset behavior and accuracy calculation, refactoring into additional functions only when it improves testability.
- [ ] Ensure importing functions for testing does not unintentionally execute the entire CLI script.
- [ ] Run `python3 -m pytest` and document successful results.

#### Acceptance criteria

- Tests run repeatedly without manually changing input files between cases.
- A failing assertion causes the test run to fail.
- Existing CLI output and behaviors remain available and correct.

**Learning references:** [pytest getting started](https://docs.pytest.org/en/stable/getting-started.html), [Python modules](https://docs.python.org/3/tutorial/modules.html).

### Milestone 2C: Input validation and error handling

**Status: Planned.** Learn `try/except`, input contracts, informative error messages, and testing failure paths.

#### Assignment

- [ ] Handle a missing `eval-read.json` file gracefully.
- [ ] Handle blank and malformed JSON without displaying an unhandled traceback during normal CLI use.
- [ ] Reject a non-list top-level JSON value with a useful message.
- [ ] Check that each case has the required fields (`id`, `expected`, `response`) with appropriate types.
- [ ] Decide and document the policy for an empty array versus an invalid dataset.
- [ ] Add pytest cases covering both valid inputs and these failures.

#### Acceptance criteria

- Valid inputs still produce the Milestone 1 results.
- Invalid inputs produce clear errors and an appropriate nonzero process exit status.
- The evaluator does not silently count malformed cases as valid passes or failures.

**Learning references:** [Python exceptions](https://docs.python.org/3/tutorial/errors.html), [Python JSON module](https://docs.python.org/3/library/json.html).

---

## Milestone 3: Real AI model integration

**Status: Planned.** Replace prerecorded-only input with an optional way to collect actual model responses, while **retaining** the ability to evaluate saved responses offline.

### Proposed work

- [ ] Learn HTTP requests, API authentication, timeouts, retries, and rate limits.
- [ ] Implement one configurable model connector before generalizing to multiple providers.
- [ ] Keep credentials out of Git and logs.
- [ ] Store responses with the test ID, provider/model identifier, prompt configuration, execution time, and relevant settings.
- [ ] Support offline fixtures or mocks so development does not require paid API usage.
- [ ] Distinguish API failures from genuine model evaluation failures.

### Completion evidence

Demonstrate a small real-model run, repeat it from documented instructions, and show the saved raw responses and execution metadata. Record any financial or free-tier limitations.

---

## Milestone 4: Responsible AI evaluation methods

**Status: Planned.** Develop narrow, defensible tests rather than claiming comprehensive AI safety coverage.

### Proposed work

- [ ] Build a small, documented factual-grounding dataset using known reference material.
- [ ] Introduce assessment methods beyond exact string matching, while explicitly documenting evaluator error.
- [ ] Explore controlled prompt-injection resilience cases that are safe to reproduce.
- [ ] Investigate consistency across repeated runs and categorize model failures.
- [ ] Identify cases requiring human judgment and record review criteria.
- [ ] Investigate bias and privacy testing only where the dataset and methodology support meaningful claims.

### Completion evidence

For each metric, document: what is tested, how a result is scored, examples of false positives/negatives, sample size, and limitations. Do not label a simple pass rate as “AI safety” or “hallucination rate” without validated measurement.

**Background reading:** [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework), [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/).

---

## Milestone 5: Reproducibility and reporting

**Status: Planned.** Make results inspectable and comparisons scientifically cautious.

### Proposed work

- [ ] Save structured run results (for example JSON/CSV, with SQLite only if useful).
- [ ] Compare runs against the same versioned test suite and evaluation rules.
- [ ] Summarize pass rates by category and retain examples of failures.
- [ ] Record model versions/configurations, test dataset version, scoring rules, and run timestamps.
- [ ] Include sample sizes and uncertainty or limitations where appropriate.
- [ ] Publish a concise evaluation report, with clear instructions to reproduce it.

### Completion evidence

A reader can inspect a report, understand what was tested, trace scores to individual cases, and repeat the procedure without relying on undocumented manual steps.

---

## Working practices and milestone completion

1. Begin new development on a feature branch of your choosing; branch creation is managed manually.
2. Implement a small change and run the existing example before adding the next change.
3. Add automated tests where applicable; preserve existing functionality throughout.
4. Update this file and the README when a milestone is genuinely completed.
5. Keep Git commits focused and include meaningful descriptions.

### Near-term next step

**Start Milestone 2A only:** write and test `compare_answers(expected, response)` yourself, then replace the inline comparison in `eval.py` with a call to that function. Do not implement Milestones 2B or 2C until 2A is understood and verified.
