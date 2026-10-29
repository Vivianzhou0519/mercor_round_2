"""Scale and render monetary amounts for the settlement service."""

from iso4217 import minor_unit_table


def minor_units(code):
    """Number of decimal places `code` is quoted to."""
    return minor_unit_table()[code]


def to_minor(amount, code):
    """Convert a major unit decimal string to a whole number of minor units."""
    return round(float(amount) * (10 ** minor_units(code)))


def format_minor(minor, code):
    """Render a whole number of minor units as a display string."""
    exponent = minor_units(code)
    return "%s %s" % (code, minor / (10 ** exponent))
