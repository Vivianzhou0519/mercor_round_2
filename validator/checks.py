"""All quality checks. Each check_<name>(ctx) returns a CheckResult.

Core idea: everything is a *trial* = one harness run of some action (NOP, ORACLE, a stub, a mutant, a cheat,
an LLM-written solution) against the task's own verifier. Checks differ only in which action they run and how
they judge the score. Tier 1 reads files (instant); Tier 2 = Part 1 + reliability; Tier 3 = can the grader be
fooled / is it fair.
"""

from __future__ import annotations

import difflib
import re
import subprocess
import time
import tomllib

from harness import NOP, ORACLE, run_task_detailed, write_files_action

from . import llm, probes
from .evidence import CheckResult, TaskEvidence

REQUIRED_FILES = ["instruction.md", "task.toml", "environment/Dockerfile", "solution/solve.sh", "tests/test.sh"]


class Ctx:
    """Everything one task's checks share: the task, its evidence writer, options, and cached results."""

    def __init__(self, task, ev: TaskEvidence, runs: int, use_llm: bool):
        self.task, self.ev, self.runs, self.use_llm = task, ev, runs, use_llm
        self.cache: dict = {}

    def trial(self, check: str, label: str, action, extra: dict | None = None):
        """Run one action through the provided harness and save the evidence. The single primitive."""
        t0 = time.time()
        r = run_task_detailed(self.task.dir, action)
        text = action if isinstance(action, str) else (self.task.dir / "solution" / "solve.sh").read_text()
        self.ev.save_run(check, label, text, r, time.time() - t0, extra)
        return r

    def oracle_changes(self) -> dict:
        if "changes" not in self.cache:
            self.cache["changes"] = probes.oracle_changes(self.task)
        return self.cache["changes"]


def _r(name, tier, status, reason, fix="", details=None):
    return CheckResult(name, tier, status, reason, fix, details or [])


# ----------------------------------------------------------------------------- Tier 1: read files only


def check_structure(ctx: Ctx) -> CheckResult:
    """STRUCTURE: is the task packaged correctly?
    WHY:  a missing file or broken script makes every later result meaningless.
    HOW:  required files exist, task.toml parses with name + verifier timeout, instruction non-empty,
          `bash -n` on solve.sh/test.sh, test.sh writes a reward file, at least one test file.
    FAIL: anything missing or broken."""
    t, probs = ctx.task, []
    for f in REQUIRED_FILES:
        if not (t.dir / f).is_file():
            probs.append(f"missing {f}")
    if not list((t.dir / "tests").glob("test_*.py")):
        probs.append("no tests/test_*.py")
    try:
        cfg = tomllib.loads((t.dir / "task.toml").read_text())
        if not cfg.get("task", {}).get("name"):
            probs.append("task.toml has no [task] name")
        if "timeout_sec" not in cfg.get("verifier", {}):
            probs.append("task.toml has no [verifier] timeout_sec")
    except (OSError, tomllib.TOMLDecodeError) as e:
        probs.append(f"task.toml does not parse: {e}")
    if not t.instruction.strip():
        probs.append("instruction.md is empty")
    for f in ("solution/solve.sh", "tests/test.sh"):
        p = t.dir / f
        if p.is_file() and subprocess.run(["bash", "-n", str(p)], capture_output=True).returncode != 0:
            probs.append(f"{f} has a shell syntax error")
    test_sh = t.dir / "tests" / "test.sh"
    if test_sh.is_file() and "reward" not in test_sh.read_text():
        probs.append("tests/test.sh never writes a reward file")
    if probs:
        return _r("structure", 1, "FAIL", "; ".join(probs), "add/repair the listed files")
    return _r("structure", 1, "PASS", "all required files present and valid")


