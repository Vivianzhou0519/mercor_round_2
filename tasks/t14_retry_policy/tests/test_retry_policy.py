from retry_policy import next_delay


def test_first_retry_waits_the_base_interval():
    assert next_delay(1, 503) == 500


def test_wait_doubles_each_retry():
    assert [next_delay(n, 503) for n in (1, 2, 3, 4)] == [500, 1000, 2000, 4000]


def test_wait_is_clamped_to_the_cap():
    assert next_delay(4, 500, cap=3000) == 3000
    assert next_delay(2, 500, cap=3000) == 1000


def test_stops_after_max_attempts():
    assert next_delay(5, 503) is None
    assert next_delay(3, 503, max_attempts=2) is None


def test_only_transient_statuses_are_retried():
    assert next_delay(1, 429) == 500
    assert next_delay(1, 400) is None
    assert next_delay(1, 404) is None
    assert next_delay(1, 200) is None


def test_not_implemented_is_permanent():
    assert next_delay(1, 501) is None
    assert next_delay(1, 502) == 500


def test_retry_after_overrides_the_computed_wait():
    assert next_delay(3, 503, retry_after="12") == 12000
    assert next_delay(2, 429, retry_after="0") == 0


def test_unusable_retry_after_is_ignored():
    assert next_delay(3, 503, retry_after="Wed, 21 Oct 2026 07:28:00 GMT") == 2000
    assert next_delay(3, 503, retry_after="-5") == 2000


def test_retry_after_does_not_revive_a_dead_request():
    assert next_delay(1, 404, retry_after="5") is None
    assert next_delay(9, 503, retry_after="5") is None
