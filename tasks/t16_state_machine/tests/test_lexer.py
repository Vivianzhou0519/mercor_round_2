import itertools
import string

import pytest

from lexer import LexError, tokenize

# One representative token of every kind, used by the round-trip property check.
POOL = [
    ("NUMBER", "0"),
    ("NUMBER", "12"),
    ("NUMBER", "3.5"),
    ("NAME", "x"),
    ("NAME", "_tmp2"),
    ("NAME", "snake_case"),
    ("OP", "+"),
    ("OP", "-"),
    ("OP", "**"),
    ("OP", "%"),
    ("LPAREN", "("),
    ("RPAREN", ")"),
]


def test_whitespace_is_never_emitted():
    assert tokenize("\t1\r\n +  2\n") == [("NUMBER", "1"), ("OP", "+"), ("NUMBER", "2")]


def test_tokens_need_no_surrounding_whitespace():
    assert tokenize("2*x+(3.5**y)") == [
        ("NUMBER", "2"),
        ("OP", "*"),
        ("NAME", "x"),
        ("OP", "+"),
        ("LPAREN", "("),
        ("NUMBER", "3.5"),
        ("OP", "**"),
        ("NAME", "y"),
        ("RPAREN", ")"),
    ]


def test_numbers_may_have_a_fractional_part():
    assert tokenize("7 3.5 100.250") == [
        ("NUMBER", "7"),
        ("NUMBER", "3.5"),
        ("NUMBER", "100.250"),
    ]


def test_dot_joins_the_number_only_when_a_digit_follows():
    # "1.2" is consumed as one NUMBER, leaving the second dot -- which cannot start a
    # token -- at index 3.
    with pytest.raises(LexError) as info:
        tokenize("1.2.3")
    assert info.value.pos == 3

    # Nothing follows the dot at all, so the NUMBER stops at index 1.
    with pytest.raises(LexError) as info:
        tokenize("3.")
    assert info.value.pos == 1

    # A letter follows the dot, so again the dot is left over.
    with pytest.raises(LexError) as info:
        tokenize("3.x")
    assert info.value.pos == 1


def test_names_start_with_a_letter_or_underscore():
    assert tokenize("x _tmp2 abc123") == [
        ("NAME", "x"),
        ("NAME", "_tmp2"),
    ("NAME", "snake_case"),
        ("NAME", "abc123"),
    ]


def test_names_carry_underscores_and_digits_through_the_body():
    assert tokenize("snake_case_name a_1 z9_") == [
        ("NAME", "snake_case_name"),
        ("NAME", "a_1"),
        ("NAME", "z9_"),
    ]


def test_classification_is_ascii_only():
    for source in ("caf\u00e9", "\u0661\u0662", "1\u0663"):
        with pytest.raises(LexError):
            tokenize(source)


def test_vertical_tab_and_form_feed_are_not_whitespace():
    for source in ("1\v2", "1\f2"):
        with pytest.raises(LexError):
            tokenize(source)


def test_parentheses_get_their_own_kinds():
    assert tokenize("(a)") == [("LPAREN", "("), ("NAME", "a"), ("RPAREN", ")")]


def test_double_star_is_a_single_operator():
    assert tokenize("2**3") == [("NUMBER", "2"), ("OP", "**"), ("NUMBER", "3")]
    assert tokenize("2***3") == [
        ("NUMBER", "2"),
        ("OP", "**"),
        ("OP", "*"),
        ("NUMBER", "3"),
    ]


def test_single_character_operators():
    assert tokenize("+ - * / %") == [
        ("OP", "+"),
        ("OP", "-"),
        ("OP", "*"),
        ("OP", "/"),
        ("OP", "%"),
    ]


def test_unexpected_character_reports_its_position():
    with pytest.raises(LexError) as info:
        tokenize("1 + $x")
    assert info.value.pos == 4
    assert isinstance(info.value, ValueError)


def test_input_with_no_tokens():
    assert tokenize("") == []
    assert tokenize(" \t\r\n ") == []


def test_whitespace_separated_sequences_round_trip():
    for triple in itertools.product(POOL, repeat=3):
        source = " ".join(text for _, text in triple)
        tokens = tokenize(source)
        assert tokens == list(triple)
        assert "".join(text for _, text in tokens) == source.replace(" ", "")


def test_every_printable_ascii_character_is_classified():
    for code in range(33, 127):
        ch = chr(code)
        if ch in string.digits:
            expected = ("NUMBER", ch)
        elif ch in string.ascii_letters or ch == "_":
            expected = ("NAME", ch)
        elif ch == "(":
            expected = ("LPAREN", ch)
        elif ch == ")":
            expected = ("RPAREN", ch)
        elif ch in "+-*/%":
            expected = ("OP", ch)
        else:
            expected = None

        if expected is None:
            with pytest.raises(LexError) as info:
                tokenize(ch)
            assert info.value.pos == 0, ch
        else:
            assert tokenize(ch) == [expected], ch
