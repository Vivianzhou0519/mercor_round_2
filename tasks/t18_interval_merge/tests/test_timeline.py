"""Property sweeps for the maintenance-window merge.

Three test functions, each a seeded sweep over hundreds of generated schedules. The
seeds are fixed literals and every sweep builds its own `random.Random`, so the suite
is byte-identical from run to run and does not care what order it is collected in.

The reference model is deliberately not a second merge implementation: coverage is
compared as a plain set of covered integers, which is independent of how the windows
were grouped. Sorted + strictly separated + non-empty + equal coverage pins the answer
down to exactly one list, because a set of integers decomposes into maximal runs of
consecutive values in exactly one way.
"""

import random

import pytest

from timeline import merge

CANONICAL_SEED = 20260818
IDEMPOTENCE_SEED = 20260819
VALIDATION_SEED = 20260820
SPAN = 30
LENGTHS = (0, 0, 1, 1, 1, 2, 3, 5, 9)


def _windows(rng, count):
    """A schedule of `count` windows, mixing tuple and list elements."""
    out = []
    for _ in range(count):
        start = rng.randrange(-SPAN, SPAN)
        end = start + rng.choice(LENGTHS)
        out.append((start, end) if rng.random() < 0.5 else [start, end])
    return out


def _covered(windows):
    """The set of integers covered by `windows`, computed without merging anything."""
    points = set()
    for start, end in windows:
        points.update(range(start, end))
    return points


def _snapshot(windows):
    """Capture value, element type and element identity.

    Comparing only values would let a solution rewrite the caller's elements in place
    with equal-but-retyped copies and still look untouched.
    """
    return [(type(window), id(window), tuple(window)) for window in windows]


def test_merge_returns_the_canonical_cover():
    rng = random.Random(CANONICAL_SEED)
    for _ in range(400):
        raw = _windows(rng, rng.randrange(0, 13))
        before = _snapshot(raw)

        result = merge(raw)

        assert isinstance(result, list)
        for window in result:
            assert type(window) is tuple, "output windows must be tuples"
            assert len(window) == 2
            assert all(type(value) is int for value in window)
            assert window[0] < window[1], "empty windows must be dropped"
        for left, right in zip(result, result[1:]):
            assert left[1] < right[0], "output windows must not overlap or touch"
        assert result == sorted(result), "output must be sorted by start"
        assert _covered(result) == _covered(raw), "coverage must be preserved exactly"
        assert _snapshot(raw) == before, "the argument must not be modified"
        assert len(raw) == len(before)


def test_merge_is_idempotent_and_independent_of_input_order():
    rng = random.Random(IDEMPOTENCE_SEED)
    for _ in range(300):
        raw = _windows(rng, rng.randrange(0, 13))

        once = merge(raw)
        assert merge(once) == once, "merge must be idempotent"

        shuffled = list(raw)
        rng.shuffle(shuffled)
        assert merge(shuffled) == once, "the result must not depend on arrival order"

        as_lists = [[start, end] for start, end in raw]
        assert merge(as_lists) == once, "list elements must behave like tuple elements"

        reversed_input = list(reversed(raw))
        assert merge(reversed_input) == once


def test_merge_rejects_malformed_windows_and_handles_degenerate_input():
    assert merge([]) == []
    assert merge([(4, 4), (9, 9), [-2, -2]]) == []

    rng = random.Random(VALIDATION_SEED)
    for _ in range(250):
        good = _windows(rng, rng.randrange(1, 9))
        assert merge(good) is not None

        start = rng.randrange(-SPAN, SPAN)
        bad = rng.choice(
            [
                (start, start - rng.randrange(1, 6)),
                [start, start - rng.randrange(1, 6)],
                (start,),
                (start, start + 1, start + 2),
                [],
            ]
        )
        polluted = list(good)
        polluted.insert(rng.randrange(0, len(polluted) + 1), bad)
        with pytest.raises(ValueError):
            merge(polluted)
