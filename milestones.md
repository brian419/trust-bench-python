# TrustBench Development Milestones

TrustBench is an independent Python learning and portfolio project exploring reproducible evaluation of AI-generated responses. Development is incremental: implement a small feature, understand its behavior, test it, and then extend it.

**Current status:** Milestones 1, 2, and 3 implemented, tested (47 automated tests), and merged into `main` on October 21, 2026. Milestone 4A implemented and locally tested on `feature/milestone-4` (53 passing tests); not yet merged. Milestones 4B–4E and 5 remain planned.

## Guiding principles

- **Write and understand the implementation.** Use official documentation, experiments, and code review to learn; do not treat generated code as evidence of independently acquired skills.
- **Preserve functionality.** Keep the working Milestone 1 output and behavior when refactoring, unless a behavior change is explicitly required and tested.
- **Be precise about metrics.** “Accuracy” is normalized exact-match rate among scored responses in the provided test dataset, not a measurement of a model's general accuracy, factuality, safety, or fairness. Live HTTP/network/timeout errors are counted separately and excluded from the denominator.
- **Build reproducibly.** Document inputs, dependencies, assumptions, expected results, and known limitations.
- **Mark work complete only after testing.** Do not represent planned work as implemented in the README or on a resume.

## Milestone overview

| Milestone | Goal | Status |
| --- | --- | --- |
| 1 | Basic evaluation and normalization | **Complete (manual verification)** |
| 2A | Reusable Python functions | **Complete** |
| 2B | Automated unit tests with pytest | **Complete** |
| 2C | Input validation and error handling | **Complete** |
| 3 | Run evaluations against a local AI model and save basic JSON reports | **Complete (47 tests total)** |
| 4 | Responsible AI evaluation methods | In progress: 4A implemented/tested on feature branch; 4B–4E planned |
| 5 | Reproducibility, comparison, and reporting | Planned |

---

## Milestone 1: Basic evaluation and normalization

**Status: Complete.** The original prototype has since been extended. The current `eval.py` reads `eval-read-valid.json` by default and accepts an optional file path.

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

### Scope limitations

- Milestone 1 itself evaluated prerecorded responses only; Milestone 3 later added a separate live evaluator (`eval_live.py`).
- Matching remains exact after normalization: `Paris` and `The capital is Paris.` do not match.
- The current evaluator handles missing files, malformed JSON, and invalid dataset structure with errors and a nonzero exit status.
- The original `eval.py` remains offline-only; model comparisons and an evaluation database are not implemented.

**Acceptance:** Existing functionality and the above manually verified behaviors are preserved on the stable branch.

---

## Milestone 2: Testable architecture and automated testing

**Goal:** Make the existing evaluator easier to test and safer to run, without losing Milestone 1 features.

### Milestone 2A: Reusable Python functions

**Status: Complete.** Reusable functions separate comparison and accuracy calculations from CLI input/output.

#### Assignment

- [x] Create `compare_answers(expected, response)`, returning a Boolean.
- [x] Move the existing whitespace/case normalization into that function.
- [x] Call the function from the current evaluation loop rather than duplicating comparison logic.
- [x] Preserve individual test messages, totals, rounded percentage, and `N/A` for empty arrays.
- [x] Manually test equal, case-different, whitespace-different, and unequal answer pairs.

#### Acceptance criteria

- `compare_answers("Paris", "  PARIS  ")` returns `True`.
- `compare_answers("60", "45")` returns `False`.
- `compare_answers("Tokyo", "tokyo")` returns `True`.
- Running `python3 eval.py` with the Milestone 1 dataset still reports 2 passed, 1 failed, and 66.67 accuracy.
- The empty-array case still reports `Accuracy: N/A`.

