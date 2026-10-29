# Cap exponential backoff delays

`backoff.py` computes the sleep intervals for a retrying client:

```python
def delays(attempts: int, base: float = 1.0, cap: float = 30.0) -> list[float]
```

It returns `base * 2 ** i` for `i` in `0 .. attempts - 1`. In production this grows
without bound and we have seen individual sleeps of several minutes.

Fix `delays()` so that no returned delay is larger than `cap`. `attempts` may be `0`,
in which case the result is the empty list.
