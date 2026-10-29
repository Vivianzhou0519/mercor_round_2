#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/atomicwrite.py" << '__HARBOR_EOF__'
"""Persist the daemon's settings file.

The target file is never opened for writing. A sibling temporary file is written in
full and then moved onto the target with `os.replace`, which is atomic within a single
filesystem -- so a crash at any point leaves either the old file or the new one, never
a truncated mixture of the two.
"""

import os
from pathlib import Path

TEMP_SUFFIX = ".part"
BACKUP_SUFFIX = ".bak"


def render(settings):
    """Serialise `settings` into the on-disk `key=value` form.

    Every item is validated before any output is produced, so a rejected mapping
    yields a `ValueError` and no text.
    """
    lines = []
    for key in sorted(settings):
        value = settings[key]
        if not key or "=" in key or "\n" in key:
            raise ValueError("unusable settings key: %r" % (key,))
        if "\n" in value:
            raise ValueError("unusable value for key %r: %r" % (key, value))
        lines.append("%s=%s\n" % (key, value))
    return "".join(lines)


def _backups_enabled():
    """Read the backup policy now, not at import time."""
    return os.environ.get("ATOMIC_BACKUP", "1") != "0"


def save(path, settings):
    """Write `settings` to `path` atomically and return the target path."""
    target = Path(path)
    text = render(settings)  # validate everything before touching the filesystem

    temp = target.with_name(target.name + TEMP_SUFFIX)
    backup = target.with_name(target.name + BACKUP_SUFFIX)

    temp.write_text(text, encoding="utf-8")
    try:
        if _backups_enabled() and target.exists():
            backup.write_bytes(target.read_bytes())
        os.replace(temp, target)
    except OSError:
        temp.unlink(missing_ok=True)
        raise
    return target
__HARBOR_EOF__
