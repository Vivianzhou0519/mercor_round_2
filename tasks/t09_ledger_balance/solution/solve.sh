#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/ledger.py" << '__HARBOR_EOF__'
def audit(entries):
    """Summarise a list of (txn_id, account, amount) double-entry postings."""
    totals = {}
    balances = {}
    debits = 0
    credits = 0

    for txn_id, account, amount in entries:
        totals[txn_id] = totals.get(txn_id, 0) + amount
        balances[account] = balances.get(account, 0) + amount
        if amount > 0:
            debits += amount
        elif amount < 0:
            credits -= amount

    return {
        "unbalanced": sorted(txn_id for txn_id, total in totals.items() if total != 0),
        "balances": {account: net for account, net in balances.items() if net != 0},
        "debits": debits,
        "credits": credits,
    }
__HARBOR_EOF__
