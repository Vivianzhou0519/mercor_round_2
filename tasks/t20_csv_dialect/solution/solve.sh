#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/csvdialect.py" << '__HARBOR_EOF__'
"""Read delimiter-separated exports, quoted fields included."""

CANDIDATES = (",", ";", "\t", "|")


def _read_quoted(text, i):
    """Read a quoted field starting at the opening quote; return (value, index)."""
    i += 1
    chunks = []
    while True:
        if i >= len(text):
            raise ValueError("quoted field is never closed")
        char = text[i]
        if char != '"':
            chunks.append(char)
            i += 1
        elif text[i + 1 : i + 2] == '"':
            chunks.append('"')
            i += 2
        else:
            return "".join(chunks), i + 1


def parse_rows(text, delimiter=","):
    """Cut `text` into records, then each record into fields."""
    if len(delimiter) != 1 or delimiter in '"\n':
        raise ValueError("bad delimiter: %r" % (delimiter,))
    rows, row, started = [], [], False
    i, end = 0, len(text)
    while i < end:
        started = True
        if text[i] == '"':
            value, i = _read_quoted(text, i)
            if i < end and text[i] != delimiter and text[i] != "\n":
                raise ValueError("stray text after a closing quote")
        else:
            stop = i
            while stop < end and text[stop] != delimiter and text[stop] != "\n":
                stop += 1
            value, i = text[i:stop], stop
        row.append(value)
        if i >= end:
            break
        if text[i] == delimiter:
            i += 1
            if i >= end:
                row.append("")
            continue
        i += 1
        rows.append(row)
        row, started = [], False
    if started:
        rows.append(row)
    return rows


def sniff(sample):
    """Return the candidate delimiter that best accounts for `sample`."""
    best = None
    for candidate in CANDIDATES:
        try:
            rows = parse_rows(sample, delimiter=candidate)
        except ValueError:
            continue
        widths = {len(row) for row in rows}
        if len(widths) != 1:
            continue
        width = widths.pop()
        if width < 2:
            continue
        if best is None or width > best[0]:
            best = (width, candidate)
    if best is None:
        raise ValueError("no candidate delimiter fits the sample")
    return best[1]
__HARBOR_EOF__
