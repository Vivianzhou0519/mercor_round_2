#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/timeline.py" << '__HARBOR_EOF__'
"""Collapse reported maintenance windows into the schedule's canonical cover."""


def merge(intervals):
    """Merge the half-open windows in `intervals` into a sorted, disjoint cover.

    Validation runs over the whole list before anything is merged, so a malformed
    window raises regardless of where it sits.
    """
    cleaned = []
    for window in intervals:
        pair = tuple(window)
        if len(pair) != 2:
            raise ValueError("window needs exactly two endpoints: %r" % (window,))
        start, end = pair
        if start > end:
            raise ValueError("window ends before it starts: %r" % (window,))
        if start < end:
            cleaned.append((start, end))

    cleaned.sort()
    merged = []
    for start, end in cleaned:
        if merged and start <= merged[-1][1]:
            open_start, open_end = merged[-1]
            merged[-1] = (open_start, end if end > open_end else open_end)
        else:
            merged.append((start, end))
    return merged
__HARBOR_EOF__
