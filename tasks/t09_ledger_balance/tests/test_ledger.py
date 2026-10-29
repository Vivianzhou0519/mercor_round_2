from ledger import audit

# Three transactions: a sale, the month's rent, and a sale that was keyed in wrong.
JOURNAL = [
    ("t2", "cash", 12000),
    ("t2", "revenue", -12000),
    ("t1", "rent", 90000),
    ("t1", "cash", -90000),
    ("t3", "cash", 5000),
    ("t3", "revenue", -4500),
]


def test_unbalanced_transaction_is_reported():
    assert audit(JOURNAL)["unbalanced"] == ["t3"]


def test_balances_net_across_transactions():
    assert audit(JOURNAL)["balances"] == {
        "cash": -73000,
        "revenue": -16500,
        "rent": 90000,
    }


def test_debit_and_credit_totals():
    result = audit(JOURNAL)
    assert result["debits"] == 107000
    assert result["credits"] == 106500


def test_credits_are_never_negative():
    result = audit([("t1", "cash", -250), ("t1", "revenue", -750)])
    assert result["credits"] == 1000
    assert result["debits"] == 0


def test_unbalanced_is_sorted_and_deduplicated():
    entries = [
        ("b", "cash", 100),
        ("a", "cash", 50),
        ("c", "cash", 25),
        ("a", "cash", 50),
    ]
    assert audit(entries)["unbalanced"] == ["a", "b", "c"]


def test_single_posting_transaction_is_unbalanced():
    assert audit([("t1", "cash", 500)])["unbalanced"] == ["t1"]


def test_account_that_nets_to_zero_is_omitted():
    entries = [
        ("t1", "cash", 2500),
        ("t1", "fees", -2500),
        ("t2", "cash", -2500),
        ("t2", "revenue", 2500),
    ]
    result = audit(entries)
    assert result["balances"] == {"fees": -2500, "revenue": 2500}
    assert result["unbalanced"] == []


def test_zero_amount_postings_contribute_nothing():
    entries = [
        ("t1", "cash", 700),
        ("t1", "revenue", -700),
        ("t1", "suspense", 0),
    ]
    result = audit(entries)
    assert result == {
        "unbalanced": [],
        "balances": {"cash": 700, "revenue": -700},
        "debits": 700,
        "credits": 700,
    }


def test_empty_journal():
    assert audit([]) == {
        "unbalanced": [],
        "balances": {},
        "debits": 0,
        "credits": 0,
    }


def test_input_is_not_mutated():
    entries = list(JOURNAL)
    before = list(entries)
    audit(entries)
    assert entries == before
