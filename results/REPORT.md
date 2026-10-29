# Task quality report: 20 Harbor coding tasks

**Result:** 7 tasks VALID, 6 need human REVIEW, 7 INVALID. Plus one dataset-wide verifier hole that affects all
20 tasks and should be fixed once in the shared template. Evidence for every verdict is in
`results/final-code/` (open `report.html`); the run left `tasks/` byte-for-byte unchanged (hash checked).

| Verdict | Tasks |
|---|---|
| INVALID (7) | t02 t03 t04 t06 t07 t09 t16 |
| REVIEW (6) | t05 t10 t12 t13 t15 t19 |
| VALID (7) | t01 t08 t11 t14 t17 t18 t20 |

## 1. How the checks are designed

**Everything is a trial.** The provided harness runs one *action* (a bash script) against a task's own verifier
and returns the score. Every check is a choice of action and a rule for judging the score: the empty action
(NOP), the reference solution (ORACLE), trivial stubs, small breaks of the answer key, cheats, and LLM-written
solutions. Two checks need what the harness can't express (one test alone, reversed order, a time zone), so
they run pytest directly on the oracle's files in the same layout.

**Three tiers, ordered by cost:**

| Tier | Question | Checks |
|---|---|---|
| 1. Reading files (instant) | Is the task well made, and does the agent get a fair, non-leaking spec? | structure, env_leak, dockerfile_parity, oracle_hygiene, spec_coverage, thin_tests, duplicates |
| 2. Running the grader (seconds) | Does the grader work on known answers, reliably? | **nop** and **oracle** (Part 1), flaky (3× each), test_order, timezone |
| 3. Trying to fool it | Can wrong answers pass? Is it fair to right ones? | stub, mutation, cheat, verifier_isolation; with `--llm`: spec-vs-tests, independent solve, hard-coded fake fix |

**Statuses:** PASS (ran, nothing wrong) · **FAIL** (the task is wrong) · **WARN** (probably a problem; a human
decides) · ERROR (our side broke: never blamed on the task; retried once) · SKIPPED (always says what blocked it).

**FAIL vs WARN rule.** FAIL when the evidence is conclusive that the task can't be used as is: doing nothing
scores 1; the answer key scores 0; identical runs disagree; the answer is in the agent's files; tests require
names the agent can't see anywhere; a cheat is accepted. WARN when it's a judgment call or the probe can be
wrong: a surviving mutant may be an equivalent program, one leaked line may be legitimate spec, near-duplicate
text may still test different skills, and LLM findings are opinions. **Task verdict:** any FAIL → INVALID,
any WARN → REVIEW, else VALID.

**Skip rule.** Always run every Tier 1 check, so the author gets the whole list in one round trip. Skip a later
check only if an earlier result makes it impossible or meaningless, naming the blocker. Tier 3 runs only if
nop, oracle and flaky passed: mutants and cheats compare against a working answer key.

**Trusting the checks.** `fixtures/` holds copies of t01 with one planted defect each (starter already
correct, broken oracle, random test, leaked solution, hackable verifier). `check_fixtures.py` confirms the good
copy passes and each broken copy trips only its own check.

## 2. Findings

| Task | Verdict | Problem | Evidence (`results/final-code/…`) |
|---|---|---|---|
| t02_slug | INVALID | Doing nothing scores 1 in 3/3 runs: the starter already passes every test | `t02_slug/nop/` |
| t03_backoff | INVALID | Reference solution scores 0 in 3/3 runs; fails `test_zero_base_disables_backoff` | `t03_backoff/oracle/` |
| t04_invoice | INVALID | Tests import `format_money` and `line_total` and pass `currency=` to `total`; none appears in the instruction or the starter | `t04_invoice/spec_coverage/` |
| t06_dedupe | INVALID | Oracle scored 1, 1, 0: `test_random_sample_roundtrip` uses unseeded `random.sample` and asserts order | `t06_dedupe/flaky/`, `oracle/` |
| t07_configlite | INVALID | `environment/NOTES.md` (visible to the agent) contains 14 lines of the reference solution; also declares `schema.py` as an output the oracle never writes | `t07_configlite/env_leak/`, `oracle_hygiene/` |
| t09_ledger_balance | INVALID | `test.sh` copies the tests into the agent's dir and runs `pytest .`, so an agent `conftest.py` forces a pass (reward 1 without solving) | `t09_ledger_balance/cheat/runs/cheat-conftest-force-pass/` |
| t16_state_machine | INVALID | Reference solution scores 0 in 3/3 runs; fails `test_names_start_with_a_letter_or_underscore` | `t16_state_machine/oracle/` |
| t05_gradebook | REVIEW | One test function on one example; deleting the odd-length median line still passes | `t05_gradebook/thin_tests/`, `mutation/` |
| t10_wordwrap_columns | REVIEW | Instruction 96% similar to t01_word_wrap | `t10_wordwrap_columns/duplicates/` |
| t12_session_cart | REVIEW | 4 tests fail when the suite runs in reverse: they share a module-level cart | `t12_session_cart/test_order/runs/reversed-order/` |
| t13_billing_period | REVIEW | 4 tests pass in UTC and fail in Pacific/Auckland; also, deleting the backwards-range guard still passes (the same-day backwards case of rule 4 is untested) | `t13_billing_period/timezone/`, `mutation/` |
| t15_matrix_report | REVIEW | The instruction contains a line of the solution (`STATS = {"reports": 0, "cells": 0}`) | `t15_matrix_report/env_leak/` |
| t19_atomic_write | REVIEW | The instruction contains a line of the solution (`os.replace(temp, target)`) | `t19_atomic_write/env_leak/` |

