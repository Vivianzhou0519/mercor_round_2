# Sniff a CSV dialect and cut it into records

`csvdialect.py` deals with delimiter-separated exports whose fields may be quoted. Two
functions are public:

```python
def parse_rows(text: str, delimiter: str = ",") -> list[list[str]]
def sniff(sample: str) -> str
```

Today `parse_rows` hands each line to `str.split`, so a spreadsheet export in which one
column holds a comma or a paragraph break comes back shredded into extra columns and
extra rows, and `sniff` just picks whichever candidate character occurs most often in
the whole blob. Rewrite both so every point below holds.

## `parse_rows`

1. **Records.** `text` is a run of records separated by `\n`. A `\n` at the very end of
   `text` closes the final record rather than opening another. Empty `text` gives back
   `[]`.
2. **An empty line in the middle of the text is a record of one empty field**, `[""]`.
3. **Fields.** Inside a record, `delimiter` separates fields. When `delimiter` is the
   last character of a record, the record gains a trailing empty field.
4. **Quoting.** A field counts as quoted when its opening character is `"`. Everything
   between that `"` and the closing `"` is content: a `delimiter` or a `\n` sitting
   inside a quoted field is just a character and separates nothing.
5. **Escaping.** Two `"` characters back to back inside a quoted field stand for a
   single literal `"` and leave the field open.
6. **Elsewhere a `"` is unremarkable.** Because `ab"c` does not open with a quote, it is
   the four-character field `ab"c`, quotes and all.
7. **Nothing is trimmed.** Spaces around a field belong to the field. Quoted fields lose
   their two enclosing quotes and keep everything else.
8. **Damaged input raises `ValueError`:** a quoted field still open when `text` runs
   out, or any character other than `delimiter` or `\n` immediately following a
   closing `"`.
9. **`delimiter` is exactly one character** and cannot be `"` or `\n`; anything else is
   a `ValueError`.

## `sniff`

10. `sniff` reports which delimiter best accounts for `sample`. The candidates, in this
    order, are `,` then `;` then a tab then `|`.
11. A candidate qualifies when `parse_rows(sample, delimiter=candidate)` completes
    without raising, yields one or more records, and hands every record the identical
    field count -- a count of 2 or more.
12. The qualifying candidate whose records carry the most fields wins. Should two tie on
    field count, the earlier candidate in the order above takes it.
13. When nothing qualifies, `sniff` raises `ValueError`.

Keep both names and signatures as written above.
