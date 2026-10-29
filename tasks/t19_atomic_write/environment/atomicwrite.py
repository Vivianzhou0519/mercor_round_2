"""Persist the daemon's settings file."""

import os
from pathlib import Path

TEMP_SUFFIX = ".part"
BACKUP_SUFFIX = ".bak"

BACKUPS_ENABLED = os.environ.get("ATOMIC_BACKUP", "1") != "0"


def render(settings):
    """Serialise `settings` into the on-disk `key=value` form."""
    return "".join("%s=%s\n" % (key, value) for key, value in settings.items())


def save(path, settings):
    """Write `settings` to `path`."""
    target = Path(path)
    if BACKUPS_ENABLED and target.exists():
        target.with_suffix(BACKUP_SUFFIX).write_bytes(target.read_bytes())
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(render(settings))
    return target
