import cart


def test_add_item_records_a_line():
    cart.clear()
    cart.add_item("APPLE", 149)
    cart.add_item("BREAD", 320, quantity=2)
    assert cart.line_items() == [("APPLE", 149, 1), ("BREAD", 320, 2)]


def test_repeat_sku_accumulates_quantity():
    cart.add_item("APPLE", 149, quantity=3)
    assert cart.line_items() == [("APPLE", 149, 4), ("BREAD", 320, 2)]


def test_subtotal_sums_every_line():
    assert cart.subtotal() == 1236  # 149 * 4 + 320 * 2


def test_unknown_discount_code_is_rejected():
    assert cart.apply_discount("BOGUS") is False
    assert cart.total() == 1236


def test_known_discount_code_reduces_the_total():
    assert cart.apply_discount("SAVE10") is True
    assert cart.total() == 1113  # 1236 - 1236 * 10 // 100, i.e. the 123.6 floors to 123


def test_applying_a_second_code_replaces_the_first():
    assert cart.apply_discount("HALFOFF") is True
    assert cart.total() == 618


def test_rejected_code_leaves_the_stored_discount_alone():
    assert cart.apply_discount("SAVE5") is False
    assert cart.total() == 618


def test_clear_ends_the_session():
    cart.clear()
    assert cart.line_items() == []
    assert cart.subtotal() == 0
    cart.add_item("MILK", 200, quantity=2)
    assert cart.total() == 400  # no discount is in effect after clear()
