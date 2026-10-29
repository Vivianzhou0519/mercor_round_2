def total(items):
    """Sum the line items and round to 2 decimal places."""
    subtotal = 0.0
    for item in items:
        subtotal += item["unit_price"] * item["quantity"]
    return round(subtotal, 2)
