from slug import slugify


def test_basic():
    assert slugify("Hello World") == "hello-world"


def test_leading_and_trailing_punctuation():
    assert slugify("  Hello, World!  ") == "hello-world"


def test_runs_collapse_to_one_hyphen():
    assert slugify("a --- b") == "a-b"


def test_already_a_slug():
    assert slugify("already-a-slug") == "already-a-slug"


def test_digits_are_kept():
    assert slugify("Top 10 Tips!") == "top-10-tips"
