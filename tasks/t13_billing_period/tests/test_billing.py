from billing import day_key, day_range, period_key

MID_DECEMBER = 1765800000  # 2025-12-15T12:00:00Z
NEW_YEAR = 1767268800  # 2026-01-01T12:00:00Z
LATE_JANUARY = 1769861400  # 2026-01-31T12:10:00Z
EARLY_FEBRUARY = 1770206400  # 2026-02-04T12:00:00Z


def test_day_key_is_a_dashed_calendar_day():
    assert day_key(NEW_YEAR) == "2026-01-01"
    assert day_key(EARLY_FEBRUARY) == "2026-02-04"


def test_period_key_is_year_and_month():
    assert period_key(NEW_YEAR) == "2026-01"
    assert period_key(EARLY_FEBRUARY) == "2026-02"


def test_period_key_does_not_roll_the_year_early():
    assert day_key(MID_DECEMBER) == "2025-12-15"
    assert period_key(MID_DECEMBER) == "2025-12"


def test_period_key_is_the_prefix_of_the_day_key():
    for ts in (MID_DECEMBER, NEW_YEAR, LATE_JANUARY, EARLY_FEBRUARY):
        assert period_key(ts) == day_key(ts)[:7]


def test_day_range_covers_both_ends_and_the_month_boundary():
    assert day_range(LATE_JANUARY, EARLY_FEBRUARY) == [
        "2026-01-31",
        "2026-02-01",
        "2026-02-02",
        "2026-02-03",
        "2026-02-04",
    ]


def test_day_range_of_one_day():
    assert day_range(NEW_YEAR, NEW_YEAR) == ["2026-01-01"]


def test_day_range_backwards_is_empty():
    assert day_range(EARLY_FEBRUARY, LATE_JANUARY) == []


def test_long_day_range_is_ascending_and_unique():
    keys = day_range(NEW_YEAR, NEW_YEAR + 60 * 86400)
    assert len(keys) == 61
    assert len(set(keys)) == len(keys)
    assert keys == sorted(keys)
