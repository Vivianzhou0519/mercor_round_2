import pytest

from money import format_minor, minor_units, to_minor


def test_lookup_normalises_the_code():
    assert minor_units(" jpy ") == 0
    assert minor_units("Kwd") == 3


def test_malformed_code_is_rejected():
    for bad in ("US", "USDD", "US1", "", "   "):
        with pytest.raises(ValueError):
            minor_units(bad)


def test_unlisted_code_falls_back_to_two():
    assert minor_units("ZZZ") == 2


def test_to_minor_scales_by_the_exponent():
    assert to_minor("12.34", "USD") == 1234
    assert to_minor("1234", "ISK") == 1234
    assert to_minor("1.234", "KWD") == 1234
    assert to_minor("0.0001", "CLF") == 1


def test_to_minor_rounds_half_up():
    assert to_minor("12.345", "USD") == 1235
    assert to_minor("12.344", "USD") == 1234
    assert to_minor("0.5", "ISK") == 1
    assert to_minor("0.4999", "ISK") == 0
    assert to_minor("1.23449", "KWD") == 1234


def test_to_minor_rounds_negatives_away_from_zero():
    assert to_minor("-12.345", "USD") == -1235
    assert to_minor("-12.344", "USD") == -1234
    assert to_minor("-0.5", "ISK") == -1


def test_to_minor_rejects_anything_but_a_decimal_string():
    for bad in ("", "1e5", "nan", "1.2.3", " 1", "1,5", "+1", "1."):
        with pytest.raises(ValueError):
            to_minor(bad, "USD")


def test_format_minor_places_the_decimal_point():
    assert format_minor(123456, "USD") == "USD 1,234.56"
    assert format_minor(5, "USD") == "USD 0.05"
    assert format_minor(0, "CLF") == "CLF 0.0000"


def test_format_minor_omits_the_point_when_there_is_no_minor_unit():
    assert format_minor(1234, "JPY") == "JPY 1,234"
    assert format_minor(0, "JPY") == "JPY 0"


def test_format_minor_groups_the_integer_part_only():
    assert format_minor(1234567, "KWD") == "KWD 1,234.567"
    assert format_minor(123456789012, "EUR") == "EUR 1,234,567,890.12"
    assert format_minor(100000, "ISK") == "ISK 100,000"


def test_format_minor_signs_negatives():
    assert format_minor(-123456, "USD") == "USD -1,234.56"
    assert format_minor(-5, "USD") == "USD -0.05"
    assert format_minor(0, "USD") == "USD 0.00"


def test_format_minor_normalises_the_code():
    assert format_minor(100, " usd ") == "USD 1.00"
    assert format_minor(100, "zzz") == "ZZZ 1.00"


def test_format_minor_rejects_non_integer_minor_units():
    for bad in (1.5, "100", None, True, False):
        with pytest.raises(ValueError):
            format_minor(bad, "USD")
