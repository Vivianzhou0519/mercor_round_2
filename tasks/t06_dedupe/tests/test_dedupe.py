import random

from dedupe import dedupe


def test_first_seen_order():
    assert dedupe(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]


def test_input_is_not_modified():
    items = [3, 1, 3]
    dedupe(items)
    assert items == [3, 1, 3]


def test_empty():
    assert dedupe([]) == []


def test_random_sample_roundtrip():
    values = random.sample(range(100), 4)
    out = dedupe(values * 3)
    assert out == values
    assert out[0] < out[-1]
