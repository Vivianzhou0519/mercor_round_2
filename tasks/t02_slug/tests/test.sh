#!/bin/bash
# Harbor verifier. Runs the test suite and writes a binary reward to
# $LOGS_DIR/reward.txt, per the Harbor reward contract.
set -uo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

mkdir -p "$LOGS_DIR"
cd "$APP_DIR"

PYTHONPATH="$APP_DIR" "$PYTHON_BIN" -m pytest "$TESTS_DIR" -q -p no:cacheprovider
status=$?

if [ "$status" -eq 0 ]; then
  echo 1 > "$LOGS_DIR/reward.txt"
else
  echo 0 > "$LOGS_DIR/reward.txt"
fi

exit "$status"