def check_env_leak(ctx: Ctx) -> CheckResult:
    """ENV LEAK: can the agent see the answer?
    WHY:  the agent sees instruction.md and environment/. If the reference solution's code is in there, the
          task tests copying, not solving.
    HOW:  take the lines the oracle adds (via materialize, no verifier), keep distinctive ones (>= 20 chars),
          and search the instruction + every agent-visible file. Also: test function names in the instruction.
    FAIL: >= 3 solution lines visible. WARN: 1-2 lines, or test names named."""
    t = ctx.task
    visible = {"instruction.md": t.instruction, **t.starter_files}
    sol_lines = set()
    for path, new in ctx.oracle_changes().items():
        # only lines the solution ADDS to this file (not lines that were already in the same starter file;
        # other agent-visible files like a NOTES.md must NOT be subtracted, or a leak hides itself)
        original = {l.strip() for l in t.starter_files.get(path, "").splitlines()}
        sol_lines |= {l.strip() for l in new.splitlines() if l.strip() not in original and len(l.strip()) >= 20
                      and not l.strip().startswith(("#", '"""', "def ", "import", "from"))}
    visible = {name: text for name, text in visible.items() if name not in ctx.oracle_changes() or name == "instruction.md"}
    hits = {}
    for name, text in visible.items():
        found = [l for l in sol_lines if l in text]
        if found:
            hits[name] = found
    test_names = set(re.findall(r"def (test_\w+)", " ".join(p.read_text() for p in (t.dir / "tests").glob("*.py"))))
    named = sorted(n for n in test_names if n in t.instruction)
    details = [f"{f}: {len(v)} solution line(s), e.g. `{v[0][:80]}`" for f, v in hits.items()]
    details += [f"instruction names hidden test {n}" for n in named]
    n_lines = sum(len(v) for v in hits.values())
    if n_lines >= 3:
        return _r("env_leak", 1, "FAIL", f"{n_lines} lines of the reference solution are visible to the agent in "
                  f"{', '.join(hits)}", "remove the solution code from the agent-visible files", details)
    if n_lines or named:
        return _r("env_leak", 1, "WARN", "possible answer leak in agent-visible files",
                  "remove solution lines / hidden test names from instruction and environment", details)
    return _r("env_leak", 1, "PASS", f"none of {len(sol_lines)} distinctive solution lines is visible to the agent")


def check_dockerfile_parity(ctx: Ctx) -> CheckResult:
    """DOCKERFILE PARITY: does the real container match what the harness shows the agent?
    WHY:  the harness copies every environment/ file; real Harbor only has what the Dockerfile COPYs.
          A mismatch means local results don't predict production. Unpinned versions drift over time.
    HOW:  compare COPY sources with environment/ files; base image has a tag; pip installs pinned (==).
    FAIL: COPY of a file that doesn't exist (build breaks). WARN: file not copied / unpinned."""
    t = ctx.task
    df = (t.dir / "environment" / "Dockerfile").read_text() if (t.dir / "environment" / "Dockerfile").is_file() else ""
    copied = set()
    for m in re.finditer(r"^(?:COPY|ADD)\s+(.+)$", df, re.MULTILINE):
        parts = [p for p in m.group(1).split() if not p.startswith("--")]
        copied.update(p.strip("./") for p in parts[:-1])
    env_files = set(t.starter_files)
    missing_src = sorted(c for c in copied if c not in env_files and c not in (".", "*") and "*" not in c)
    not_copied = sorted(f for f in env_files if f not in copied and "." not in copied)
    unpinned = re.findall(r"pip install[^\n]*?\s([A-Za-z][\w.-]*)(?=\s|$)(?!==)", df)
    unpinned = [p for p in unpinned if "==" not in p and not p.startswith("-")]
    base = re.search(r"^FROM\s+(\S+)", df, re.MULTILINE)
    details = [f"Dockerfile COPYs {c} but environment/ has no such file" for c in missing_src]
    details += [f"environment/{f} is shown to the agent by the harness but not COPY'd into the image" for f in not_copied]
    details += [f"unpinned pip package: {p}" for p in unpinned]
    if base and (":" not in base.group(1) or base.group(1).endswith(":latest")):
        details.append(f"base image not pinned: {base.group(1)}")
    if missing_src:
        return _r("dockerfile_parity", 1, "FAIL", "Dockerfile copies files that don't exist; the real build fails",
                  "fix the COPY lines or add the files", details)
    if details:
        return _r("dockerfile_parity", 1, "WARN", "harness and real container differ, or versions unpinned",
                  "COPY every agent file in the Dockerfile and pin versions", details)
    return _r("dockerfile_parity", 1, "PASS", "Dockerfile copies exactly the agent's files; versions pinned")


