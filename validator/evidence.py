"""Evidence trail: everything behind every verdict is saved so it can be audited without rerunning.

results/<run>/<task>/<check>/
    result.txt, result.json     STATUS, one-line REASON, FIX, TIME, details, list of runs
    runs/<name>/                one folder per harness run: action.sh, stdout.txt, stderr.txt, run.json
    llm-call.json               full prompt and raw response of any LLM call
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

STATUSES = ("PASS", "FAIL", "WARN", "ERROR", "SKIPPED")


@dataclass
class CheckResult:
    """One check's verdict. FAIL = the task is wrong; WARN = a human should look;
    ERROR = our side broke (never blamed on the task); SKIPPED = deliberately not run (says why)."""
    name: str
    tier: int
    status: str
    reason: str                 # one line, plain English
    fix: str = ""               # what the task author should change (FAIL/WARN)
    details: list[str] = field(default_factory=list)
    seconds: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-") or "x"


class TaskEvidence:
    """Writes one task's evidence. One instance per task, so tasks can run in parallel safely."""

    def __init__(self, root: Path, task_name: str):
        self.dir = root / task_name
        self.dir.mkdir(parents=True, exist_ok=True)

    def check_dir(self, check: str) -> Path:
        d = self.dir / check
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_run(self, check: str, label: str, action_text: str, result, seconds: float, extra: dict | None = None) -> str:
        """Save one harness run in full: the exact action, full stdout/stderr, score, reward, timing."""
        d = self.check_dir(check) / "runs" / slug(label)
        i = 2
        while d.exists():  # a repeat of the same label gets -2, -3 ...
            d = d.with_name(f"{slug(label)}-{i}")
            i += 1
        d.mkdir(parents=True)
        (d / "action.sh").write_text(action_text or "# (empty action: the agent does nothing)\n")
        (d / "stdout.txt").write_text(result.stdout or "")
        (d / "stderr.txt").write_text(result.stderr or "")
        meta = {"label": label, "score": result.score, "reward": result.reward, "action_ok": result.action_ok,
                "returncode": result.returncode, "timed_out": result.timed_out, "error": result.error,
                "seconds": round(seconds, 2), "failing_tests": failing_tests(result.stdout),
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), **(extra or {})}
        (d / "run.json").write_text(json.dumps(meta, indent=2))
        return d.relative_to(self.dir.parent).as_posix()

    def save_llm(self, check: str, record: dict) -> None:
        (self.check_dir(check) / "llm-call.json").write_text(json.dumps(record, indent=2, default=str))

    def write_result(self, r: CheckResult) -> None:
        d = self.check_dir(r.name)
        runs = sorted(p.name for p in (d / "runs").iterdir()) if (d / "runs").is_dir() else []
        data = {**r.to_dict(), "runs": [f"runs/{x}" for x in runs]}
        (d / "result.json").write_text(json.dumps(data, indent=2))
        lines = [f"STATUS: {r.status}", f"REASON: {r.reason}"]
        if r.fix:
            lines.append(f"FIX: {r.fix}")
        lines.append(f"TIME: {r.seconds:.2f}s")
        if r.details:
            lines += ["", "DETAILS:"] + [f"  {x}" for x in r.details]
        if runs:
            lines += ["", "RUNS (each: action.sh, stdout.txt, stderr.txt, run.json):"] + [f"  runs/{x}" for x in runs]
        if (d / "llm-call.json").exists():
            lines += ["", "LLM CALL: llm-call.json (full prompt + raw response)"]
        (d / "result.txt").write_text("\n".join(lines) + "\n")


_FAILED = re.compile(r"^(?:FAILED|ERROR) (\S+)", re.MULTILINE)


def failing_tests(stdout: str) -> list[str]:
    """pytest -q prints 'FAILED path::test - reason' lines in its short summary. The path includes the
    harness's random temp dir, so keep only 'file.py::test' (otherwise identical runs look different)."""
    out = []
    for tid in _FAILED.findall(stdout or ""):
        path, sep, rest = tid.partition("::")
        out.append(path.rsplit("/", 1)[-1] + sep + rest)
    return sorted(set(out))
