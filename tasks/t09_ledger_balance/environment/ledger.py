def audit(entries):
    """Summarise a list of (txn_id, account, amount) double-entry postings."""
    totals = {}
    balances = {}
    unbalanced = []
    debits = 0
    credits = 0

    for txn_id, account, amount in entries:
        totals[txn_id] = totals.get(txn_id, 0) + amount
        balances[account] = balances.get(account, 0) + amount
        if amount > 0:
            debits += amount
        else:
            credits += amount

    for txn_id, total in totals.items():
        if total != 0:
            unbalanced.append(txn_id)

    return {
        "unbalanced": unbalanced,
        "balances": balances,
        "debits": debits,
        "credits": credits,
    }