def check_oracle_hygiene(ctx: Ctx) -> CheckResult:
    """ORACLE HYGIENE: is the reference solution a legitimate answer?
    WHY:  an oracle that reads the hidden tests, or writes files the task doesn't declare, proves nothing
          about whether an agent could solve the task from the instruction.
    HOW:  solve.sh must not *use* $TESTS_DIR / /tests (declaring the variable is boilerplate); files it
          changes should match [metadata] required_output_files, and each declared file must be produced.
    FAIL: uses hidden tests, or a declared output is never produced. WARN: undeclared outputs."""
    t = ctx.task
    solve = (t.dir / "solution" / "solve.sh").read_text() if (t.dir / "solution" / "solve.sh").is_file() else ""
    uses_tests = [l.strip() for l in solve.splitlines()
                  if re.search(r"\$\{?TESTS_DIR|/tests\b", l) and not re.match(r"\s*TESTS_DIR=", l)]
    declared = set(t.meta.get("required_output_files", []))
    changed = set(ctx.oracle_changes())
    details = [f"solve.sh uses the hidden tests: `{l[:90]}`" for l in uses_tests]
    not_made = sorted(declared - changed)
    extra = sorted(changed - declared) if declared else []
    details += [f"declared output {f} is not produced by the oracle" for f in not_made]
    details += [f"oracle changes undeclared file {f}" for f in extra]
    if uses_tests:
        return _r("oracle_hygiene", 1, "FAIL", "reference solution reads the hidden tests",
                  "make solve.sh produce the answer without reading tests/", details)
    if not_made or extra:  # metadata mismatch: wrong, but the task itself can still be graded
        return _r("oracle_hygiene", 1, "WARN", "task.toml required_output_files doesn't match what the oracle writes",
                  "make [metadata] required_output_files list exactly the files the solution produces", details)
    return _r("oracle_hygiene", 1, "PASS", f"oracle writes exactly {sorted(changed)} and never reads tests/")


# ----------------------------------------------------------------------------- Tier 2: Part 1 + reliability


def _repeat(ctx: Ctx, check: str, action, label: str):
    key = (label,)
    if key not in ctx.cache:
        ctx.cache[key] = [ctx.trial(check, f"{label}-run-{i}", action) for i in range(1, ctx.runs + 1)]
    return ctx.cache[key]


def check_nop(ctx: Ctx) -> CheckResult:
    """NOP (Part 1): does a blank answer score 0?
    WHY:  if the untouched starter already passes, every agent 'solves' it by doing nothing.
    HOW:  run the empty action --runs times through the harness.
    FAIL: NOP scored 1 in any run."""
    runs = _repeat(ctx, "nop", NOP, "nop")
    scores = [r.score for r in runs]
    if any(scores):
        return _r("nop", 2, "FAIL", f"doing nothing scores 1 ({sum(scores)}/{len(scores)} runs)",
                  "the starter already satisfies the tests: make the starter wrong or the tests stricter",
                  [f"scores: {scores}"])
    return _r("nop", 2, "PASS", f"doing nothing scores 0 in all {len(scores)} runs")


def check_oracle(ctx: Ctx) -> CheckResult:
    """ORACLE (Part 1): does the answer key score 1?
    WHY:  if the reference solution fails, the task is unsolvable as graded (or the key is wrong).
    HOW:  run solution/solve.sh --runs times through the harness.
    FAIL: the oracle scored 0 in any run (the failing tests are listed)."""
    runs = _repeat(ctx, "oracle", ORACLE, "oracle")
    scores = [r.score for r in runs]
    if not all(scores):
        bad = next(r for r in runs if not r.score)
        from .evidence import failing_tests
        why = bad.error or ", ".join(failing_tests(bad.stdout)[:5]) or "reward 0"
        return _r("oracle", 2, "FAIL", f"reference solution scores 0 in {scores.count(0)}/{len(scores)} runs ({why})",
                  "fix solution/solve.sh or the tests so the answer key passes", [f"scores: {scores}"])
    return _r("oracle", 2, "PASS", f"reference solution scores 1 in all {len(scores)} runs")


