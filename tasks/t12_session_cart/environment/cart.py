"""Checkout cart for a single session.

The cart is module-level state: import the module and you are in the session.
"""

_CODES = {"SAVE10": 10, "HALFOFF": 50}

_CART = {}
_DISCOUNT_CODE = None


def add_item(sku, unit_price_cents, quantity=1):
    """Put `quantity` units of `sku` in the cart at `unit_price_cents` each."""
    _CART[sku] = (unit_price_cents, quantity)


def line_items():
    """The cart as (sku, unit_price_cents, quantity) tuples."""
    return [(sku, price, qty) for sku, (price, qty) in _CART.items()]


def apply_discount(code):
    """Store `code` as the session's discount."""
    global _DISCOUNT_CODE
    _DISCOUNT_CODE = code
    return True


def subtotal():
    """Sum of every line, in cents."""
    return sum(price * qty for price, qty in _CART.values())


def total():
    """What the customer pays, in cents."""
    return subtotal()


def clear():
    """End the session."""
    _CART.clear()
