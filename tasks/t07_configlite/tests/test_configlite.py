import pytest

from configlite import parse

SAMPLE = """
# a comment
name: research-ops
retries: 3
verbose: true

[database]
host: localhost
port: 5432
password: "  secret  "
readonly: FALSE
offset: -12
"""


def test_top_level_keys():
    result = parse(SAMPLE)
    assert result["name"] == "research-ops"
    assert result["retries"] == 3
    assert result["verbose"] is True


def test_sections_nest():
    result = parse(SAMPLE)
    assert result["database"]["host"] == "localhost"
    assert result["database"]["port"] == 5432


def test_quoted_values_keep_inner_whitespace():
    assert parse(SAMPLE)["database"]["password"] == "  secret  "


def test_booleans_are_case_insensitive():
    assert parse(SAMPLE)["database"]["readonly"] is False


def test_negative_integers():
    assert parse(SAMPLE)["database"]["offset"] == -12


def test_comments_and_blank_lines_are_ignored():
    assert parse("\n\n   # nothing here\n") == {}


def test_duplicate_key_overwrites():
    assert parse("a: 1\na: 2") == {"a": 2}


def test_malformed_line_raises():
    with pytest.raises(ValueError):
        parse("this is not a pair")
