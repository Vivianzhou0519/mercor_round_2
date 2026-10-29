# Fix the checkout cart's totals

`cart.py` holds the shopping cart for one checkout session. The cart lives in
module-level state, so the module is the session: importing it gives you one cart and
the functions that operate on it.

```python
def add_item(sku: str, unit_price_cents: int, quantity: int = 1) -> None
def line_items() -> list[tuple[str, int, int]]
def apply_discount(code: str) -> bool
def subtotal() -> int
def total() -> int
def clear() -> None
```

The version in the repo was written for a single-item demo and gets several things
wrong once a real basket goes through it. Fix `cart.py` so that all of the following
hold. Keep the names and signatures above.

1. **Adding the same SKU twice adds to it.** `add_item` records a line for `sku` with
   the given `unit_price_cents` and `quantity`. If that `sku` is already in the cart,
   the quantities are summed and the unit price is updated to the one just supplied.
   The line keeps the position it had when the SKU was first added.
2. **`line_items()` reports the cart in insertion order**, as a list of
   `(sku, unit_price_cents, quantity)` tuples -- first SKU added first.
3. **`subtotal()` is the sum of `unit_price_cents * quantity` over every line**, in
   whole cents. An empty cart has a subtotal of `0`.
4. **Only known discount codes are accepted.** The codes are `"SAVE10"` (10% off) and
   `"HALFOFF"` (50% off). `apply_discount` returns `True` for a known code and stores
   it as the session's discount, replacing any code stored earlier. For anything else
   it returns `False` and leaves the stored discount exactly as it was.
5. **`total()` applies the stored discount.** With a discount of `percent`, the
   reduction is `subtotal() * percent // 100` -- integer floor division, so the result
   is always whole cents -- and `total()` returns `subtotal()` minus that reduction.
   With no discount stored, `total()` equals `subtotal()`.
6. **`clear()` ends the session.** It empties the cart *and* drops any stored discount
   code, so the next `total()` after a `clear()` is undiscounted.

All prices and quantities are non-negative integers. Return real `int` values from
`subtotal()` and `total()`, and a real `bool` from `apply_discount()`.
