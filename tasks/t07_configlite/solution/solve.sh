#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/configlite.py" << '__HARBOR_EOF__'
def _coerce(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    digits = value[1:] if value.startswith("-") else value
    if digits.isdigit():
        return int(value)
    return value


def parse(text):
    """Parse the tiny config format into a nested dict."""
    result = {}
    target = result
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            target = result.setdefault(line[1:-1].strip(), {})
            continue
        if ":" not in line:
            raise ValueError("cannot parse line: %r" % raw)
        key, _, value = line.partition(":")
        target[key.strip()] = _coerce(value)
    return result
__HARBOR_EOF__
