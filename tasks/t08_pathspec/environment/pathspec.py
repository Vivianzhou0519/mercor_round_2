import fnmatch


def matches(path, patterns):
    """Return True if `path` matches any of `patterns`."""
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False