def check_flaky(ctx: Ctx) -> CheckResult:
    """FLAKY: same answer, same score, every time?
    WHY:  a grader that changes its mind on identical input gives noisy rewards for training and eval.
    HOW:  compare the scores (and failing tests) across the repeated NOP and ORACLE runs.
    FAIL: any difference between identical runs."""
    found = []
    for label in ("nop", "oracle"):
        runs = ctx.cache.get((label,), [])
        from .evidence import failing_tests
        sig = [(r.score, tuple(failing_tests(r.stdout))) for r in runs]
        if len(set(sig)) > 1:
            found.append(f"{label}: scores {[s for s, _ in sig]}, failing tests vary: "
                         f"{sorted({t for _, ts in sig for t in ts})}")
    if found:
        return _r("flaky", 2, "FAIL", "identical runs gave different results", "make the tests deterministic "
                  "(seed randomness, remove time/order dependence)", found)
    return _r("flaky", 2, "PASS", f"identical results across {ctx.runs} NOP + {ctx.runs} ORACLE runs")


# ----------------------------------------------------------------------------- Tier 3: can the grader be fooled?


def check_stub(ctx: Ctx) -> CheckResult:
    """STUB PROBE: do trivial implementations score 0?
    WHY:  'return None' passing means the tests check almost nothing.
    HOW:  replace every function body in the starter's .py files with return None / raise / return-first-arg.
    WARN: any stub scores 1."""
    passed = []
    for label, files in probes.stubs(ctx.task):
        r = ctx.trial("stub", label, write_files_action(files))
        if r.score:
            passed.append(label)
    if passed:
        return _r("stub", 3, "WARN", f"trivial implementations pass: {', '.join(passed)}",
                  "add tests that a do-nothing implementation cannot pass", passed)
    return _r("stub", 3, "PASS", "every trivial implementation scores 0")


def check_mutation(ctx: Ctx) -> CheckResult:
    """MUTATION: do small breaks of the answer key fail?
    WHY:  if the oracle with a line deleted or a comparison flipped still scores 1, the tests are too loose and
          a model can be rewarded for a wrong answer.
    HOW:  up to 8 mutants of the lines the oracle changed (stillborn ones dropped), each run through the harness.
    WARN: a mutant survives (some mutants are genuinely equivalent, hence WARN not FAIL)."""
    muts = probes.mutants(ctx.task, ctx.oracle_changes())
    if not muts:
        return _r("mutation", 3, "SKIPPED", "the oracle changes no Python lines that can be mutated")
    survived = []
    for label, files, desc in muts:
        r = ctx.trial("mutation", label, write_files_action(files), {"mutant": desc})
        if r.score:
            survived.append(desc)
    if survived:
        return _r("mutation", 3, "WARN", f"{len(survived)}/{len(muts)} broken versions of the answer key still pass",
                  "add tests that catch these changes", survived)
    return _r("mutation", 3, "PASS", f"all {len(muts)} mutants fail the tests")


def check_cheat(ctx: Ctx) -> CheckResult:
    """CHEAT: can the verifier be gamed by files the agent is allowed to write?
    WHY:  models find shortcuts; a verifier that runs agent-controlled config rewards hacking, not solving.
    HOW:  write a force-pass conftest.py / a no-test pytest.ini into the app dir, then run the verifier.
    FAIL: any cheat scores 1."""
    accepted = []
    for label, desc, action in probes.TASK_CHEATS:
        r = ctx.trial("cheat", label, action, {"cheat": desc})
        if r.score:
            accepted.append(f"{label}: {desc}")
    if accepted:
        return _r("cheat", 3, "FAIL", f"the verifier accepts a cheat: {accepted[0]}",
                  "run pytest on the tests directory only, with a clean rootdir (not `pytest .` in the agent's "
                  "dir) so agent files can't configure the test run", accepted)
    return _r("cheat", 3, "PASS", f"all {len(probes.TASK_CHEATS)} cheats score 0")


def check_verifier_isolation(ctx: Ctx) -> CheckResult:
    """VERIFIER ISOLATION (systemic): holes in how every verifier is run, not in one task.
    WHY:  same as cheat, but these work through the shared test.sh/harness setup, so they hit all tasks.
    HOW:  pre-write reward.json (preferred over reward.txt); drop a sitecustomize.py on the verifier PYTHONPATH.
    WARN: reported per task so it's visible, flagged as a dataset-level fix."""
    accepted = []
    for label, desc, action in probes.SYSTEMIC_CHEATS:
        r = ctx.trial("verifier_isolation", label, action, {"cheat": desc})
        if r.score:
            accepted.append(f"{label}: {desc}")
    if accepted:
        return _r("verifier_isolation", 3, "WARN", f"{len(accepted)} dataset-wide cheat(s) work here",
                  "dataset-level fix: clear /logs/verifier before running tests and always write reward.json; run "
                  "pytest with `python -I` or without the agent's dir on PYTHONPATH", accepted)
    return _r("verifier_isolation", 3, "PASS", "no dataset-wide cheat works")


