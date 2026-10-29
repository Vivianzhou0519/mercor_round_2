"""Task harness -- PROVIDED. You should not need to modify this file.

The tasks are in Harbor format (https://www.harborframework.com/docs/tasks). Harbor
normally runs each task in a Docker container; this harness runs the same task locally
in a temp directory so a full sweep takes seconds instead of minutes. It honours the
Harbor contract: it executes `solution/solve.sh` and `tests/test.sh` and reads the
reward the verifier writes to `reward.json` / `reward.txt`.

Public API
----------
load_tasks(root)                              -> list[Task]
run_task(task_dir, action=NOP, timeout=None)  -> int          # 1 if the verifier rewards 1
run_task_detailed(task_dir, action, timeout)  -> RunResult    # same run, with output
write_files_action({"f.py": "..."})           -> str          # build an action script
materialize(task_dir, action)                 -> dict         # the workdir after an action
NOP                                           -> str          # the agent does nothing
ORACLE                                        -> sentinel     # run solution/solve.sh

A `Task` exposes:
    .dir           pathlib.Path to the task folder
    .name          folder name
    .instruction   contents of instruction.md
    .meta          parsed task.toml, flattened: [task] + [metadata] keys
    .config        the full parsed task.toml

An **action** is a bash script, run with the agent's working directory as cwd. That is
what an agent's turn amounts to here. `NOP` is the empty script; `ORACLE` is the
sentinel meaning "run the task's own solution/solve.sh".

Sanity check your environment with:

    python harness.py selfcheck
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info < (3, 11):  # pragma: no cover
    raise RuntimeError("this harness needs Python 3.11+ (it uses tomllib)")

import tomllib

__all__ = [
    "Task",
    "RunResult",
    "NOP",
    "NOP_PATCH",
    "ORACLE",
    "load_tasks",
    "run_task",
    "run_task_detailed",
    "materialize",
    "write_files_action",
]


class _Oracle:
    def __repr__(self) -> str:
        return "ORACLE"


#: An action that does nothing. Running a task with this measures whether the verifier
#: already rewards the unmodified starter code.
NOP = ""

#: Deprecated alias kept so older write-ups still read correctly.
NOP_PATCH = NOP

#: Sentinel action meaning "run this task's solution/solve.sh" -- Harbor's oracle agent.
ORACLE = _Oracle()

DEFAULT_TIMEOUT = 120


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #


@dataclass
class Task:
    dir: Path
    name: str
    instruction: str
    meta: dict
    config: dict = field(repr=False, default_factory=dict)

    @property
    def environment_dir(self) -> Path:
        """Files the agent starts from. Everything here except the Dockerfile."""
        return self.dir / "environment"

    @property
    def tests_dir(self) -> Path:
        return self.dir / "tests"

    @property
    def solution_dir(self) -> Path:
        return self.dir / "solution"

    @property
    def starter_files(self) -> dict:
        """{relative path: text} for the code the agent is given."""
        return _read_tree(self.environment_dir, skip={"Dockerfile", "docker-compose.yaml"})

    @property
    def verifier_timeout(self) -> float:
        return float(self.config.get("verifier", {}).get("timeout_sec", DEFAULT_TIMEOUT))


def load_tasks(root) -> list[Task]:
    """Load every Harbor task folder directly under `root`, sorted by name."""
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"no such task root: {root}")

    tasks = []
    for entry in sorted(p for p in root.iterdir() if p.is_dir()):
        if entry.name.startswith(".") or entry.name == "__pycache__":
            continue
        if not (entry / "task.toml").is_file():
            continue
        try:
            config = tomllib.loads((entry / "task.toml").read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"{entry.name}: task.toml is not valid TOML: {exc}") from exc

        meta = dict(config.get("task", {}))
        meta.update(config.get("metadata", {}))
        tasks.append(
            Task(
                dir=entry,
                name=entry.name,
                instruction=_read(entry / "instruction.md"),
                meta=meta,
                config=config,
            )
        )
    return tasks


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _read_tree(root: Path, skip: set | None = None) -> dict:
    skip = skip or set()
    if not root.is_dir():
        return {}
    return {
        str(p.relative_to(root)): p.read_text(encoding="utf-8", errors="replace")
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name not in skip and "__pycache__" not in p.parts
    }


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #


def write_files_action(files: dict) -> str:
    """Build an action script that writes `{relative path: text}` into the workdir.

    Useful for probing a task with a submission you construct yourself, e.g. a stub
    that implements nothing.
    """
    sentinel = "__ACTION_EOF__"
    lines = ["#!/bin/bash", "set -euo pipefail", ""]
    for rel, body in files.items():
        if sentinel in body:
            raise ValueError(f"{rel}: content collides with the heredoc sentinel")
        parent = str(Path(rel).parent)
        if parent != ".":
            lines.append(f'mkdir -p "{parent}"')
        text = body if body.endswith("\n") else body + "\n"
        lines.append(f"cat > '{rel}' << '{sentinel}'\n{text}{sentinel}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Running
# --------------------------------------------------------------------------- #


@dataclass
class RunResult:
    score: int
    reward: float | None
    action_ok: bool
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    error: str = ""

    def __bool__(self) -> bool:  # pragma: no cover - convenience only
        return bool(self.score)


def run_task(task_dir, action=NOP, timeout: float | None = None) -> int:
    """Run `action` against the task and return the verifier's reward as 0 or 1."""
    return run_task_detailed(task_dir, action, timeout).score


