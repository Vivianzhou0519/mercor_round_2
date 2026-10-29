#!/bin/bash
# Harbor verifier. Runs the test suite and writes a binary reward to
# $LOGS_DIR/reward.txt, per the Harbor reward contract.
set -uo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

mkdir -p "$LOGS_DIR"

# Stage the suite alongside the module under test so a plain `pytest` picks up
# both without any path juggling.
cp "$TESTS_DIR"/test_*.py "$APP_DIR"/ 2>/dev/null || true
cd "$APP_DIR"

PYTHONPATH="$APP_DIR" "$PYTHON_BIN" -m pytest . -q -p no:cacheprovider
status=$?

if [ "$status" -eq 0 ]; then
  echo 1 > "$LOGS_DIR/reward.txt"
else
  echo 0 > "$LOGS_DIR/reward.txt"
fi

exit "$status"
