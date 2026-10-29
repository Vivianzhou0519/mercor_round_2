#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/invoice.py" << '__HARBOR_EOF__'
from decimal import ROUND_HALF_UP, Decimal

SYMBOLS = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3"}


def _half_up(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def line_total(item):
    """Return the half-up rounded total for a single line item."""
    return _half_up(item["unit_price"] * item["quantity"])


def format_money(value, currency="USD"):
    """Render `value` as a currency string, e.g. ``$3.50``."""
    return "%s%.2f" % (SYMBOLS[currency], _half_up(value))


def total(items, currency=None):
    """Sum the line items and round half-up to 2 decimal places."""
    amount = _half_up(sum(line_total(item) for item in items))
    if currency is None:
        return amount
    return format_money(amount, currency)
__HARBOR_EOF__
