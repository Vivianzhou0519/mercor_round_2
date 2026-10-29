# `slugify()` leaves stray hyphens on the ends

`slug.py` turns a title into a URL slug: lowercased, alphanumerics kept, and every
run of other characters replaced by a single hyphen.

When the input starts or ends with punctuation or whitespace, the result currently
comes back with leading or trailing hyphens:

```python
>>> slugify("  Hello, World!  ")
'-hello-world-'          # should be 'hello-world'
```

Fix `slugify()` so leading and trailing hyphens are removed. Everything else about
its behaviour stays the same.