# ----------------------------------------------------------------------------- Tier 3: LLM (only PASS/WARN/ERROR)


def _agent_view(ctx: Ctx) -> str:
    files = "\n\n".join(f'<file path="{p}">\n{t}\n</file>' for p, t in ctx.task.starter_files.items())
    return f"<instruction>\n{ctx.task.instruction}\n</instruction>\n\n<starter_files>\n{files}\n</starter_files>"


_FILES_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["files", "summary"],
                 "properties": {"summary": {"type": "string"},
                                "files": {"type": "array", "items": {
                                    "type": "object", "additionalProperties": False, "required": ["path", "content"],
                                    "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}}}}


def _llm_solution(ctx: Ctx, check: str, system: str):
    data, rec = llm.ask_json(system, _agent_view(ctx), _FILES_SCHEMA)
    ctx.ev.save_llm(check, rec)
    if data is None:
        return None, rec.get("error", "no response")
    allowed = set(ctx.task.starter_files)
    files = {f["path"]: f["content"] for f in data.get("files", []) if f["path"] in allowed}
    if not files:
        return None, "LLM returned no usable files"
    return ctx.trial(check, check.removeprefix("llm_").replace("_", "-"), write_files_action(files),
                     {"llm_summary": data.get("summary", "")}), None


def check_llm_spec_tests(ctx: Ctx) -> CheckResult:
    """LLM SPEC vs TESTS: do the tests grade what the instruction says?
    WHY:  tests that require behaviour the instruction never states are unfair (no agent could know);
          stated requirements with no test are loose.
    HOW:  the LLM reads instruction + tests and lists both kinds of mismatch.
    WARN: any test requires something the instruction doesn't state."""
    tests = "\n\n".join(f'<file path="{p.name}">\n{p.read_text()}\n</file>' for p in (ctx.task.dir / "tests").glob("*.py"))
    schema = {"type": "object", "additionalProperties": False, "required": ["unstated", "untested"],
              "properties": {k: {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                                            "required": ["test_or_requirement", "explanation"],
                                                            "properties": {"test_or_requirement": {"type": "string"},
                                                                           "explanation": {"type": "string"}}}}
                             for k in ("unstated", "untested")}}
    system = ("You review coding tasks. 'unstated': behaviour a test REQUIRES that the instruction does not state or "
              "clearly imply (an agent reading only the instruction could not know it). 'untested': explicit "
              "instruction requirements no test checks. Be strict and concrete; empty lists are fine.")
    data, rec = llm.ask_json(system, f"<instruction>\n{ctx.task.instruction}\n</instruction>\n\n<tests>\n{tests}\n</tests>", schema)
    ctx.ev.save_llm("llm_spec_tests", rec)
    if data is None:
        return _r("llm_spec_tests", 3, "ERROR", f"LLM call failed: {rec.get('error')}")
    det = [f"unstated: {x['test_or_requirement']} — {x['explanation']}" for x in data["unstated"]]
    det += [f"untested: {x['test_or_requirement']} — {x['explanation']}" for x in data["untested"]]
    if data["unstated"]:
        return _r("llm_spec_tests", 3, "WARN", f"tests require {len(data['unstated'])} thing(s) the instruction "
                  "doesn't state (LLM, needs human review)", "state these requirements in instruction.md or drop "
                  "the tests", det)
    return _r("llm_spec_tests", 3, "PASS", f"no unstated requirements found ({len(data['untested'])} untested noted)", "", det)


def check_llm_independent_solve(ctx: Ctx) -> CheckResult:
    """LLM INDEPENDENT SOLVE: can the task be solved from what the agent sees?
    WHY:  if a careful solver given only instruction + starter fails, the spec is unclear or the grader too strict.
    HOW:  the LLM writes a solution from the agent's view only; run it through the harness.
    WARN: it fails (failing tests listed for human review)."""
    r, err = _llm_solution(ctx, "llm_independent_solve", "Solve the task. You see only the instruction and starter "
                           "files. Return the complete new contents of each starter file you change.")
    if r is None:
        return _r("llm_independent_solve", 3, "ERROR", f"LLM step failed: {err}")
    if not r.score:
        from .evidence import failing_tests
        return _r("llm_independent_solve", 3, "WARN", "an independent solution written from the instruction fails "
                  "(spec unclear, hidden requirement, or grader too strict; needs human review)",
                  "compare the failing tests with the instruction", failing_tests(r.stdout)[:10])
    return _r("llm_independent_solve", 3, "PASS", "an independent solution written from the instruction passes")


def check_llm_fake_fix(ctx: Ctx) -> CheckResult:
    """LLM FAKE FIX: does hard-coding the instruction's examples pass?
    WHY:  if special-casing the visible examples scores 1, the hidden tests are too narrow to reward real work.
    HOW:  the LLM writes a deliberately wrong solution that only handles the instruction's examples.
    WARN: it scores 1."""
    r, err = _llm_solution(ctx, "llm_fake_fix", "Write a deliberately WRONG solution: hard-code / special-case only "
                           "the examples visible in the instruction and leave the general logic broken. Return the "
                           "complete contents of each starter file you change.")
    if r is None:
        return _r("llm_fake_fix", 3, "ERROR", f"LLM step failed: {err}")
    if r.score:
        return _r("llm_fake_fix", 3, "WARN", "a hard-coded fake solution passes the tests",
                  "add hidden test cases beyond the instruction's examples")
    return _r("llm_fake_fix", 3, "PASS", "a hard-coded fake solution fails the tests")


TIER1 = [check_structure, check_env_leak, check_dockerfile_parity, check_oracle_hygiene]
TIER2 = [check_nop, check_oracle, check_flaky]
TIER3 = [check_stub, check_mutation, check_cheat, check_verifier_isolation]
TIER3_LLM = [check_llm_spec_tests, check_llm_independent_solve, check_llm_fake_fix]


# ----------------------------------------------------------------------------- added checks


def _test_sources(ctx) -> dict[str, str]:
    return {p.name: p.read_text() for p in (ctx.task.dir / "tests").glob("*.py")}


def check_spec_coverage(ctx: Ctx) -> CheckResult:
    """SPEC COVERAGE: do the tests use names the agent was never told about?
    WHY:  if a test imports `format_money` or passes `currency=` and neither the instruction nor the starter
          mentions it, no agent can know to write it: the task is unsolvable as specified.
    HOW:  read tests/*.py with `ast`: names imported from the starter's modules, attributes used on those
          modules, and keyword arguments passed to them. Each must appear in instruction.md or the starter files.
    FAIL: some are in neither (the agent can't see them anywhere)."""
    import ast as _ast
    t = ctx.task
    modules = {p.rsplit("/", 1)[-1].removesuffix(".py") for p in t.starter_files if p.endswith(".py")}
    visible = t.instruction + "\n" + "\n".join(t.starter_files.values())
    used: dict[str, str] = {}
    for fname, src in _test_sources(ctx).items():
        try:
            tree = _ast.parse(src)
        except SyntaxError:
            continue
        api = set()  # names that refer to the task's own code
        for node in _ast.walk(tree):
            if isinstance(node, _ast.ImportFrom) and node.module in modules:
                for a in node.names:
                    used.setdefault(a.name, f"{fname}: imported from {node.module}")
                    api.add(a.asname or a.name)
            elif isinstance(node, _ast.Import):
                api.update(a.asname or a.name for a in node.names if a.name in modules)
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Attribute) and isinstance(node.value, _ast.Name) and node.value.id in api \
                    and node.value.id in modules:
                used.setdefault(node.attr, f"{fname}: {node.value.id}.{node.attr}")
            if isinstance(node, _ast.Call):
                f = node.func
                callee = f.id if isinstance(f, _ast.Name) else f.attr if isinstance(f, _ast.Attribute) else ""
                base = f.value.id if isinstance(f, _ast.Attribute) and isinstance(f.value, _ast.Name) else ""
                if callee in api or base in api:
                    for kw in node.keywords:
                        if kw.arg:
                            used.setdefault(f"{kw.arg}=", f"{fname}: keyword {kw.arg}= in a call to {callee}")
    missing = [f"{n} ({where})" for n, where in sorted(used.items())
               if not re.search(rf"(?<!\w){re.escape(n.rstrip('='))}(?!\w)", visible)]
    if missing:
        return _r("spec_coverage", 1, "FAIL", f"tests require {len(missing)} name(s) that appear in neither "
                  "instruction.md nor the starter files", "document these functions/arguments in instruction.md "
                  "(or add them to the starter)", missing)
    return _r("spec_coverage", 1, "PASS", f"all {len(used)} names the tests use are visible to the agent")


def check_thin_tests(ctx: Ctx) -> CheckResult:
    """THIN TESTS: are there enough tests to mean anything?
    WHY:  one or two test functions can't cover an instruction's requirements; a model gets rewarded for
          satisfying a few examples.
    HOW:  count `def test_*` functions in tests/ (module level and in classes).
    WARN: fewer than 3."""
    n = sum(len(re.findall(r"^\s*def test_\w+", s, re.MULTILINE)) for s in _test_sources(ctx).values())
    if n < 3:
        return _r("thin_tests", 1, "WARN", f"only {n} test function(s)", "add tests for each requirement in the "
                  "instruction (edge cases, error paths)")
    return _r("thin_tests", 1, "PASS", f"{n} test functions")


def check_test_order(ctx: Ctx) -> CheckResult:
    """TEST ORDER: does each test pass on its own, and in reverse order?
    WHY:  tests that share state (a module-level cart, a cache) pass or fail depending on what ran before,
          so a correct answer can be scored 0 when the order changes.
    HOW:  with the oracle's files: normal run, every test alone, and the suite reversed (direct pytest runs).
    WARN: a test that passes normally fails alone or reversed."""
    from . import direct
    normal = direct.run_pytest(ctx, "test_order", "normal-order")
    passing = [t for t, v in normal.items() if v == "passed"]
    if not passing:
        return _r("test_order", 2, "SKIPPED", "no test passes in the normal run, so order can't be judged")
    bad = []
    rev = direct.run_pytest(ctx, "test_order", "reversed-order", reverse=True)
    bad += [f"{t} fails when the suite runs in reverse" for t in passing if rev.get(t) == "failed"]
    for t in passing:
        alone = direct.run_pytest(ctx, "test_order", f"alone-{t.split('::')[-1]}", select=[t])
        if alone.get(t) == "failed":
            bad.append(f"{t} fails when run alone")
    if bad:
        return _r("test_order", 2, "WARN", "tests share state / depend on order", "make every test set up its own "
                  "state (fixtures, reset module-level globals)", bad)
    return _r("test_order", 2, "PASS", f"all {len(passing)} tests pass alone and in reverse order")


def check_timezone(ctx: Ctx) -> CheckResult:
    """TIMEZONE: does the result depend on the machine's time zone?
    WHY:  graders run on machines in different zones; a test that passes in UTC and fails in Auckland gives
          different scores to the same answer.
    HOW:  run the oracle's files + tests with TZ=UTC and TZ=Pacific/Auckland (direct pytest; the harness drops TZ).
    WARN: per-test results differ."""
    from . import direct
    utc = direct.run_pytest(ctx, "timezone", "tz-utc", tz="UTC")
    akl = direct.run_pytest(ctx, "timezone", "tz-pacific-auckland", tz="Pacific/Auckland")
    diff = [f"{t}: UTC {utc.get(t)} vs Pacific/Auckland {akl.get(t)}" for t in sorted(set(utc) | set(akl))
            if utc.get(t) != akl.get(t)]
    if diff:
        return _r("timezone", 2, "WARN", "time-zone dependent; specify UTC", "state the time zone in the instruction "
                  "and make the tests/solution use UTC explicitly", diff)
    return _r("timezone", 2, "PASS", f"same results for {len(utc)} tests in UTC and Pacific/Auckland")


TIER1 = [check_structure, check_env_leak, check_dockerfile_parity, check_oracle_hygiene, check_spec_coverage,
         check_thin_tests]
TIER2_EXTRA = [check_test_order, check_timezone]
