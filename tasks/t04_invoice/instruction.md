# Use half-up rounding for invoice totals

`invoice.py` sums line items and rounds the result:

```python
def total(items) -> float
```

`items` is a list of dicts shaped like
`{"description": str, "unit_price": float, "quantity": int}`.

`total()` currently uses Python's built-in `round()`, which rounds halves to even
("banker's rounding"), so `2.675` becomes `2.67` and our totals disagree with the
billing system by a cent.

Fix `total()` so monetary values are rounded **half-up** to 2 decimal places
(`2.675 -> 2.68`, `2.665 -> 2.67`).
