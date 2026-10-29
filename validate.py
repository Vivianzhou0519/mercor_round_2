"""Validate every Harbor task: python validate.py [tasks] [--runs 3] [--llm] [--only t05,t06] [--jobs 6]

Writes results/<name>/ (report.html, report.json, summary.txt, and per task/check evidence folders).
Never modifies tasks/: every file is hashed before and after; a change exits with code 3.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import os
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from harness import load_tasks

from validator import checks as C
from validator import report
from validator.evidence import CheckResult, TaskEvidence

SIMILAR = 0.85


def tree_hash(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            h.update(str(p.relative_to(root)).encode() + p.read_bytes())
    return h.hexdigest()


def run_check(fn, ctx) -> CheckResult:
    """Run a check; a crash in OUR code is ERROR (retried once), never blamed on the task."""
    for attempt in (1, 2):
        t0 = time.time()
        try:
            r = fn(ctx)
        except Exception as e:
            r = CheckResult(fn.__name__.removeprefix("check_"), 0, "ERROR", f"validator error: {type(e).__name__}: {e}",
                            details=traceback.format_exc().splitlines()[-4:])
        r.seconds = time.time() - t0
        if r.status != "ERROR" or attempt == 2:
            if r.status == "ERROR" and attempt == 2:
                r.reason += " (failed twice; rerun later)"
            return r


def skip(fn, tier, why) -> CheckResult:
    return CheckResult(fn.__name__.removeprefix("check_"), tier, "SKIPPED", why)


def validate_task(task, out: Path, args) -> list[CheckResult]:
    """Tier order with the skip rule: always run all of Tier 1; skip a later check only if an earlier result
    makes it impossible or meaningless, naming the blocker; Tier 3 only if Tier 2 passed."""
    ev = TaskEvidence(out, task.name)
    ctx = C.Ctx(task, ev, args.runs, args.llm)
    res: list[CheckResult] = [run_check(f, ctx) for f in C.TIER1]

    blocked = [f for f in ("environment/Dockerfile", "tests/test.sh") if not (task.dir / f).is_file()]
    has_oracle = (task.dir / "solution" / "solve.sh").is_file()
    for f in C.TIER2:
        if blocked:
            res.append(skip(f, 2, f"blocked: missing {', '.join(blocked)}"))
        elif f is C.check_oracle and not has_oracle:
            res.append(skip(f, 2, "blocked: no solution/solve.sh"))
        else:
            res.append(run_check(f, ctx))

    if args.llm:  # reading-only LLM check: useful even for broken tasks (it can explain an oracle failure)
        res.append(run_check(C.check_llm_spec_tests, ctx))
    by = {r.name: r for r in res}
    t2_bad = [n for n in ("nop", "oracle", "flaky") if by.get(n) and by[n].status != "PASS"]
    tier3 = C.TIER3 + ([C.check_llm_independent_solve, C.check_llm_fake_fix] if args.llm else [])
    for f in tier3:
        res.append(skip(f, 3, f"blocked by Tier 2: {', '.join(f'{n} {by[n].status}' for n in t2_bad)}")
                   if t2_bad else run_check(f, ctx))
    if not args.llm:
        for f in C.TIER3_LLM:
            res.append(skip(f, 3, "LLM check; run with --llm"))
    for r in res:
        ev.write_result(r)
    return res


def duplicates(tasks) -> dict[str, CheckResult]:
    """DUPLICATES (folder-level): near-identical tasks inflate a dataset and leak between train/test splits.
    HOW: instruction similarity (difflib) and identical solve.sh. WARN on the later task of a pair."""
    out = {}
    sol = {t.name: (t.dir / "solution" / "solve.sh").read_bytes() if (t.dir / "solution" / "solve.sh").is_file() else b""
           for t in tasks}
    for i, t in enumerate(tasks):
        hits = []
        for prev in tasks[:i]:
            sim = difflib.SequenceMatcher(None, prev.instruction, t.instruction, autojunk=False).ratio()
            if sim > SIMILAR:
                hits.append(f"instruction {sim:.0%} similar to {prev.name}")
            elif sol[t.name] and sol[t.name] == sol[prev.name]:
                hits.append(f"identical solve.sh to {prev.name}")
        out[t.name] = (CheckResult("duplicates", 1, "WARN", "possible duplicate: " + "; ".join(hits),
                                   "confirm it tests something different, or drop one", hits) if hits else
                       CheckResult("duplicates", 1, "PASS", f"no near-duplicate among {len(tasks)} tasks"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tasks", nargs="?", default="tasks")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--llm", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    if args.llm and not os.environ.get("OPENROUTER_API_KEY"):  # Claude Code's shell may not load ~/.zshrc
        os.environ["OPENROUTER_API_KEY"] = subprocess.run(["zsh", "-ic", 'printf %s "$OPENROUTER_API_KEY"'],
                                                          capture_output=True, text=True).stdout
    root = Path(args.tasks)
    tasks = [t for t in load_tasks(root) if not args.only or any(t.name.startswith(o) for o in args.only.split(","))]
    name = Path(args.out).name if args.out else root.resolve().name + ("-llm" if args.llm else "")
    out = Path("results") / name
    i = 2
    while out.exists() and not args.out:
        out = Path("results") / f"{name}-run-{i}"
        i += 1
    out.mkdir(parents=True, exist_ok=True)
    before = tree_hash(root)
    started = datetime.now().isoformat(timespec="seconds")
    dups = duplicates(tasks) if len(tasks) > 1 else {}
    with ThreadPoolExecutor(args.jobs) as pool:
        futs = {t.name: pool.submit(validate_task, t, out, args) for t in tasks}
        results = {}
        for t in tasks:
            res = futs[t.name].result()
            if t.name in dups:
                res.insert(len(C.TIER1), dups[t.name])
                TaskEvidence(out, t.name).write_result(dups[t.name])
            results[t.name] = [r.to_dict() for r in res]
            print(f"{t.name:<26} " + " ".join(f"{r.name}={r.status}" for r in res if r.status != "PASS"), flush=True)
    unchanged = tree_hash(root) == before
    report.write(out, results, {"started": started, "command": " ".join(["python"] + sys.argv),
                                "tasks_unchanged": unchanged})
    print(f"\nReport: {out / 'report.html'}   tasks/ unchanged: {unchanged}")
    if not unchanged:
        print("INTEGRITY ERROR: tasks/ changed during validation", file=sys.stderr)
        return 3
    return 1 if any(c["status"] == "FAIL" for cs in results.values() for c in cs) else 0


if __name__ == "__main__":
    sys.exit(main())
