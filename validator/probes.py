"""Probes: submissions we construct on purpose. Each one is just an action run through the harness.

stubs    - "do-nothing" implementations of the starter's functions. Must score 0.
mutants  - the oracle's code with one small break. Must score 0, or the tests are too loose.
cheats   - actions that try to game the verifier instead of solving. Must score 0.
"""

from __future__ import annotations

import ast
import difflib
import re

from harness import ORACLE, materialize, write_files_action

_CMP = re.compile(r"(?<![<>=!])(==|!=|<=|>=|<|>)(?![<>=])")
_NEGATE = {"==": "!=", "!=": "==", "<=": ">", ">=": "<", "<": ">=", ">": "<="}
_NO_MUTATE = re.compile(r"^\s*($|#|def |class |@|import |from |\"\"\"|'''|return$|pass$|else:|try:|finally:)")


def oracle_changes(task) -> dict[str, str]:
    """Files the reference solution creates or changes: {path: new text}. Uses materialize (no verifier)."""
    before = task.starter_files
    after = materialize(task.dir, ORACLE)
    return {p: t for p, t in after.items() if before.get(p) != t and "__pycache__" not in p}


def stubs(task) -> list[tuple[str, dict]]:
    """Replace every top-level function body in the starter's .py files with a trivial body.
    WHY: if 'return None' scores 1, the tests barely test anything."""
    out = []
    for body_src, label in (("return None", "return-none"), ("raise NotImplementedError", "raise"),
                            ("return args[0] if args else None", "return-first-arg")):
        files = {}
        for path, text in task.starter_files.items():
            if not path.endswith(".py"):
                continue
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            changed = False
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if label == "return-first-arg":  # accept anything so 'return args[0]' is valid
                        node.args = ast.arguments(posonlyargs=[], args=[], vararg=ast.arg("args"), kwonlyargs=[],
                                                  kw_defaults=[], kwarg=ast.arg("kwargs"), defaults=[])
                    node.body = ast.parse(body_src).body
                    changed = True
            if changed:
                files[path] = ast.unparse(tree) + "\n"
        if files:
            out.append((f"stub-{label}", files))
    return out


def mutants(task, changed: dict[str, str], limit: int = 8) -> list[tuple[str, dict, str]]:
    """Small breaks of the oracle's code: delete one line (-> `pass`) or negate one comparison.
    Only lines the oracle added/changed; skip comments, headers, imports; drop mutants that don't compile.
    Returns (label, files, description)."""
    found = []
    starter = task.starter_files
    for path, new in changed.items():
        if not path.endswith(".py"):
            continue
        old_lines = starter.get(path, "").splitlines()
        new_lines = new.splitlines()
        sm = difflib.SequenceMatcher(None, old_lines, new_lines)
        touched = [j for tag, _i1, _i2, j1, j2 in sm.get_opcodes() if tag in ("replace", "insert") for j in range(j1, j2)]
        for j in touched:
            line = new_lines[j]
            if _NO_MUTATE.match(line) or line.rstrip().endswith(":") and not _CMP.search(line):
                continue
            indent = line[: len(line) - len(line.lstrip())]
            variants = [(f"{indent}pass", f"{path}:{j + 1} delete `{line.strip()[:60]}`")]
            m = _CMP.search(line)
            if m:
                flipped = line[: m.start()] + _NEGATE[m.group(1)] + line[m.end():]
                variants.append((flipped, f"{path}:{j + 1} `{line.strip()[:50]}` -> `{flipped.strip()[:50]}`"))
            for repl, desc in variants:
                lines = list(new_lines)
                lines[j] = repl
                text = "\n".join(lines) + "\n"
                try:
                    compile(text, path, "exec")
                except SyntaxError:
                    continue  # stillborn: a syntax error proves nothing about the tests
                found.append((path, text, desc))
    if len(found) > limit:  # spread across the file instead of only the first lines
        step = len(found) / limit
        found = [found[int(i * step)] for i in range(limit)]
    return [(f"mutant-{i}", {p: t}, d) for i, (p, t, d) in enumerate(found, 1)]


# Cheats an agent could try. Only the app dir is writable by the agent; tests/ and solution/ are hidden.
CONFTEST_FORCE_PASS = '''import pytest

def pytest_sessionfinish(session, exitstatus):
    # cheat: report success no matter what the tests said
    session.exitstatus = 0
'''

TASK_CHEATS = [
    ("cheat-conftest-force-pass", "a conftest.py in the app dir that forces pytest to exit 0",
     write_files_action({"conftest.py": CONFTEST_FORCE_PASS})),
    ("cheat-pytest-ini-no-tests", "a pytest.ini in the app dir that collects nothing and ignores failures",
     write_files_action({"pytest.ini": "[pytest]\naddopts = -p no:python --co -q\n"})),
]

# Holes in how the verifier is run, not in any one task: tried once per task but reported as systemic.
SYSTEMIC_CHEATS = [
    ("cheat-prewrite-reward-json", "write reward.json = 1 into the verifier log dir before the tests run "
     "(the harness prefers reward.json, test.sh only writes reward.txt)",
     '#!/bin/bash\nmkdir -p "$HARBOR_LOGS_DIR"\necho \'{"reward": 1}\' > "$HARBOR_LOGS_DIR/reward.json"\n'),
    ("cheat-sitecustomize-exit-0", "a sitecustomize.py in the app dir (which is on the verifier's PYTHONPATH) "
     "that forces every Python process to exit 0",
     write_files_action({"sitecustomize.py": "import atexit, os\natexit.register(lambda: os._exit(0))\n"})),
]
