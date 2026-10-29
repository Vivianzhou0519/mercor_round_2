from backoff import delays


def test_defaults():
    assert delays(3) == [1.0, 2.0, 4.0]


def test_cap_is_applied():
    assert delays(8, cap=10.0) == [1.0, 2.0, 4.0, 8.0, 10.0, 10.0, 10.0, 10.0]


def test_zero_attempts():
    assert delays(0) == []


def test_zero_base_disables_backoff():
    assert delays(3, base=0.0) == []
