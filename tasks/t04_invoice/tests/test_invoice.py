from invoice import format_money, line_total, total

ITEMS = [
    {"description": "widget", "unit_price": 1.005, "quantity": 1},
    {"description": "gadget", "unit_price": 2.675, "quantity": 1},
]


def test_half_up_rounding():
    assert total([{"description": "x", "unit_price": 2.675, "quantity": 1}]) == 2.68
    assert total([{"description": "x", "unit_price": 2.665, "quantity": 1}]) == 2.67


def test_multiple_line_items():
    assert total(ITEMS) == 3.69


def test_empty_invoice():
    assert total([]) == 0.0


def test_line_total_helper():
    assert line_total({"description": "x", "unit_price": 0.125, "quantity": 1}) == 0.13
    assert line_total({"description": "x", "unit_price": 2.5, "quantity": 4}) == 10.0


def test_format_money():
    assert format_money(3.5) == "$3.50"
    assert format_money(3.5, "EUR") == "\u20ac3.50"


def test_total_accepts_a_currency():
    assert total(ITEMS, currency="EUR") == "\u20ac3.69"
