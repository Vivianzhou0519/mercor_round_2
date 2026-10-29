import time

import pytest

from matrix import render, reset_stats

DAY = 86400
MAR01 = 1772323200  # 2026-03-01T00:00:00Z
GENERATED_AT = 1772615100  # 2026-03-04T09:05:00Z
STAMP = "generated 2026-03-04 09:05 UTC"

EVENTS = [
    ("api", MAR01 + 3600),
    ("api", MAR01 + 7200),
    ("web", MAR01 + DAY + 60),
    ("worker", MAR01 + 2 * DAY + 10),
    ("api", MAR01 + 2 * DAY + 20),
]

# Rendering the same scenario twice in one test is wasteful, so the report bodies are
# memoised. The cache is per-test: `fresh_state` empties it before and after each one.
RENDERED = {}


@pytest.fixture(autouse=True)
def fresh_state(monkeypatch):
    monkeypatch.delenv("MATRIX_BLANK_ZEROS", raising=False)
    RENDERED.clear()
    reset_stats()
    yield
    RENDERED.clear()
    reset_stats()
    time.tzset()


def report(key, events, days=3, start=MAR01, generated_at=GENERATED_AT):
    if key not in RENDERED:
        RENDERED[key] = render(events, start, days, generated_at)
    return RENDERED[key]


def test_full_layout():
    assert report("basic", EVENTS) == "\n".join(
        [
            STAMP,
            "       03-01 03-02 03-03",
            "api        2     0     1",
            "web        0     1     0",
            "worker     0     0     1",
            "TOTAL      2     1     2",
        ]
    )


def test_stamp_is_formatted_as_utc():
    assert report("basic", EVENTS).splitlines()[0] == STAMP


def test_columns_are_utc_days():
    just_before = [("api", MAR01 + DAY - 1)]
    just_after = [("api", MAR01 + DAY)]
    assert report("before", just_before, days=2).splitlines()[-1] == "TOTAL     1     0"
    assert report("after", just_after, days=2).splitlines()[-1] == "TOTAL     0     1"


def test_events_outside_the_window_are_ignored():
    events = EVENTS + [("api", MAR01 - 5), ("web", MAR01 + 3 * DAY)]
    assert report("clipped", events) == report("basic", EVENTS)


def test_empty_report_still_has_a_total_row():
    assert report("empty", [], days=2) == "\n".join(
        [
            STAMP,
            "      03-01 03-02",
            "TOTAL     0     0",
        ]
    )


def test_label_field_widens_for_a_long_category():
    events = [("ingestion-pipeline", MAR01 + 100)]
    lines = report("wide", events, days=1).splitlines()
    assert lines[1] == "                   03-01"
    assert lines[2] == "ingestion-pipeline     1"
    assert lines[3] == "TOTAL                  1"


def test_grid_lines_all_have_the_same_length():
    lines = report("basic", EVENTS).splitlines()[1:]
    assert len({len(line) for line in lines}) == 1


def test_rows_are_sorted_by_category():
    events = [("zulu", MAR01), ("alpha", MAR01), ("mike", MAR01)]
    labels = [line.split()[0] for line in report("sorted", events, days=1).splitlines()[2:]]
    assert labels == ["alpha", "mike", "zulu", "TOTAL"]


def test_blank_zero_mode(monkeypatch):
    monkeypatch.setenv("MATRIX_BLANK_ZEROS", "1")
    assert report("blank", EVENTS) == "\n".join(
        [
            STAMP,
            "       03-01 03-02 03-03",
            "api        2     .     1",
            "web        .     1     .",
            "worker     .     .     1",
            "TOTAL      2     1     2",
        ]
    )


def test_blank_zero_mode_is_read_per_call(monkeypatch):
    plain = report("plain", EVENTS).splitlines()[3]
    monkeypatch.setenv("MATRIX_BLANK_ZEROS", "1")
    blanked = report("blanked", EVENTS).splitlines()[3]
    assert plain == "web        0     1     0"
    assert blanked == "web        .     1     ."


def test_other_values_of_the_variable_do_not_blank(monkeypatch):
    monkeypatch.setenv("MATRIX_BLANK_ZEROS", "true")
    assert report("truthy", EVENTS).splitlines()[3] == "web        0     1     0"


def test_bucketing_is_utc_whatever_the_host_clock_says(monkeypatch):
    """The report must not move when the machine sits on the other side of the date line."""
    baseline = render(EVENTS, MAR01, 3, GENERATED_AT)
    for zone in ("Pacific/Kiritimati", "Pacific/Niue"):
        monkeypatch.setenv("TZ", zone)
        time.tzset()
        assert render(EVENTS, MAR01, 3, GENERATED_AT) == baseline


def test_a_category_with_only_out_of_window_events_has_no_row():
    events = EVENTS + [("zeta", MAR01 - DAY), ("zeta", MAR01 + 5 * DAY)]
    assert report("zeta_outside", events) == report("basic", EVENTS)


def test_blank_zero_mode_also_blanks_the_total_row(monkeypatch):
    monkeypatch.setenv("MATRIX_BLANK_ZEROS", "1")
    total = [
        line
        for line in render(EVENTS, MAR01, 4, GENERATED_AT).splitlines()
        if line.startswith("TOTAL")
    ][0]
    assert total.split()[1:] == ["2", "1", "2", "."]


def test_stamp_is_truncated_to_the_minute_not_rounded():
    assert render([], MAR01, 1, GENERATED_AT + 59).splitlines()[0] == STAMP
