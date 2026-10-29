import re

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(title):
    """Turn `title` into a URL slug."""
    lowered = title.lower()
    collapsed = _NON_ALNUM.sub("-", lowered)
    return collapsed.strip("-")
