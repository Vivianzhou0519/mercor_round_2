def delays(attempts, base=1.0, cap=30.0):
    """Return the sequence of backoff delays for `attempts` retries."""
    return [base * 2 ** i for i in range(attempts)]
