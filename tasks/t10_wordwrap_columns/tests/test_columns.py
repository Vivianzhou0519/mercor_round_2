from columns import fill


def test_packs_tokens_greedily():
    assert fill("roses are red and violets are blue", 14) == [
        "roses are red",
        "and violets",
        "are blue",
    ]


def test_lines_stay_within_width():
    text = "one two three four five six seven eight nine ten"
    for line in fill(text, 9):
        assert len(line) <= 9


def test_oversized_token_is_left_intact():
    assert fill("go incomprehensibilities on", 6) == [
        "go",
        "incomprehensibilities",
        "on",
    ]


def test_runs_of_whitespace_become_one_space():
    assert fill("\n\n red\t\tgreen  blue \n", 16) == ["red green blue"]


def test_text_without_tokens_yields_nothing():
    assert fill("", 8) == []
    assert fill(" \t\n  ", 8) == []


def test_single_column_width():
    assert fill("hi q z", 1) == ["hi", "q", "z"]


def test_line_that_exactly_fills_width():
    assert fill("four five", 9) == ["four five"]
