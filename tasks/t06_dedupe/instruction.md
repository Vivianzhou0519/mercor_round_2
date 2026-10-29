# Preserve order when de-duplicating

`dedupe.py` removes duplicate values from a list:

```python
def dedupe(items: list) -> list
```

It currently returns the items in an arbitrary order. Fix it so the result keeps the
order in which each value was **first seen**, and each value appears exactly once.
All items are hashable. The input list must not be modified.
