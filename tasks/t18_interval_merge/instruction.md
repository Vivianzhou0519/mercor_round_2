# Normalise a maintenance-window schedule

`timeline.py` collapses the raw maintenance windows a fleet reports into the canonical
cover the scheduler consumes:

```python
def merge(intervals: list) -> list[tuple[int, int]]
```

Each element of `intervals` is a sequence of two integers — a tuple or a list, both
appear in real input — and is read as the half-open window `[start, end)`. The current
implementation was written against a demo feed that was already sorted and disjoint,
and it gets almost everything else wrong. Rewrite `merge` so that all of the following
hold. Keep the name and signature.

1. **Half-open semantics.** A window `(start, end)` covers exactly the integers `x`
   with `start <= x < end`. `(3, 7)` covers 3, 4, 5 and 6 — not 7.
2. **Every element is validated, whatever its position.** An element that does not have
   exactly two endpoints raises `ValueError`, and so does an element whose `start` is
   greater than its `end`. A single bad window anywhere in the list makes
   the whole call raise; validation is not allowed to stop at the first element or to
   quietly skip the offender.
3. **Empty windows are dropped.** `start == end` covers nothing, so it contributes
   nothing and never appears in the output. It is valid input, not an error.
4. **The output is sorted ascending by start.**
5. **Overlapping windows merge into one.** `(0, 5)` and `(3, 9)` become `(0, 9)`.
6. **Touching windows merge too.** Because the windows are half-open, `(0, 3)` and
   `(3, 8)` cover a contiguous run of integers, so they become `(0, 8)`. No two
   windows in the output may touch: for consecutive output windows `a` then `b`,
   `a[1] < b[0]` strictly.
7. **A merged run spans its earliest start to its latest end.** Nesting is common in
   the feed — `(0, 20)` and `(4, 6)` become `(0, 20)`, not `(0, 6)`.
8. **Coverage is preserved exactly.** The set of integers covered by the output is the
   same set covered by the input: `merge` never invents coverage and never loses any.
9. **`merge` is idempotent.** `merge(merge(x)) == merge(x)` for every valid `x`, and
   the result does not depend on the order the windows arrived in.
10. **The return value is a new list of `(int, int)` tuples** — tuples, not lists, even
    when the input used lists.
11. **The argument is never modified.** Neither the list handed in nor any element of
    it may be reordered or rewritten. Sorting in place is the usual way this breaks.
12. **Empty input returns `[]`**, and so does an input made up entirely of empty
    windows.

Coordinates are ordinary Python `int`s and may be negative.
