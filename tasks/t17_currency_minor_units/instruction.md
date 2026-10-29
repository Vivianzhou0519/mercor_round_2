# Quote money in the right number of decimal places

The settlement service stores every amount as a whole number of *minor units* -- cents
for the dollar, fils for the dinar, and nothing at all for the yen, which has no
subdivision. How many decimal places a currency carries is its **ISO 4217 minor unit
exponent**. That number is published data; it cannot be computed from the code.

Two modules are involved.

## `iso4217.py`

```python
def minor_unit_table() -> dict[str, int]
```

The pilot cut of this table lists six currencies, all of them with two decimal places,
which is why every non-dollar account reconciles a factor of ten or a hundred out.
Replace it with the real thing.

1. **The table is the published ISO 4217 exponent list**, restricted to the currencies
   we settle in -- **at least 40 codes**. Every key is exactly three uppercase ASCII
   letters and every value is one of `0`, `2`, `3` or `4`. The published values are
   authoritative, so `JPY` is `0`, `USD` is `2`, `KWD` is `3` and `CLF` is `4`.
   `ISK` is `0` as well -- Iceland dropped the eyrir, and it is the zero-exponent
   case we hit most often outside Japan, so it must be in the table.
2. **Each call hands back a fresh mapping.** Callers annotate the table for their own
   reporting, so mutating what one call returned must not change what the next call
   returns.

## `money.py`

```python
def minor_units(code: str) -> int
def to_minor(amount: str, code: str) -> int
def format_minor(minor: int, code: str) -> str
```

`minor_units(code)` resolves a currency code to its exponent.

3. **Codes are normalised before lookup**: surrounding whitespace is stripped and the
   code is upper-cased, so `" jpy "` resolves the same as `"JPY"`.
4. **A malformed code is a `ValueError`.** After normalisation the code must be exactly
   three ASCII letters; `"US"`, `"USDD"`, `"US1"` and `""` are all rejected.
5. **An unlisted code falls back to `2`.** New codes reach us before the table is
   updated, and two places is the documented default rather than an error.

`to_minor(amount, code)` converts a major unit amount into minor units.

6. **`amount` is a decimal string** matching `-?[0-9]+(\.[0-9]+)?` exactly: an optional
   leading `-`, at least one integer digit, and an optional fractional part. Anything
   else -- `""`, `"1e5"`, `"nan"`, `"1.2.3"`, `" 1"`, `"1,5"`, a leading `+` -- raises
   `ValueError`. Do not strip whitespace from `amount`; only `code` is normalised.
7. **The amount is scaled by the currency's exponent**, so `"12.34"` in `USD` is `1234`
   and `"1.234"` in `KWD` is also `1234`.
8. **Digits past the exponent are rounded half up**, not to even and not truncated:
   `"12.345"` in `USD` is `1235`, `"12.344"` is `1234`, and `"0.5"` in a zero-exponent
   currency is `1`.
9. **Negative amounts round away from zero and keep their sign**, so `"-12.345"` in
   `USD` is `-1235`. Rounding looks at the magnitude, and the sign is reapplied
   afterwards.

`format_minor(minor, code)` renders stored minor units for display.

10. **The result is the normalised code, a single space, then the number**, for example
    `"USD 1,234.56"`. The code is normalised exactly as in rule 3.
11. **The number carries exactly `exponent` digits after the decimal point**, zero
    padded on both sides as needed: `format_minor(5, "USD")` is `"USD 0.05"` and
    `format_minor(0, "CLF")` is `"CLF 0.0000"`. When the exponent is `0` there is no
    decimal point at all -- `"JPY 1,234"`, never `"JPY 1,234."`.
12. **The integer part is grouped in threes with `,`**, counting from the right. The
    fractional digits are never grouped: `1234567` in `KWD` is `"KWD 1,234.567"`.
13. **A negative renders one `-` immediately before the integer part**, after the space
    that follows the code: `"USD -1,234.56"`. Zero is never signed.
14. **`minor` must be an `int`** (a `bool` does not count); anything else raises
    `ValueError`. `format_minor` does no rounding of its own -- it is handed exact minor
    units and lays them out.

Keep the four function names and signatures exactly as they are; the ledger exporter and
the statement renderer both import them by name.
