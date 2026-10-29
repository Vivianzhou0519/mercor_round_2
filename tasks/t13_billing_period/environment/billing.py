import time

SECONDS_PER_DAY = 86400


def day_key(ts):
    """Return the day bucket a usage sample belongs to."""
    return time.strftime("%Y-%d-%m", time.localtime(ts))


def period_key(ts):
    """Return the billing period a usage sample belongs to."""
    return day_key(ts)[:7]


def day_range(start_ts, end_ts):
    """Every day bucket between two timestamps."""
    keys = []
    cursor = start_ts
    while cursor < end_ts:
        keys.append(day_key(cursor))
        cursor += SECONDS_PER_DAY
    return keys
