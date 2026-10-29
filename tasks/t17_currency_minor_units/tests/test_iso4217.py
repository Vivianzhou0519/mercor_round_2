from iso4217 import minor_unit_table


def test_table_covers_the_settlement_list():
    assert len(minor_unit_table()) >= 40


def test_every_entry_is_well_formed():
    for code, exponent in minor_unit_table().items():
        assert isinstance(code, str)
        assert len(code) == 3 and code.isalpha() and code.isupper()
        assert exponent in (0, 2, 3, 4)


def test_published_exponents():
    table = minor_unit_table()
    assert table["USD"] == 2
    assert table["JPY"] == 0
    assert table["KWD"] == 3
    assert table["CLF"] == 4


def test_each_call_returns_a_fresh_mapping():
    first = minor_unit_table()
    first["USD"] = 99
    first["QQQ"] = 7
    second = minor_unit_table()
    assert second["USD"] == 2
    assert "QQQ" not in second
