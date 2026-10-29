"""Direct pytest runs on the oracle's files, for checks the harness can't express: running one test alone,
reversing the test order, or setting TZ (harness.py builds its env from PATH/LANG/TMPDIR only, so TZ is lost).
Same layout as the harness: the app files in app/, the tests in tests/, PYTHONPATH=app, cwd=app."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from harness import ORACLE, materialize

REVERSE_PLUGIN = "def pytest_collection_modifyitems(items):\n    items.reverse()\n"
_RA = re.compile(r"^(PASSED|FAILED|ERROR) (\S+)", re.MULTILINE)


def oracle_files(ctx) -> dict:
    if "oracle_files" not in ctx.cache:
        ctx.cache["oracle_files"] = materialize(ctx.task.dir, ORACLE)
    return ctx.cache["oracle_files"]


def run_pytest(ctx, check: str, label: str, select: list[str] | None = None, reverse: bool = False,
               tz: str | None = None) -> dict[str, str]:
    """Run pytest on the oracle's files. Returns {file.py::test: passed|failed}; saves the run as evidence."""
    work = Path(tempfile.mkdtemp(prefix="direct-"))
    try:
        app, tests = work / "app", work / "tests"
        for rel, body in oracle_files(ctx).items():
            (app / rel).parent.mkdir(parents=True, exist_ok=True)
            (app / rel).write_text(body)
        app.mkdir(exist_ok=True)
        shutil.copytree(ctx.task.dir / "tests", tests, ignore=shutil.ignore_patterns("__pycache__"))
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(work), "LANG": os.environ.get("LANG", "C.UTF-8"),
               "PYTHONPATH": str(app), "PYTHONDONTWRITEBYTECODE": "1", "HARBOR_APP_DIR": str(app),
               "HARBOR_TESTS_DIR": str(tests), "HARBOR_LOGS_DIR": str(work / "logs")}
        if tz:
            env["TZ"] = tz
        cmd = [sys.executable, "-m", "pytest", "-q", "-rA", "-p", "no:cacheprovider"]
        if reverse:
            (work / "reverse_order.py").write_text(REVERSE_PLUGIN)
            env["PYTHONPATH"] += os.pathsep + str(work)
            cmd += ["-p", "reverse_order"]
        cmd += [str(tests / s) for s in select] if select else [str(tests)]
        t0 = time.time()
        p = subprocess.run(cmd, cwd=app, env=env, capture_output=True, text=True, timeout=300)
        out = {}
        for verdict, tid in _RA.findall(p.stdout):
            path, sep, rest = tid.partition("::")
            out[path.rsplit("/", 1)[-1] + sep + rest] = "passed" if verdict == "PASSED" else "failed"
        res = SimpleNamespace(score=int(p.returncode == 0), reward=None, action_ok=True, returncode=p.returncode,
                              stdout=p.stdout, stderr=p.stderr, timed_out=False, error="")
        ctx.ev.save_run(check, label, "# direct pytest run on the oracle's files\n" + " ".join(cmd) + "\n", res,
                        time.time() - t0, {"tz": tz, "reverse": reverse, "select": select, "tests": out})
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)
