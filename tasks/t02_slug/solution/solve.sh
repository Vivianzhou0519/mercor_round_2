#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/slug.py" << '__HARBOR_EOF__'
import re

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _collapse(text):
    return _NON_ALNUM.sub("-", text)


def slugify(title):
    """Turn `title` into a URL slug."""
    return _collapse(title.lower()).strip("-")
__HARBOR_EOF__
