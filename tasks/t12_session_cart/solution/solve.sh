#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/cart.py" << '__HARBOR_EOF__'
"""Checkout cart for a single session.

The cart is module-level state: import the module and you are in the session.
"""

_CODES = {"SAVE10": 10, "HALFOFF": 50}

_CART = {}
_DISCOUNT_CODE = None


def add_item(sku, unit_price_cents, quantity=1):
    """Put `quantity` more units of `sku` in the cart at `unit_price_cents` each.

    A repeat SKU keeps its original position in the cart and accumulates quantity;
    the unit price is refreshed to the one just supplied.
    """
    existing = _CART.get(sku)
    if existing is None:
        _CART[sku] = (unit_price_cents, quantity)
    else:
        _CART[sku] = (unit_price_cents, existing[1] + quantity)


def line_items():
    """The cart as (sku, unit_price_cents, quantity) tuples, in insertion order."""
    return [(sku, price, qty) for sku, (price, qty) in _CART.items()]


def apply_discount(code):
    """Store `code` as the session's discount if we recognise it."""
    global _DISCOUNT_CODE
    if code not in _CODES:
        return False
    _DISCOUNT_CODE = code
    return True


def subtotal():
    """Sum of every line, in cents."""
    return sum(price * qty for price, qty in _CART.values())


def total():
    """What the customer pays, in cents, after the session's discount."""
    gross = subtotal()
    if _DISCOUNT_CODE is None:
        return gross
    return gross - gross * _CODES[_DISCOUNT_CODE] // 100


def clear():
    """End the session: empty the cart and forget the discount."""
    global _DISCOUNT_CODE
    _CART.clear()
    _DISCOUNT_CODE = None
__HARBOR_EOF__