def run_task_detailed(task_dir, action=NOP, timeout: float | None = None) -> RunResult:
    """Same as `run_task`, but returns the verifier output for debugging."""
    task_dir = Path(task_dir)
    environment = task_dir / "environment"
    tests = task_dir / "tests"
    if not environment.is_dir():
        return _fail(f"{task_dir.name}: no environment/ directory")
    if not (tests / "test.sh").is_file():
        return _fail(f"{task_dir.name}: no tests/test.sh")

    if timeout is None:
        try:
            config = tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
            timeout = float(config.get("verifier", {}).get("timeout_sec", DEFAULT_TIMEOUT))
        except (OSError, tomllib.TOMLDecodeError, TypeError, ValueError):
            timeout = DEFAULT_TIMEOUT

    work = Path(tempfile.mkdtemp(prefix=f"harbor-{task_dir.name}-"))
    try:
        app, tests_dst, logs = work / "app", work / "tests", work / "logs" / "verifier"
        app.mkdir()
        logs.mkdir(parents=True)
        for rel, body in _read_tree(environment, skip={"Dockerfile", "docker-compose.yaml"}).items():
            target = app / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        shutil.copytree(tests, tests_dst, ignore=shutil.ignore_patterns("__pycache__"))

        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(work),
            "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "HARBOR_APP_DIR": str(app),
            "HARBOR_TESTS_DIR": str(tests_dst),
            "HARBOR_LOGS_DIR": str(logs),
            "HARBOR_PYTHON": sys.executable,
        }

        # 1. the agent's turn
        if isinstance(action, _Oracle):
            solve = task_dir / "solution" / "solve.sh"
            if not solve.is_file():
                return _fail(f"{task_dir.name}: no solution/solve.sh")
            shutil.copytree(task_dir / "solution", work / "solution", dirs_exist_ok=True)
            script = work / "solution" / "solve.sh"
        else:
            script = work / "action.sh"
            script.write_text(action or "#!/bin/bash\ntrue\n", encoding="utf-8")

        done = _bash(script, cwd=app, env=env, timeout=timeout)
        if done.get("timed_out"):
            return _fail("action timed out", timed_out=True)
        if done["returncode"] != 0:
            return RunResult(
                0, None, False, done["returncode"], done["stdout"], done["stderr"],
                error="action script exited %d" % done["returncode"],
            )

        # 2. the verifier
        done = _bash(tests_dst / "test.sh", cwd=app, env=env, timeout=timeout)
        if done.get("timed_out"):
            return _fail("verifier timed out", timed_out=True)
        if "No module named pytest" in done["stderr"] + done["stdout"]:
            return _fail("pytest is not installed -- run: pip install -r requirements.txt")

        reward = _read_reward(logs)
        if reward is None:
            return RunResult(
                0, None, True, done["returncode"], done["stdout"], done["stderr"],
                error="verifier wrote no reward file",
            )
        return RunResult(
            score=1 if reward >= 1 else 0,
            reward=reward,
            action_ok=True,
            returncode=done["returncode"],
            stdout=done["stdout"],
            stderr=done["stderr"],
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


def materialize(task_dir, action=NOP, timeout: float | None = None) -> dict:
    """Run `action` and return the resulting working directory as {path: text}.

    The verifier is not run. Useful for looking at what the oracle actually produces:

        before = load_tasks("tasks")[0].starter_files
        after = materialize(task.dir, ORACLE)
    """
    task_dir = Path(task_dir)
    work = Path(tempfile.mkdtemp(prefix=f"harbor-mat-{task_dir.name}-"))
    try:
        app, logs = work / "app", work / "logs" / "verifier"
        app.mkdir()
        logs.mkdir(parents=True)
        for rel, body in _read_tree(
            task_dir / "environment", skip={"Dockerfile", "docker-compose.yaml"}
        ).items():
            target = app / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")

        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(work),
            "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "HARBOR_APP_DIR": str(app),
            "HARBOR_TESTS_DIR": str(task_dir / "tests"),
            "HARBOR_LOGS_DIR": str(logs),
            "HARBOR_PYTHON": sys.executable,
        }
        if isinstance(action, _Oracle):
            shutil.copytree(task_dir / "solution", work / "solution", dirs_exist_ok=True)
            script = work / "solution" / "solve.sh"
        else:
            script = work / "action.sh"
            script.write_text(action or "#!/bin/bash\ntrue\n", encoding="utf-8")
        _bash(script, cwd=app, env=env, timeout=timeout or DEFAULT_TIMEOUT)
        return _read_tree(app)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _fail(message: str, timed_out: bool = False) -> RunResult:
    return RunResult(0, None, False, None, "", "", timed_out=timed_out, error=message)


