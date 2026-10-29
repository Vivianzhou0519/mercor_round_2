#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/columns.py" << '__HARBOR_EOF__'
def fill(text, width):
    """Reflow `text` into lines of at most `width` characters.

    A token longer than `width` is never broken up; it is given a line to itself.
    """
    tokens = text.split()
    if not tokens:
        return []

    lines = []
    line = []
    used = 0
    for token in tokens:
        if not line:
            line = [token]
            used = len(token)
        elif used + 1 + len(token) <= width:
            line.append(token)
            used += 1 + len(token)
        else:
            lines.append(" ".join(line))
            line = [token]
            used = len(token)
    lines.append(" ".join(line))
    return lines
__HARBOR_EOF__
