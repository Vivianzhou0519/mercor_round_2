# Render a daily count matrix

`matrix.py` builds the fixed-width text report our on-call rota pastes into the daily
handover note. It counts events per category per day and lays them out as a grid:

```python
def render(events, start, days, generated_at) -> str
```

- `events` is a list of `(category, at)` pairs. `category` is a non-empty string with
  no spaces in it; `at` is an integer number of seconds since the Unix epoch.
- `start` is an epoch-seconds instant somewhere inside the first day of the window.
- `days` is the number of day columns, always at least 1.
- `generated_at` is the epoch-seconds instant the report was produced.

The current version buckets events by whatever the host machine thinks the local date
is, so the same input reports differently in Dublin and in Denver, and it stops short
of a totals row. Fix it so that all of the following hold.

1. **Days are UTC days.** The first column is the UTC calendar date of `start`; the
   remaining columns are the next `days - 1` UTC dates. An event belongs to the column
   whose UTC date matches the UTC date of its `at`. Events outside the window are
   ignored.
2. **Line 1 is the stamp**, `generated <YYYY-MM-DD HH:MM> UTC`, with `generated_at`
   formatted as UTC and truncated to the minute.
3. **Line 2 is the column header.** It is a label field of spaces, then one field per
   column holding that column's date as `MM-DD`.
4. **One row per category**, sorted ascending by category name, then a final `TOTAL`
   row holding the column sums.
5. **Field layout.** The label field is left-aligned and as wide as the longest label,
   counting `TOTAL` itself, so the label field is never narrower than 5. Each of the
   `days` cell fields that follow is a single space plus the value right-aligned in 5
   characters. Every line from line 2 down is therefore the same length.
6. **A category with no events in the window has no row.** With no events at all, the
   report is still the stamp, the header and a `TOTAL` row of zeros.
7. **Blank-zero mode.** When the environment variable `MATRIX_BLANK_ZEROS` is set to
   `"1"`, a zero cell renders as `.` instead of `0`, in the category rows and in the
   `TOTAL` row alike. Read the variable inside `render`, not at import time, so a
   caller can flip it between calls.

## Counters

The module keeps two counters for the operators' own dashboards:

```python
STATS = {"reports": 0, "cells": 0}

def reset_stats() -> None
```

Each `render` call adds 1 to `STATS["reports"]` and adds the number of **non-zero**
category cells it emitted to `STATS["cells"]`; the `TOTAL` row does not contribute to
`STATS["cells"]`. `reset_stats()` sets both counters back to zero **in place** --
callers hold a reference to `STATS` from import time, so it must not be rebound.

Do not change the name or signature of `render`.
