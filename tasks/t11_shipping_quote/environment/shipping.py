def quote(weight_kg, distance_km):
    """Return the shipping cost in dollars for a single parcel."""
    if weight_kg <= 1.0:
        base = 4.50
    elif weight_kg <= 5.0:
        base = 7.25
    else:
        base = 12.00
    multiplier = 1.0 + 0.02 * (distance_km / 100.0)
    return round(base * multiplier, 2)
