from wordwrap import wrap


def test_greedy_packing():
    assert wrap("the quick brown fox jumps", 10) == ["the quick", "brown fox", "jumps"]


def test_no_line_exceeds_width():
    text = "alpha beta gamma delta epsilon zeta eta theta"
    for line in wrap(text, 12):
        assert len(line) <= 12


def test_long_word_gets_its_own_line():
    assert wrap("a supercalifragilistic b", 5) == ["a", "supercalifragilistic", "b"]


def test_whitespace_is_collapsed():
    assert wrap("  the\tquick\n\nbrown  ", 20) == ["the quick brown"]


def test_empty_input():
    assert wrap("", 10) == []
    assert wrap("   \n\t ", 10) == []


def test_width_of_one():
    assert wrap("ab c d", 1) == ["ab", "c", "d"]


def test_exact_fit():
    assert wrap("abc def", 7) == ["abc def"]
