"""Read delimiter-separated exports. Quoting is not handled yet."""

CANDIDATES = (",", ";", "\t", "|")


def parse_rows(text, delimiter=","):
    """Cut `text` into records, then each record into fields."""
    rows = []
    for line in text.splitlines():
        rows.append(line.split(delimiter))
    return rows


def sniff(sample):
    """Guess the delimiter by counting candidate characters in `sample`."""
    tally = {candidate: sample.count(candidate) for candidate in CANDIDATES}
    return max(CANDIDATES, key=lambda candidate: tally[candidate])
