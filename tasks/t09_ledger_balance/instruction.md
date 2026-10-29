# Audit a set of double-entry postings

`ledger.py` exposes a single function:

```python
def audit(entries: list[tuple[str, str, int]]) -> dict
```

Each entry is a `(txn_id, account, amount)` triple. `amount` is a whole number of cents:
positive for a debit, negative for a credit. Several entries share a `txn_id` when they
belong to the same transaction.

The current implementation reports credits with the wrong sign and lists accounts that
have netted out to nothing. Fix it so `audit` returns a dict with exactly these keys:

- `"unbalanced"` -- the `txn_id` of every transaction whose postings do not sum to
  zero, sorted ascending, each id appearing once.
- `"balances"` -- a dict mapping account name to its net total across all entries.
  Accounts whose net total is zero are left out entirely.
- `"debits"` -- the sum of every positive amount.
- `"credits"` -- the sum of the *absolute values* of every negative amount, so this is
  never negative.

Additional rules:

1. **Every transaction is checked**, including one that has only a single posting. A
   lone `("t1", "cash", 500)` is unbalanced.
2. **Zero-amount postings are legal.** They contribute nothing to `debits` or
   `credits`, and an account that only ever sees zero postings does not appear in
   `"balances"`.
3. **Unbalanced transactions still count.** Their postings are included in
   `"balances"`, `"debits"` and `"credits"` like any other.
4. `audit([])` returns `{"unbalanced": [], "balances": {}, "debits": 0, "credits": 0}`.
5. Do not mutate the list passed in.

Do not change the function's name or signature.
