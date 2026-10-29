#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/backoff.py" << '__HARBOR_EOF__'
def delays(attempts, base=1.0, cap=30.0):
    """Return the sequence of backoff delays for `attempts` retries."""
    return [min(base * 2 ** i, cap) for i in range(attempts)]
__HARBOR_EOF__
