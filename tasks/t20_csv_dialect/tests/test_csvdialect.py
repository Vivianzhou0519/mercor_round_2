import pytest

from csvdialect import parse_rows, sniff


def test_plain_records_split_on_the_delimiter():
    assert parse_rows("id,name\n7,ada\n") == [["id", "name"], ["7", "ada"]]


def test_final_newline_does_not_open_a_record():
    assert parse_rows("a,b\n") == [["a", "b"]]
    assert parse_rows("a,b") == [["a", "b"]]


def test_empty_text_has_no_records():
    assert parse_rows("") == []


def test_blank_interior_line_is_one_empty_field():
    assert parse_rows("a\n\nb\n") == [["a"], [""], ["b"]]


def test_trailing_delimiter_adds_an_empty_field():
    assert parse_rows("a,b,") == [["a", "b", ""]]
    assert parse_rows("a,,b\n") == [["a", "", "b"]]


def test_quoted_field_swallows_the_delimiter():
    assert parse_rows('id,"Lovelace, Ada",1815') == [["id", "Lovelace, Ada", "1815"]]


def test_quoted_field_spans_a_newline():
    rows = parse_rows('note,"line one\nline two",end\n')
    assert rows == [["note", "line one\nline two", "end"]]


def test_doubled_quotes_collapse_to_one():
    assert parse_rows('"he said ""hi""",x') == [['he said "hi"', "x"]]


def test_quote_after_the_first_character_is_literal():
    assert parse_rows('ab"c,d') == [['ab"c', "d"]]


def test_surrounding_spaces_are_preserved():
    assert parse_rows('  a  ,"  b  "') == [["  a  ", "  b  "]]


def test_unclosed_quote_raises():
    with pytest.raises(ValueError):
        parse_rows('a,"b,c\n')


def test_stray_text_after_closing_quote_raises():
    with pytest.raises(ValueError):
        parse_rows('a,"b"c,d')


def test_delimiter_must_be_a_single_safe_character():
    with pytest.raises(ValueError):
        parse_rows("a,b", delimiter=",,")
    with pytest.raises(ValueError):
        parse_rows("a,b", delimiter="")
    with pytest.raises(ValueError):
        parse_rows('a"b', delimiter='"')
    with pytest.raises(ValueError):
        parse_rows("a\nb", delimiter="\n")


def test_custom_delimiter_is_honoured():
    assert parse_rows("a|b,c\nd|e,f", delimiter="|") == [["a", "b,c"], ["d", "e,f"]]


def test_sniff_picks_the_column_consistent_delimiter():
    assert sniff("name;role\nada;engineer\ngrace;admiral\n") == ";"


def test_sniff_is_quote_aware():
    assert sniff('x;"a,b";z\np;q;r\n') == ";"


def test_sniff_prefers_the_widest_split():
    assert sniff("a,b|c|d\ne,f|g|h\n") == "|"


def test_sniff_breaks_ties_by_candidate_order():
    assert sniff("a,b;c\nd,e;f\n") == ","


def test_sniff_handles_tabs():
    assert sniff("one\ttwo\tthree\nfour\tfive\tsix\n") == "\t"


def test_sniff_rejects_a_sample_with_no_columns():
    with pytest.raises(ValueError):
        sniff("just one column\nand another line\n")
    with pytest.raises(ValueError):
        sniff("")


def test_sniff_skips_a_candidate_that_cannot_parse():
    # Under `,` the second field opens a quote and then has `c` hanging off the end of
    # it, which is a parse error; under `|` both records hold two fields.
    assert sniff('a,"b"c|d\ne,f|g\n') == "|"


def test_sniff_ignores_a_delimiter_with_ragged_records():
    # `,` splits the first record in two and the second in one, so it is disqualified;
    # `|` gives both records two fields.
    assert sniff("a,b|c\nd|e\n") == "|"
