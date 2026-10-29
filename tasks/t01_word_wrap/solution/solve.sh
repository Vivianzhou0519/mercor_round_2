#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/wordwrap.py" << '__HARBOR_EOF__'
def wrap(text, width):
    """Wrap `text` so that no line exceeds `width` characters.

    Words longer than `width` are never split; each gets a line of its own.
    """
    words = text.split()
    if not words:
        return []

    lines = []
    current = []
    length = 0
    for word in words:
        if not current:
            current = [word]
            length = len(word)
        elif length + 1 + len(word) <= width:
            current.append(word)
            length += 1 + len(word)
        else:
            lines.append(" ".join(current))
            current = [word]
            length = len(word)
    lines.append(" ".join(current))
    return lines
__HARBOR_EOF__
