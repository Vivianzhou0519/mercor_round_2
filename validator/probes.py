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


_NEG = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.GtE, ast.GtE: ast.Lt, ast.Gt: ast.LtE,
        ast.LtE: ast.Gt, ast.Is: ast.IsNot, ast.IsNot: ast.Is, ast.In: ast.NotIn, ast.NotIn: ast.In}


def _is_docstring(node) -> bool:
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)


def _strip_docstrings(tree):
    """Copy of the tree without docstrings, so two versions that differ only in docs compare equal."""
    import copy
    t = copy.deepcopy(tree)
    for node in ast.walk(t):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and _is_docstring(body[0]):
            node.body = body[1:] or [ast.Pass()]
    return t


def _same_behaviour(a, b) -> bool:
    return ast.dump(_strip_docstrings(a)) == ast.dump(_strip_docstrings(b))


def _trailing_return_none(node, parent_body, parent) -> bool:
    """`return` / `return None` as the last statement of a function: deleting it changes nothing."""
    return (isinstance(node, ast.Return) and (node.value is None or
            (isinstance(node.value, ast.Constant) and node.value.value is None))
            and isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)) and parent_body[-1] is node)


def _literal_init(node) -> bool:
    """`x = 0` / `x = []` / `x = ""` / `x = None`: deleting a literal initialization either raises when x is read
    before being reassigned (the mutant dies anyway) or changes nothing (a dead store, e.g. `length = 0` that the
    loop always overwrites first). Either way it says nothing about the tests, so it's not generated."""
    return (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
            and (isinstance(node.value, ast.Constant)
                 or isinstance(node.value, (ast.List, ast.Dict, ast.Tuple, ast.Set)) and not getattr(node.value, "elts", getattr(node.value, "keys", None))))


def _containers(tree):
    """(parent, field name, statement list) for every statement list in the tree, in a fixed order."""
    for parent in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            lst = getattr(parent, field, None)
            if isinstance(lst, list) and lst and isinstance(lst[0], ast.stmt):
                yield parent, field, lst


def mutants(task, changed: dict[str, str], limit: int = 8) -> list[tuple[str, dict, str]]:
    """Small breaks of the oracle's code, built with `ast` (never touching docstrings or comments):
      - delete one statement (an emptied block gets `pass`);
      - negate one comparison (== <-> !=, < <-> >=, > <-> <=, in <-> not in, is <-> is not).
    Only code on lines the oracle added or changed. Dropped: mutants that don't compile (stillborn) and mutants
    whose ast (ignoring docstrings) equals the original's (equivalent: they can't change behaviour), and deleting
    a trailing `return None`. Returns (label, files, description)."""
    import copy
    found = []
    starter = task.starter_files
    for path, new in changed.items():
        if not path.endswith(".py"):
            continue
        try:
            orig = ast.parse(new)
        except SyntaxError:
            continue
        old_lines = starter.get(path, "").splitlines()
        sm = difflib.SequenceMatcher(None, old_lines, new.splitlines())
        touched = {j + 1 for tag, _a, _b, j1, j2 in sm.get_opcodes() if tag in ("replace", "insert") for j in range(j1, j2)}

        # Statement deletions: index (container number, position) so the same spot can be found in a deep copy.
        sites = []
        for ci, (parent, field, lst) in enumerate(_containers(orig)):
            for si, node in enumerate(lst):
                if (getattr(node, "lineno", None) in touched and not _is_docstring(node)
                        and not isinstance(node, (ast.Pass, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                                  ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal))
                        and not _trailing_return_none(node, lst, parent)
                        and not _literal_init(node)):
                    sites.append(("delete", ci, si, node))
        # Comparison flips: index by position in ast.walk order.
        for wi, node in enumerate(ast.walk(orig)):
            if isinstance(node, ast.Compare) and getattr(node, "lineno", None) in touched and type(node.ops[0]) in _NEG:
                sites.append(("flip", wi, 0, node))

        for kind, a, b, node in sites:
            tree = copy.deepcopy(orig)
            if kind == "delete":
                _parent, _field, lst = list(_containers(tree))[a]
                del lst[b]
                if not lst:
                    lst.append(ast.Pass())
                desc = f"{path}:{node.lineno} delete `{ast.unparse(node).splitlines()[0][:60]}`"
            else:
                target = list(ast.walk(tree))[a]
                target.ops[0] = _NEG[type(target.ops[0])]()
                desc = f"{path}:{node.lineno} `{ast.unparse(node)[:50]}` -> `{ast.unparse(target)[:50]}`"
            if _same_behaviour(tree, orig):
                continue  # equivalent mutant: identical code once docstrings are ignored
            text = ast.unparse(tree) + "\n"
            try:
                compile(text, path, "exec")
            except SyntaxError:
                continue  # stillborn: a syntax error proves nothing about the tests
            found.append((path, text, desc))
    # Alternate deletions and comparison flips so the cap doesn't keep only one kind.
    dels = [f for f in found if " delete " in f[2]]
    flips = [f for f in found if " delete " not in f[2]]
    mixed = [x for pair in zip(dels, flips) for x in pair] + dels[len(flips):] + flips[len(dels):]
    return [(f"mutant-{i}", {p: t}, d) for i, (p, t, d) in enumerate(mixed[:limit], 1)]


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
