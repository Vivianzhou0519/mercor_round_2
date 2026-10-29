#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/iso4217.py" << '__HARBOR_EOF__'
"""Minor unit exponents for the currencies the settlement service quotes in.

The exponent is how many digits a currency carries after the decimal point.
It is published data, not something a program can derive: the yen has no minor
unit at all, most currencies have two, the Gulf dinars have three, and the
Chilean unidad de fomento is quoted to four. The list below is transcribed from
ISO 4217 and covers every currency we are licensed to settle in.
"""


def minor_unit_table():
    """Return a fresh mapping of currency code to ISO 4217 minor unit exponent."""
    return {
        # no minor unit
        "BIF": 0, "CLP": 0, "DJF": 0, "GNF": 0, "ISK": 0, "JPY": 0,
        "KMF": 0, "KRW": 0, "PYG": 0, "RWF": 0, "UGX": 0, "VND": 0,
        "VUV": 0, "XAF": 0, "XOF": 0, "XPF": 0,
        # the common case
        "AED": 2, "AUD": 2, "BRL": 2, "CAD": 2, "CHF": 2, "CNY": 2,
        "COP": 2, "CZK": 2, "DKK": 2, "EUR": 2, "GBP": 2, "HKD": 2,
        "HUF": 2, "IDR": 2, "ILS": 2, "INR": 2, "MXN": 2, "MYR": 2,
        "NOK": 2, "NZD": 2, "PHP": 2, "PLN": 2, "RON": 2, "SEK": 2,
        "SGD": 2, "THB": 2, "TWD": 2, "USD": 2, "ZAR": 2,
        # Gulf dinars and the Tunisian dinar
        "BHD": 3, "IQD": 3, "JOD": 3, "KWD": 3, "LYD": 3, "OMR": 3,
        "TND": 3,
        # funds codes quoted to four places
        "CLF": 4, "UYW": 4,
    }
__HARBOR_EOF__

cat > "$APP_DIR/money.py" << '__HARBOR_EOF__'
"""Scale and render monetary amounts for the settlement service."""

import re

from iso4217 import minor_unit_table

DEFAULT_EXPONENT = 2
_CODE = re.compile(r"^[A-Z]{3}$")
_AMOUNT = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?$")


def minor_units(code):
    """Number of decimal places `code` is quoted to."""
    if not isinstance(code, str):
        raise ValueError("not a currency code: %r" % (code,))
    normalised = code.strip().upper()
    if not _CODE.match(normalised):
        raise ValueError("not a currency code: %r" % (code,))
    return minor_unit_table().get(normalised, DEFAULT_EXPONENT)


def to_minor(amount, code):
    """Convert a major unit decimal string to a whole number of minor units."""
    if not isinstance(amount, str) or not _AMOUNT.match(amount):
        raise ValueError("not a decimal amount: %r" % (amount,))
    exponent = minor_units(code)
    negative = amount.startswith("-")
    whole, _, frac = amount.lstrip("-").partition(".")
    # One extra digit is enough to decide a half-up tie: anything past it can
    # only push the remainder further away from the halfway point.
    frac = frac.ljust(exponent + 1, "0")
    scaled = int(whole + frac[:exponent])
    if int(frac[exponent]) >= 5:
        scaled += 1
    return -scaled if negative else scaled


def format_minor(minor, code):
    """Render a whole number of minor units as a display string."""
    if not isinstance(minor, int) or isinstance(minor, bool):
        raise ValueError("minor units must be an int: %r" % (minor,))
    exponent = minor_units(code)
    normalised = code.strip().upper()
    digits = str(abs(minor)).rjust(exponent + 1, "0")
    split = len(digits) - exponent
    whole, frac = digits[:split], digits[split:]
    grouped = ""
    while len(whole) > 3:
        grouped = "," + whole[-3:] + grouped
        whole = whole[:-3]
    number = whole + grouped
    if exponent:
        number += "." + frac
    return "%s %s%s" % (normalised, "-" if minor < 0 else "", number)
__HARBOR_EOF__
