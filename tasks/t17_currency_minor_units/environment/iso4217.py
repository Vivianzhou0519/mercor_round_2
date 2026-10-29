"""Minor unit exponents for the currencies the settlement service quotes in.

The exponent is how many digits a currency carries after the decimal point.
This is the pilot cut: it only lists the currencies the first two accounts
traded in, and every one of them happens to have two decimal places.
"""


def minor_unit_table():
    """Return the mapping of currency code to minor unit exponent."""
    return {"USD": 2, "EUR": 2, "GBP": 2, "CAD": 2, "AUD": 2, "CHF": 2}