def _bash(script: Path, cwd: Path, env: dict, timeout: float) -> dict:
    try:
        proc = subprocess.run(
            ["bash", str(script)],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"timed_out": True, "returncode": None, "stdout": "", "stderr": ""}
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def _read_reward(logs: Path) -> float | None:
    """Harbor prefers reward.json and falls back to reward.txt."""
    as_json = logs / "reward.json"
    if as_json.is_file():
        try:
            payload = json.loads(as_json.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and "reward" in payload:
                return float(payload["reward"])
            if isinstance(payload, (int, float)):
                return float(payload)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    as_text = logs / "reward.txt"
    if as_text.is_file():
        try:
            return float(as_text.read_text(encoding="utf-8").strip())
        except ValueError:
            return None
    return None


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _selfcheck() -> int:
    try:
        import pytest  # noqa: F401
    except ImportError:
        print("FAIL: pytest is not installed. Run: pip install -r requirements.txt")
        return 1
    if shutil.which("bash") is None:
        print("FAIL: bash is not on PATH; the Harbor scripts need it")
        return 1

    root = Path(__file__).resolve().parent / "tasks"
    try:
        tasks = load_tasks(root)
    except Exception as exc:  # pragma: no cover
        print(f"FAIL: could not load tasks from {root}: {exc}")
        return 1

    print(f"pytest ok, bash ok, python {sys.version.split()[0]}")
    print(f"loaded {len(tasks)} Harbor tasks from {root}")
    if not tasks:
        return 1

    sample = tasks[0]
    nop = run_task_detailed(sample.dir, NOP)
    if nop.error:
        print(f"FAIL: harness could not run {sample.name}: {nop.error}")
        return 1
    oracle = run_task_detailed(sample.dir, ORACLE)
    if oracle.error:
        print(f"FAIL: oracle could not run for {sample.name}: {oracle.error}")
        return 1
    print(f"ran {sample.name}: NOP -> {nop.score}, ORACLE -> {oracle.score}")
    print("harness looks healthy")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selfcheck":
        raise SystemExit(_selfcheck())
    print(__doc__)
    raise SystemExit(0)
