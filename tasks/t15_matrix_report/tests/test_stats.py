import random

import pytest

import matrix
from matrix import STATS, render, reset_stats

DAY = 86400
MAR01 = 1772323200  # 2026-03-01T00:00:00Z
GENERATED_AT = 1772615100  # 2026-03-04T09:05:00Z

CATEGORIES = ["api", "scheduler", "web", "worker"]
RNG = random.Random(20260817)

TWO_CELLS = [("api", MAR01 + 60), ("api", MAR01 + 120), ("web", MAR01 + DAY + 60)]


@pytest.fixture(autouse=True)
def zeroed_counters(monkeypatch):
    monkeypatch.delenv("MATRIX_BLANK_ZEROS", raising=False)
    reset_stats()
    yield
    reset_stats()


def test_counters_start_at_zero():
    assert STATS == {"reports": 0, "cells": 0}


def test_one_render_counts_one_report():
    render(TWO_CELLS, MAR01, 2, GENERATED_AT)
    assert STATS["reports"] == 1


def test_counters_accumulate_across_calls():
    render(TWO_CELLS, MAR01, 2, GENERATED_AT)
    render(TWO_CELLS, MAR01, 2, GENERATED_AT)
    assert STATS["reports"] == 2
    assert STATS["cells"] == 4


def test_only_non_zero_category_cells_are_counted():
    render(TWO_CELLS, MAR01, 2, GENERATED_AT)
    # Four cells are laid out (two categories x two days) and the TOTAL row adds two
    # more, but only "api" on 03-01 and "web" on 03-02 are non-zero.
    assert STATS["cells"] == 2


def test_an_empty_report_counts_no_cells():
    render([], MAR01, 3, GENERATED_AT)
    assert STATS == {"reports": 1, "cells": 0}


def test_reset_stats_clears_in_place():
    render(TWO_CELLS, MAR01, 2, GENERATED_AT)
    reset_stats()
    assert STATS["reports"] == 0
    assert STATS["cells"] == 0
    assert STATS is matrix.STATS


def test_fuzz_total_row_matches_the_events():
    for _ in range(60):
        days = RNG.randint(1, 4)
        events = []
        inside = 0
        for _ in range(RNG.randint(0, 25)):
            offset = RNG.randint(-2, days + 1) * DAY + RNG.randrange(DAY)
            events.append((RNG.choice(CATEGORIES), MAR01 + offset))
            if 0 <= offset < days * DAY:
                inside += 1
        lines = render(events, MAR01, days, GENERATED_AT).splitlines()
        assert len({len(line) for line in lines[1:]}) == 1
        totals = [int(value) for value in lines[-1].split()[1:]]
        assert len(totals) == days
        assert sum(totals) == inside
