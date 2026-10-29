#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/billing.py" << '__HARBOR_EOF__'
from datetime import datetime, timedelta


def _calendar_date(ts):
    """The calendar date the timestamp `ts` falls on."""
    return datetime.fromtimestamp(ts).date()


def day_key(ts):
    """Return the day bucket a usage sample belongs to, as `YYYY-MM-DD`."""
    return _calendar_date(ts).isoformat()


def period_key(ts):
    """Return the billing period a usage sample belongs to, as `YYYY-MM`."""
    return _calendar_date(ts).strftime("%Y-%m")


def day_range(start_ts, end_ts):
    """Every day bucket from `start_ts` to `end_ts`, inclusive and ascending."""
    if end_ts < start_ts:
        return []
    cursor = _calendar_date(start_ts)
    last = _calendar_date(end_ts)
    keys = []
    while cursor <= last:
        keys.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return keys
__HARBOR_EOF__
