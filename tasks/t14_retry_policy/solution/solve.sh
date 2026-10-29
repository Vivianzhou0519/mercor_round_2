#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/retry_policy.py" << '__HARBOR_EOF__'
def next_delay(attempt, status, retry_after=None, base=500, cap=8000, max_attempts=4):
    """Milliseconds to wait before retry number `attempt`, or None to give up.

    `status` is the HTTP status code of the response we are reacting to and
    `retry_after` is the raw `Retry-After` header, if the server sent one.
    """
    if attempt > max_attempts:
        return None
    if not _is_transient(status):
        return None

    override = _parse_retry_after(retry_after)
    if override is not None:
        return override
    return min(base * 2 ** (attempt - 1), cap)


def _is_transient(status):
    """429 and the 5xx range, minus 501, which the server will never implement."""
    if status == 429:
        return True
    return 500 <= status < 600 and status != 501


def _parse_retry_after(value):
    """The delta-seconds form of `Retry-After`, in ms, or None if we cannot use it."""
    if value is None:
        return None
    try:
        seconds = int(value.strip())
    except (AttributeError, ValueError):
        return None
    if seconds < 0:
        return None
    return seconds * 1000
__HARBOR_EOF__
