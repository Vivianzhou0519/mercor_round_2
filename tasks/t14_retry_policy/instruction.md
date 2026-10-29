# Decide when a failed HTTP request is retried

`retry_policy.py` holds the single decision our HTTP client makes after a response
comes back looking bad:

```python
def next_delay(attempt, status, retry_after=None, base=0.5, cap=8.0, max_attempts=4)
```

`attempt` is the number of the retry being considered, counting from 1: `attempt == 1`
is the first re-send, `attempt == 2` the one after that. `status` is the HTTP status
code we just received. `retry_after` is the raw `Retry-After` response header if the
server sent one, as a string, otherwise `None`.

The function returns how long to wait before that retry, or `None` to mean "stop, this
request is dead". The current implementation retries anything that is not a 2xx or 3xx,
doubles the wait forever, and ignores the header entirely. Fix it so all of the
following hold:

1. **Only transient failures are retried.** `429` and the 5xx range are retryable, with
   one exception: `501` means the server will never implement the call, so it is not.
   Every other status -- the rest of the 4xx range, and anything that succeeded --
   returns `None`.
2. **Give up after `max_attempts`.** Once `attempt` is greater than `max_attempts`
   (4 by default), return `None` whatever the status was.
3. **The first retry goes out immediately.** A single dropped response is usually a
   blip, so `attempt == 1` waits `0` -- there is nothing to be gained by pausing before
   we have even re-sent the request once.
4. **From the second retry on, the wait doubles.** `attempt == 2` waits `base`,
   `attempt == 3` waits twice that, and so on: `base * 2 ** (attempt - 2)`. With the
   default `base` the schedule in seconds is `0`, `0.5`, `1.0`, `2.0`.
5. **Nothing waits longer than `cap`.** A computed delay above `cap` (8.0 by default)
   is clamped down to `cap`.
6. **A usable `Retry-After` wins.** We only support the delta-seconds form of the
   header: a whole number of seconds. If `retry_after` parses as a non-negative
   integer, return that many seconds as the delay instead of the computed one, and do
   not clamp it to `cap` -- the server is telling us when it will be back. If it is
   absent, negative, or not a plain integer (an HTTP-date, say), ignore it and fall
   back to the computed delay. The header never revives a request that rule 1 or rule 2
   has already killed.

All delays are returned in seconds, as floats. Keep the name, the parameter names and
the defaults exactly as they are above; private helpers are fine.