The 7 VALID tasks passed every check, including all mutants, stubs and cheats (except the dataset-wide hole below).

## 3. Dataset-wide finding: the verifier can be gamed on every task

Two cheats score 1 on all 20 tasks, because of how every verifier is run, not because of any one task
(`*/verifier_isolation/`):

1. **Pre-written reward.** The agent can write `{"reward": 1}` to `$HARBOR_LOGS_DIR/reward.json` before the
   verifier runs. The reader prefers `reward.json`, and `test.sh` only ever writes `reward.txt`, so the fake
   file wins.
2. **`sitecustomize.py`.** The agent's working dir is on the verifier's `PYTHONPATH`, so a `sitecustomize.py`
   there runs inside pytest and can force exit code 0.

**One template fix for all tasks (in `test.sh`):** clear the log dir first (`rm -f "$LOGS_DIR"/reward.*`) and
write `reward.json` (not only `reward.txt`); run pytest isolated from the agent's dir: `python -I -m pytest`
(or copy the module under test into a clean dir and point `PYTHONPATH` there), with `--rootdir "$TESTS_DIR"`
so agent files can't configure the run. Confirm against real Harbor (`harbor run -a oracle/nop`), since the
local harness may differ on the logs mount.

## 4. What to do with each bad task

| Task | Action |
|---|---|
| t02 | Make the starter wrong (or the tests stricter) so doing nothing scores 0; resubmit. |
| t03, t16 | Read the instruction for the failing test's rule to decide whether the answer key or the test is wrong; fix that side; resubmit. |
| t04 | Document `format_money`, `line_total` and the `currency=` argument in the instruction (or add them to the starter); resubmit. |
| t06 | Seed the random test or replace it with fixed cases; resubmit. |
| t07 | Remove `NOTES.md` from `environment/` (and its COPY line); fix `required_output_files` (drop `schema.py`). |
| t09 | Run pytest on the tests dir with a clean rootdir instead of copying tests into the agent's dir; resubmit. |
| t10 | Drop it, or make it clearly different from t01 (different skill, not a re-skin). |
| t12 | Reset the module-level cart in a fixture so each test sets up its own state. |
| t13 | State "all timestamps are UTC" in the instruction and make the solution/tests use UTC explicitly; add a same-day backwards-range test. |
| t15, t19 | Human review of the instruction wording: is the quoted line legitimate spec or a giveaway? Rephrase if it gives the fix away. |
| t05 | Add an odd-length median test and tests for each requirement (it has one test function). |

**General rule:** INVALID = quarantine; return it to the author with the evidence folder (the exact action,
output and failing test). REVIEW = a human decides, using the evidence. Never ship either until a re-validation
passes. Fix the dataset-wide verifier hole in the template before shipping any task.

## 5. Mistakes caught, and what I'd add with more time

**Mistakes caught in my own validator** (details in `README.md`):
- The flaky check compared failing-test ids that contain the harness's random temp path, a false FAIL on 18 tasks.
- The leak check subtracted all starter lines, which hid the t07 `NOTES.md` leak.
- Text-based mutants deleted docstrings, trailing `return None` and dead initializations; rebuilt with `ast` and
  an equivalence filter.
- An integrity alarm came from macOS `.DS_Store` files, not the validator.
- LLM rate limits (429) were throttled and retried.

Each was found by checking results against fixtures or reading the evidence, not by trusting the first run.

**With more time:**
- **Docker parity.** Run a sample through real Harbor (`harbor run`) and compare with the local harness. Also check
  that the Dockerfile builds and contains what the tests need.
- **Trajectory review.** Run real models on VALID tasks, have humans label passing and failing attempts, and
  measure the grader's real false-pass and false-fail rates. My probes only estimate them.
- **Difficulty calibration.** Model pass rates per task: tasks every model solves add little; tasks none solve need a
  solvability check.
- **LLM checks on every task by default** (spec vs tests, independent solve, hard-coded fake fix). They're built and
  ran on all 20 (`results/tasks-llm-run-2/`), but are opinions, so they only WARN.
- **Stronger mutation and property-based tests** (boundary flips, constants, hypothesis-generated inputs), and
  semantic duplicate detection (embeddings) for large datasets.
