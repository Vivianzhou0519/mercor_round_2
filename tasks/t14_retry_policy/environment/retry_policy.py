def next_delay(attempt, status, retry_after=None, base=0.5, cap=8.0, max_attempts=4):
    """How long to wait before retry number `attempt`, or None to give up.

    `status` is the HTTP status code of the response we are reacting to and
    `retry_after` is the raw `Retry-After` header, if the server sent one.
    """
    if 200 <= status < 400:
        return None
    return base * 2 ** attempt
