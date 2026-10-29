# task-validator

Starter repo for the Research Ops coding challenge. Read the brief you were sent first;
this file only covers how to run things.

## Setup

Python **3.11+** and pytest. Nothing else is required.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python harness.py selfcheck        # confirms the environment and runs one task
```

`selfcheck` should print `harness looks healthy`. If it does not, stop and tell us --
that is our bug, not yours.

## What is here

```
task-validator/
  harness.py        provided; you should not need to modify it
  tasks/            the 20 tasks to validate -- this is the exercise
  optional/         skip unless you finish early (see optional/README.md)
  requirements.txt
  README.md
```

## Task format

Tasks are in [Harbor](https://www.harborframework.com/docs/tasks) format, the same
format our production tasks ship in:

```
tasks/t01_word_wrap/
  task.toml            name, timeouts, resources, metadata
  instruction.md       the prompt the agent is given
  environment/
    Dockerfile         the container the task runs in
    wordwrap.py        the starter code, copied to /app
  solution/
    solve.sh           the reference solution ("oracle")
  tests/
    test.sh            the verifier
    test_wordwrap.py   the tests it runs
```

The agent sees `instruction.md` and the contents of `environment/`. It does **not** see
`tests/` or `solution/`.

Harbor's contract is that `tests/test.sh` writes a reward to `/logs/verifier/reward.txt`
(or `reward.json`), and that is the task's score. Ours write `1` or `0`.

## The harness

Harbor normally runs each task in a Docker container. `harness.py` runs the same task
locally in a temp directory instead, so a full sweep takes seconds rather than minutes.
It honours the same contract: it runs `solve.sh` and `test.sh` and reads the reward file.

```python
from harness import load_tasks, run_task, NOP, ORACLE

tasks = load_tasks("tasks")

for task in tasks:
    task.dir              # pathlib.Path to the task folder
    task.name             # folder name
    task.instruction      # contents of instruction.md
    task.meta             # task.toml [task] + [metadata], flattened
    task.config           # the whole parsed task.toml
    task.starter_files    # {path: text} the agent starts from

    run_task(task.dir, NOP)      # -> 0 or 1; the agent does nothing
    run_task(task.dir, ORACLE)   # -> 0 or 1; runs solution/solve.sh
```

An **action** is a bash script string, run with the agent's working directory as cwd.
That is what one agent turn amounts to here. `NOP` is the empty script. `ORACLE` is a
sentinel meaning "run this task's own `solution/solve.sh`".

Nothing is written back into `tasks/`, so it is safe to call repeatedly.

Three more helpers, which you may or may not want:

```python
from harness import run_task_detailed, write_files_action, materialize

run_task_detailed(task.dir, ORACLE)      # .score .reward .stdout .stderr .error .timed_out
write_files_action({"wordwrap.py": "..."})  # build an action from file contents
materialize(task.dir, ORACLE)            # {path: text} of the workdir after an action,
                                         # without running the verifier
```

`write_files_action` is the easy way to run a task against a submission you construct
yourself.

## Running a task the real way (optional)

If you have Docker and want to see a task run as Harbor actually runs it:

```bash
pip install harbor
harbor run -p tasks/t01_word_wrap -a oracle   # ~20s, builds a python:3.12-slim image
harbor run -p tasks/t01_word_wrap -a nop
```

This is **not** required, and it is much slower than the provided harness. It is here so
you can confirm the harness is not lying to you.

## Notes

- The 20 tasks in `tasks/` run in seconds.
- The harness uses your current interpreter, so run your tool from inside the venv.
- Use whatever tools you would use on the job.
- `optional/swe-bench-verified/` is read-only stretch from SWE-bench Verified. It is
  not Part 1 or Part 2. Ignore it unless you finish early.

---

# Task validator (built for the challenge)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt anthropic
.venv/bin/python validate.py tasks              # Parts 1-2, all code checks (~4 min)
.venv/bin/python validate.py tasks --llm        # + LLM checks via OpenRouter (OPENROUTER_API_KEY)
.venv/bin/python fixtures/check_fixtures.py     # proves each check works on planted defects
```

Results: `results/<name>/report.html` (click a cell → reason, fix, evidence) and per task/check folders with
the exact action, full stdout/stderr and score of every run. Write-up: `results/REPORT.md`.

| File | What it does |
|---|---|
| `validate.py` | runs the checks per task (in parallel), the skip rule, duplicates, the tasks/ integrity hash |
| `validator/checks.py` | one `check_<name>()` per check, each with a WHAT/WHY/HOW/STATUS docstring |
| `validator/probes.py` | the constructed submissions: stubs, ast mutants, cheats |
| `validator/direct.py` | direct pytest runs (one test alone, reversed order, TZ) the harness can't express |
| `validator/evidence.py`, `report.py` | the evidence trail and report.html |
| `validator/llm.py` | OpenRouter call (Claude Sonnet), rate-limited |

## Mistakes caught (every time the validator itself was wrong)

1. **Flaky false positive on 18/20 tasks.** pytest prints failing test ids with the harness's random temp dir,
   so identical failures looked different. Fixed: compare only `file.py::test`.
2. **Leak check hid the t07 leak.** It subtracted every starter line from the solution's lines, and `NOTES.md`
   *is* a starter file, so the leaked lines were subtracted away. Fixed: subtract only the original lines of
   the file being changed.
3. **Mutation false positives.** Text-based mutants deleted docstring lines, a trailing `return None`, and dead
   initializations (`length = 0` that the loop always overwrites first). Rebuilt with `ast`: statements and
   comparisons only, never docstrings/comments; no trailing `return None`, no literal initializations; drop any
   mutant whose ast (ignoring docstrings) equals the original's.
4. **Integrity alarm from macOS.** Finder wrote `.DS_Store` files into tasks/; the hash now ignores OS metadata
   (git confirmed no task file changed).
5. **LLM rate limit.** 6 parallel tasks exceeded OpenRouter's 20 requests/min for new accounts (429s, correctly
   reported as ERROR, not blamed on tasks). Fixed: calls spaced 3.2 s apart, 429 retried after a pause.
6. **Severity call:** a `required_output_files` mismatch was FAIL; it's a metadata error, so now WARN.
7. **A fixture expectation of mine** assumed the random test would fail the oracle; it passed 3/3 by chance
   (1 in 8). The flaky check still caught it; the fixture now allows either oracle result.
