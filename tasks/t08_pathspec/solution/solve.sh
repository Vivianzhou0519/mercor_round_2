#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/pathspec.py" << '__HARBOR_EOF__'
import re


def _expand_braces(pattern):
    """Expand brace groups into one pattern per alternative, left to right."""
    match = re.search(r"\{([^{}]*)\}", pattern)
    if match is None:
        return [pattern]
    head = pattern[: match.start()]
    tail = pattern[match.end() :]
    expanded = []
    for alternative in match.group(1).split(","):
        expanded.extend(_expand_braces(head + alternative + tail))
    return expanded


def _to_regex(pattern):
    parts = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("/**", index):
            parts.append("/.*")
            index += 3
        elif pattern[index] == "*":
            parts.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            parts.append("[^/]")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    return re.compile("^" + "".join(parts) + "$")


def _matches_one(path, pattern):
    if "/" in pattern:
        return _to_regex(pattern).match(path) is not None
    return _to_regex(pattern).match(path.rsplit("/", 1)[-1]) is not None


def matches(path, patterns):
    """Return True if `path` matches `patterns`; the last matching pattern wins."""
    result = False
    for pattern in patterns:
        negated = pattern.startswith("!")
        body = pattern[1:] if negated else pattern
        for expanded in _expand_braces(body):
            if _matches_one(path, expanded):
                result = not negated
                break
    return result
__HARBOR_EOF__

cat > "$APP_DIR/spec.py" << '__HARBOR_EOF__'
import os
import re

from pathspec import _expand_braces, matches

_UNSUPPORTED = re.compile(r"[^/]\*\*|\*\*[^/]")


def compile_spec(patterns):
    """Validate `patterns` and return a matcher closure."""
    strict = os.environ.get("PATHSPEC_STRICT") == "1"
    usable = []
    for pattern in patterns:
        body = pattern[1:] if pattern.startswith("!") else pattern
        if any(_UNSUPPORTED.search(part) for part in _expand_braces(body)):
            if strict:
                raise ValueError("unsupported pattern: %r" % pattern)
            continue
        usable.append(pattern)

    def matcher(path):
        return matches(path, usable)

    return matcher
__HARBOR_EOF__
