#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/matrix.py" << '__HARBOR_EOF__'
import os
from datetime import datetime, timedelta, timezone

CELL = 5

#: Counters for the rendering pass. Rebound nowhere; `reset_stats` clears in place so
#: a caller that did `from matrix import STATS` keeps seeing the live object.
STATS = {"reports": 0, "cells": 0}


def reset_stats():
    """Zero both counters in place."""
    STATS["reports"] = 0
    STATS["cells"] = 0


def _utc_date(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).date()


def render(events, start, days, generated_at):
    """Render a per-category, per-UTC-day count matrix as fixed-width text."""
    columns = [_utc_date(start) + timedelta(days=i) for i in range(days)]
    position = {day: i for i, day in enumerate(columns)}
    grid = {}
    for category, at in events:
        index = position.get(_utc_date(at))
        if index is not None:
            grid.setdefault(category, [0] * days)[index] += 1

    blank = os.environ.get("MATRIX_BLANK_ZEROS") == "1"
    names = sorted(grid)
    width = max([len("TOTAL")] + [len(name) for name in names])

    def line(label, cells):
        body = "".join(" %*s" % (CELL, cell) for cell in cells)
        return "%-*s%s" % (width, label, body)

    def counts(row):
        return ["." if blank and value == 0 else value for value in row]

    stamp = datetime.fromtimestamp(generated_at, tz=timezone.utc)
    out = ["generated %s UTC" % stamp.strftime("%Y-%m-%d %H:%M")]
    out.append(line("", [day.strftime("%m-%d") for day in columns]))
    for name in names:
        out.append(line(name, counts(grid[name])))
    totals = [sum(grid[name][i] for name in names) for i in range(days)]
    out.append(line("TOTAL", counts(totals)))

    STATS["reports"] += 1
    STATS["cells"] += sum(1 for name in names for value in grid[name] if value)
    return "\n".join(out)
__HARBOR_EOF__
