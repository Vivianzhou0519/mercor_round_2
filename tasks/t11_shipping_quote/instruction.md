# Price a parcel against the published rate card

`shipping.py` exposes the pricing entry point:

```python
def quote(weight_kg: float, distance_km: int) -> float
```

It was written against an older rate card and no longer matches what the billing
system charges. Fix it so that a quote is built in this order:

1. **Base rate by weight band.** `weight_kg` is a positive float.
   - up to and including 1 kg: `4.50`
   - over 1 kg, up to and including 5 kg: `7.25`
   - over 5 kg, up to and including 20 kg: `12.00`
   - over 20 kg: `12.00` plus `0.60` for each kilogram *or part of a kilogram*
     above 20 (so 22.4 kg is `12.00 + 3 * 0.60 = 13.80`)
2. **Distance multiplier.** Multiply the base rate by `1 + 0.02 * h`, where `h` is
   the number of *complete* hundreds of kilometres in `distance_km`. A 120 km leg
   and a 199 km leg both use `1.02`; 0 km uses `1.00`. `distance_km` is a
   non-negative integer.
3. **Long-haul surcharge.** If `distance_km` is **strictly greater than** 1000, add a
   flat `6.00` to the amount from step 2. Exactly 1000 km is not long haul.
4. **Rounding.** Round the result to the nearest cent, halves rounding up, and
   return it as a float.

Do not change `quote`'s name or signature. Helpers are fine.