**Learning references:** [Python functions](https://docs.python.org/3/tutorial/controlflow.html#defining-functions), [Python string methods](https://docs.python.org/3/library/stdtypes.html#string-methods).

### Milestone 2B: Automated unit tests with pytest

**Status: Complete.** Automated pytest tests cover answer matching and accuracy computation without running the CLI on import.

#### Assignment

- [x] Install `pytest` in a project-specific virtual environment and document the setup.
- [x] Add a `tests/` directory with tests for `compare_answers`.
- [x] Verify exact matches, case differences, leading/trailing whitespace, and nonmatches.
- [x] Test the empty-dataset behavior and accuracy calculation, refactoring into additional functions only when it improves testability.
- [x] Ensure importing functions for testing does not unintentionally execute the entire CLI script.
- [x] Run `python3 -m pytest` and document successful results.

#### Acceptance criteria

- Tests run repeatedly without manually changing input files between cases.
- A failing assertion causes the test run to fail.
- Existing CLI output and behaviors remain available and correct.

**Learning references:** [pytest getting started](https://docs.pytest.org/en/stable/getting-started.html), [Python modules](https://docs.python.org/3/tutorial/modules.html).

### Milestone 2C: Input validation and error handling

**Status: Complete.** Input validation and clean CLI errors are implemented and tested.

#### Assignment

- [x] Handle a missing `eval-read.json` file gracefully.
- [x] Handle blank and malformed JSON without displaying an unhandled traceback during normal CLI use.
- [x] Reject a non-list top-level JSON value with a useful message.
- [x] Check that each case has the required fields (`id`, `expected`, `response`) with appropriate types.
- [x] Decide and document the policy for an empty array versus an invalid dataset.
- [x] Add pytest cases covering both valid inputs and these failures.

#### Acceptance criteria

- Valid inputs still produce the Milestone 1 results.
- Invalid inputs produce clear errors and an appropriate nonzero process exit status.
- The evaluator does not silently count malformed cases as valid passes or failures.

**Learning references:** [Python exceptions](https://docs.python.org/3/tutorial/errors.html), [Python JSON module](https://docs.python.org/3/library/json.html).

---

## Milestone 3: Real AI model integration

**Status: Complete (implementation and local validation, October 21, 2026).** Added live evaluation against a **local Ollama model** while retaining offline evaluation of prerecorded fixtures.

### Implemented

- [x] Learned and used local HTTP POST requests, JSON request/response payloads, and a request timeout using Python's standard library (`urllib.request`).
- [x] Built `ollama_client.py` with `generate_response(prompt, model)` targeting Ollama's local `/api/generate` endpoint with `stream: false`.
- [x] Used the locally available `gemma3:1b` model without paid hosted API requests or credentials.
- [x] Added `eval_live.py`, with live dataset validation (`id`, `question`, `expected`; a prerecorded `response` is not required).
- [x] Reused `compare_answers` and `calculate_accuracy`, keeping `eval.py` usable for prerecorded answers.
- [x] Distinguished `PASS`/`FAIL` from `ERROR`, handling HTTP errors, network failures, and timeouts (including timeouts wrapped in `URLError`).
- [x] Kept API/network errors out of the accuracy denominator; represented accuracy as `None`/JSON `null` when no cases were scored.
- [x] Recorded model identifier, dataset filename, UTC timestamp, per-case prompt/expected/generated answers/status, error details where applicable, and per-request elapsed seconds.
- [x] Saved a new uniquely named JSON file for each run under ignored `reports/`, preserving previous reports.
- [x] Added filesystem/report-save failure handling and automated tests using mocked model calls.
- [x] Verified repeated real local runs and a complete suite of **47 passing pytest tests**.

### Completion evidence

- Commands: `ollama pull gemma3:1b` (first-time setup), then `python3 eval_live.py` from the repository root while Ollama is running; run `python3 -m pytest -v` for tests without requiring Ollama.
- Live sample: two simple prompts requesting `Paris` and `12`, both passing in observed runs. The evaluator records raw replies (including harmless surrounding whitespace) as well as scores.
- The reports contain `metadata`, `summary`, and `results`; durations were checked against terminal output and guarded by a deterministic regression test.
- Automated tests exercise HTTP, connection, and timeout failures, dataset errors, saved report contents, multiple report preservation, and report-saving failures.
- No paid API charges are required for the documented Ollama workflow. Model download and local CPU/RAM usage still apply.

### Current limitations / deferred work

- Live evaluation is currently configured in source for `gemma3:1b` and `eval-read-live.json`; it does **not** yet expose a general-purpose model selection or live dataset CLI argument.
- The connector uses a 120-second request timeout but does not implement retries, exponential backoff, hosted-provider authentication, or rate-limit policies. Those were learning topics in the initial plan, not completed features.
- The current report records model name and timing but not model weights hash, decoding settings, prompt templates, or dataset version hash.
- No multi-model comparisons, semantic scoring, factuality/safety metrics, or aggregated evaluation database yet.
- Saved reports are currently written directly; partial output cleanup on a mid-write failure is not implemented.

---

## Milestone 4: Responsible AI evaluation methods

**Status: In progress on `feature/milestone-4`.** Milestone 4A is implemented and locally tested (53 passing tests), building on Milestone 3's local `gemma3:1b` Ollama workflow, JSON reports, and **47-test baseline**. Work remains on the feature branch pending review/merge; 4B–4E are planned.

**Working approach:** Progress through 4A–4E sequentially, with small learning exercises, targeted tests, and review of outputs before advancing. Preserve `eval.py`, existing `eval_live.py` behavior, JSON reports, and all baseline tests. Favor free local execution, offline fixtures, and mocked calls; no paid API accounts or substantial new dependencies required. Keep dataset and scoring definitions explicit rather than adding vague "responsible AI" scores.

### Milestone 4A: Reference-grounded factual evaluation

**Status: Implementation and local validation complete on `feature/milestone-4` (October 21, 2026); commit/merge status not yet confirmed.**

**Goal:** Introduce a small curated evaluation set with auditable references for each expected factual answer. References serve as human-review evidence, not retrieved model context.

- [x] Created 10 factual cases in `eval-read-reference.json`, each with stable `id`, `question`, `expected`, and `reference` containing `url` and `verified_date`.
- [x] Chose narrow, mostly stable facts across chemistry, geography, computing, astronomy, biology, and measurement.
- [x] Implemented `validate_reference_dataset()` in `reference_validator.py`; reuses `validate_dataset(..., require_response=False)` and validates the reference object, nonblank URL/date strings, and strict calendar-date formatting.
- [x] Allowed `eval_live.main(filename="eval-read-live.json")` to accept the reference dataset while preserving the original default and legacy schema; the reference filename selects reference-specific validation.
- [x] Preserved per-case `reference` metadata in the JSON results for PASS, FAIL, and ERROR cases.
- [x] Ran local `gemma3:1b` baseline on the ten cases, saved raw outputs and categorized mismatches, and verified **53 passing pytest tests** including successful/error-path reference reporting.

**Local evidence:** `python3 -c "from eval_live import main; main('eval-read-reference.json')"`. One October 21 run saved `reports/evaluation-2ecae329e17d458ba51bce8a457c4ab8.json`: **8 PASS, 2 FAIL, 0 ERROR, 80.0 normalized exact-match accuracy**. `fact_007`: `Thymine` expected, `A` generated. `fact_009`: `kilogram` expected, `Gram` generated. Other observed runs showed response variation. Reports are ignored by Git and are not included in a fresh checkout unless explicitly shared.

**Limitations:** Structural validation does not fetch or verify the URL's factual content; `verified_date` is dataset metadata, not automatically established by the program. Source citations are stored but not passed to Ollama as retrieval context. Normalized exact matching does not accept equivalent paraphrases or detect unsupported explanations, and ten cases cannot establish a general model reliability score. Source-content verification, review of ambiguous equivalent responses, and stronger reproduction metadata remain open improvements or later milestone work.

**Acceptance evidence:** Each case includes an auditable URL/date, local scoring is reproducible with the documented command and installed model, results retain references (even on request error), and the report clearly separates exact matches, incorrect outputs, and request failures.

### Milestone 4B: Evaluation beyond exact matching

**Goal:** Make legitimate paraphrases and incorrect assertions distinguishable without claiming to solve general semantic evaluation.

- [ ] Create labeled examples of exact matches, acceptable alternatives, semantically correct paraphrases, incomplete answers, and incorrect or unsupported claims.
- [ ] Define a narrowly specified alternative scorer (e.g., accepted answer variants or a transparent rule-based method), **alongside** the original normalized exact-match baseline.
- [ ] Represent uncertain outcomes as `REVIEW` / unscored when automated assessment is not sufficiently justified; document false positives and negatives.
- [ ] Test scorer boundaries, preserve original `compare_answers` behavior, and compare outcomes with the exact-match baseline on the small labeled set.

**Acceptance:** The scoring rules, permitted answer variants, and disagreement cases are inspectable. No unsupported "hallucination rate" or generalized semantic-accuracy claims.

### Milestone 4C: Response consistency and failure classification

**Goal:** Investigate variability across repeated local generations and organize observed errors.

- [ ] Choose a small fixed prompt set and repeat runs under documented conditions; record run count, prompts, model, and any available inference settings.
- [ ] Keep requests sequential and bounded for the 8 GB development machine; do not require costly compute.
- [ ] Classify examples by specific categories such as correct, incorrect, unsupported, ambiguous, formatting-only mismatch, or request error.
- [ ] Summarize disagreement counts and representative outputs, without treating small-sample variability as a statistically definitive reliability metric.
- [ ] Test classification helpers independently of live Ollama access.

**Acceptance:** A short reproducible experiment and saved evidence show where answers vary, with a clear separation between model behavior and evaluator limitations.

### Milestone 4D: Controlled prompt-injection resilience

**Goal:** Explore instruction-boundary failures in safe, self-contained experiments.

- [ ] Prepare a few synthetic scenarios containing trusted task instructions and untrusted quoted or document-like content.
- [ ] Label the intended response and the untrusted text's attempted behavioral redirection; do not use real secrets, external exfiltration, or harmful payloads.
- [ ] Define observable success/failure/review criteria and run a bounded local evaluation.
- [ ] Document both successful resistance and failures, including where exact matching or manual review changes interpretation.
- [ ] Add test fixtures for scenario structure and scoring.

**Acceptance:** A reader can reproduce safe test cases and understand precisely what behavior was tested, without claims of comprehensive prompt-injection safety.

### Milestone 4E: Review, synthesis, and documentation

**Goal:** Make Milestone 4 evidence understandable and ready to share without overstating results.

- [ ] Summarize dataset size, method, reference quality, labeled examples, and major failure modes; use existing local JSON reports where useful.
- [ ] Explain known evaluator errors, manual review decisions, compute constraints, and threats to validity.
- [ ] Update `README.md` and this milestone plan only for features actually implemented.
- [ ] Run the full pytest suite, verify preserved Milestones 1–3 behavior, and manually reproduce at least one representative experiment.
- [ ] Commit/push changes to `feature/milestone-4`; review before eventual merge into `main`.

**Acceptance:** Every reported conclusion is traceable to specific prompts, reference material, scoring criteria, and saved or documented evidence.

### Deferred work and scope boundaries

- Avoid broad claims about fairness, bias, privacy, safety, or factuality based solely on tiny datasets. If rigorous bias/privacy methodology would substantially expand scope, record it as future research instead of marking it complete.
- Advanced cross-model comparisons, dataset/version hashing, configurable report comparisons, and statistical uncertainty reporting remain primarily **Milestone 5** work.
- No new hosted provider integration, paid API, model training/fine-tuning, large orchestration framework, or unrelated application refactor is required for Milestone 4.

**Background reading:** [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework), [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/).


---

## Milestone 5: Reproducibility and reporting

**Status: Planned (advanced features).** Basic per-run JSON reports already exist from Milestone 3; cross-run comparisons and stronger reproducibility metadata remain future work.

### Proposed work

- [x] Save basic structured JSON run results (**implemented in Milestone 3**; CSV/SQLite remain optional future work).
- [ ] Compare runs against the same versioned test suite and evaluation rules.
- [ ] Summarize pass rates by category and retain examples of failures.
- [ ] Expand existing model-name/dataset-name/timestamp metadata to include model versions/configuration, dataset revision, and explicit scoring-rule version.
- [ ] Include sample sizes and uncertainty or limitations where appropriate.
- [ ] Publish a concise evaluation report, with clear instructions to reproduce it.

### Completion evidence

A reader can compare multiple runs using documented model/dataset/scoring versions, inspect individual cases and categories, understand the uncertainty and limitations, and reproduce the comparison without undocumented manual steps.

---

## Working practices and milestone completion

1. Begin new development on a feature branch of your choosing; branch creation is managed manually.
2. Implement a small change and run the existing example before adding the next change.
3. Add automated tests where applicable; preserve existing functionality throughout.
4. Update this file and the README when a milestone is genuinely completed.
5. Keep Git commits focused and include meaningful descriptions.

### Completed Milestone 2 evidence

- `compare_answers`, `calculate_accuracy`, and `validate_dataset` are importable and tested.
- The CLI accepts custom paths, produces clear input errors, and stops before scoring invalid datasets.
- `python3 -m pytest -v` runs 27 automated unit and CLI tests (26 originally completed, plus the CLI empty-array test).
- The default sample still produces 2 passes, 1 failure, and 66.67 accuracy.

### Completed Milestone 3 evidence

- `ollama_client.py` calls local Ollama, and `eval_live.py` evaluates model-generated answers without changing offline `eval.py` behavior.
- PASS/FAIL/ERROR outcomes, request durations, UTC timestamps, and raw generated responses are recorded in unique JSON reports.
- `tests/test_eval_live.py` and `tests/test_ollama_client.py` cover success paths, mocked request errors, timing, report persistence, and failure handling.
- **47 tests passed** on October 21, 2026; multiple local Ollama runs and JSON reports were also manually validated.

### Near-term next step

Milestone 4A is implemented and tested on `feature/milestone-4` (53 passing tests). Review and commit/push the 4A code and documentation, then begin **4B: evaluation beyond exact matching**. Milestone 3 remains complete on `main` (47-test baseline); advanced cross-run reporting remains planned for Milestone 5.
