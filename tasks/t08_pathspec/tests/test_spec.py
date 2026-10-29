import os
import random

import pytest

from pathspec import matches
from spec import compile_spec

RNG = random.Random(20260214)

NAMES = ["main", "utils", "test", "a1", "keep"]
DIRS = ["src", "lib", "src/app", "build/x"]


def test_unsupported_pattern_is_dropped_by_default():
    spec = compile_spec(["a**b", "*.py"])
    assert spec("main.py") is True
    assert spec("aXb") is False


def test_strict_mode_raises(monkeypatch):
    monkeypatch.setenv("PATHSPEC_STRICT", "1")
    with pytest.raises(ValueError):
        compile_spec(["a**b"])


def test_strict_mode_is_read_per_call(monkeypatch):
    monkeypatch.delenv("PATHSPEC_STRICT", raising=False)
    assert compile_spec(["a**b"])("aXb") is False


def test_supported_patterns_survive_strict_mode(monkeypatch):
    monkeypatch.setenv("PATHSPEC_STRICT", "1")
    spec = compile_spec(["**/main.py", "build/**", "!build/x/keep.o"])
    assert spec("a/b/main.py") is True
    assert spec("build/x/z.o") is True
    assert spec("build/x/keep.o") is False


@pytest.mark.skipif(
    os.environ.get("PATHSPEC_SKIP_SLOW") == "1",
    reason="set PATHSPEC_SKIP_SLOW=1 to skip the fuzz check",
)
def test_fuzz_basename_patterns_agree():
    for _ in range(200):
        path = "%s/%s.py" % (RNG.choice(DIRS), RNG.choice(NAMES))
        basename = path.rsplit("/", 1)[-1]
        assert matches(path, ["*.py"]) == matches(basename, ["*.py"])
