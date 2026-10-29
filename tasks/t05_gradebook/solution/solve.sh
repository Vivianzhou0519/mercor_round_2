#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/gradebook.py" << '__HARBOR_EOF__'
def summary(scores):
    """Return summary statistics for a list of exam scores."""
    ordered = sorted(scores)
    count = len(ordered)
    middle = count // 2
    if count % 2:
        median = float(ordered[middle])
    else:
        median = (ordered[middle - 1] + ordered[middle]) / 2
    return {
        "mean": round(sum(ordered) / count, 1),
        "median": round(median, 1),
        "highest": ordered[-1],
        "lowest": ordered[0],
        "passing": sum(1 for score in ordered if score >= 60),
    }
__HARBOR_EOF__
