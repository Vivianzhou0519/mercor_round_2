# Bucket usage samples into billing days and periods

`billing.py` turns the Unix timestamp on a usage sample into the keys the metering
pipeline aggregates on:

```python
def day_key(ts: int) -> str
def period_key(ts: int) -> str
def day_range(start_ts: int, end_ts: int) -> list[str]
```

Two bugs are visible in the exported invoices. Days come back with the month and the
day of the month the wrong way round (`2026-04-02` for the 4th of February), which also
corrupts the period key that is sliced out of them. And a period that ends on the day
an invoice is cut is short one day, because `day_range()` stops before the timestamp it
was handed.

Fix all three functions so that:

1. **`day_key(ts)` returns the calendar day the sample falls on**, formatted
   `YYYY-MM-DD`, zero padded.
2. **`period_key(ts)` returns the billing period the sample falls on**, formatted
   `YYYY-MM`. We bill on whole calendar months, so the period is just the year and
   month of the same calendar day, and `period_key(ts) == day_key(ts)[:7]` always
   holds.
3. **`day_range(start_ts, end_ts)` returns every day key from the day containing
   `start_ts` through the day containing `end_ts`**, inclusive at both ends, ascending,
   with no repeats. A range whose endpoints land on the same day is a one-element list.
4. **A backwards range is empty.** If `end_ts` is earlier than `start_ts`, return `[]`.
5. **`day_range()` must stay correct across month and year boundaries.** Month lengths
   differ, so a range that opens in one month and closes in another still lists every
   day in between exactly once.

Timestamps are whole seconds and are always positive. Keep the three function names and
signatures exactly as they are; the metering pipeline imports them by name.
