# A tiny config parser

Implement `parse(text)` in `configlite.py`. The format is one `key: value` per line:

- Blank lines, and lines whose first non-space character is `#`, are ignored.
- A line of the form `[section]` opens a section: keys after it nest under
  `result["section"]`. Keys before any section header live at the top level. Sections
  do not nest.
- Values are typed. `true` / `false` (case-insensitive) become booleans; a value made
  only of digits, with an optional leading `-`, becomes an `int`; anything else is a
  string with surrounding whitespace stripped.
- A value wrapped in double quotes is always a string, and the quotes are removed
  (whitespace inside the quotes is preserved).
- A duplicate key inside the same section overwrites the earlier one.
- Raise `ValueError` on a line that is not blank, a comment, a section header, or a
  `key: value` pair.
