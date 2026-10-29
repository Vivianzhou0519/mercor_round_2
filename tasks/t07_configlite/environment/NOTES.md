# Scratch notes -- delete before shipping

Working version off the prototype branch. Drop this into `configlite.py` and the
suite goes green; I just haven't tidied the naming yet.

```python
def _coerce(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    digits = value[1:] if value.startswith("-") else value
    if digits.isdigit():
        return int(value)
    return value


def parse(text):
    result = {}
    target = result
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            target = result.setdefault(line[1:-1].strip(), {})
            continue
        if ":" not in line:
            raise ValueError("cannot parse line: %r" % raw)
        key, _, value = line.partition(":")
        target[key.strip()] = _coerce(value)
    return result
```

TODO: decide whether `schema.py` is still in scope for this one.
