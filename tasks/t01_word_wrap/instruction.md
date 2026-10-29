# Wrap text to a fixed column width

`wordwrap.py` exposes a single function:

```python
def wrap(text: str, width: int) -> list[str]
```

It currently produces lines that overflow `width`. Fix it so that it satisfies all of
the following:

1. **Greedy packing.** Fill each line with as many whitespace-separated words as fit
   without exceeding `width` characters. Words on a line are joined by a single space.
2. **Long words are never split.** A word longer than `width` gets a line of its own
   and is emitted unchanged, even though that line then exceeds `width`.
3. **Whitespace is collapsed.** Any run of whitespace in the input (spaces, tabs,
   newlines) is a single separator. Returned lines never have leading or trailing
   whitespace.
4. **Empty input.** If `text` contains no words, return `[]`.
5. `width` is always at least 1.

Do not change the function's name or signature.
