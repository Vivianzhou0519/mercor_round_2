# Tokenise an arithmetic expression

`lexer.py` is the front end of a small expression evaluator. It turns the raw text of
an expression into a flat list of tokens for the parser to consume:

```python
def tokenize(source: str) -> list[tuple[str, str]]
```

Each token is a `(kind, text)` pair, and the list is in source order. `text` is the
exact slice of `source` the token was read from.

The current implementation splits on whitespace and classifies each chunk by its first
character, so it can only ever see token boundaries the input already spelled out with
spaces: `2*x` comes back as a single token. It also lumps the parentheses in with the
operators and never rejects anything. Rewrite it as a left-to-right scanner that
satisfies all of the following.

1. **Whitespace separates tokens and is never emitted.** The whitespace characters are
   space, tab, carriage return and newline. Tokens do not need whitespace around them:
   `2*x` is three tokens.
2. **`NUMBER`** is one or more ASCII digits, optionally followed by `.` and one or more
   further digits. The `.` joins the number only when a digit follows it, so `3.5` is
   one `NUMBER`, while in `3.x` the number stops at `3` and the `.` is left over.
   A `.` is never a token on its own, so whatever is left over is an error (rule 6).
3. **`NAME`** starts with an ASCII letter or `_`, and continues with any run of ASCII
   letters, ASCII digits and underscores.
4. **`(` is `LPAREN` and `)` is `RPAREN`**, each a token of its own. They are not
   operators.
5. **`OP`** is one of `**`, `+`, `-`, `*`, `/`, `%`. Matching is longest-first, so `**`
   is a single `OP` token rather than two `*` tokens, and `***` is `**` followed by `*`.
6. **Anything else is an error.** On a character that cannot start a token, raise
   `LexError` (defined in `lexer.py`, a subclass of `ValueError`). The exception carries
   the 0-based index of that character in `source` as an attribute named `pos`.
   Scanning stops there; no partial token list is returned.
7. **Input with no tokens gives `[]`.** An empty string, or one containing only
   whitespace, returns an empty list rather than raising.

Keep the module's public names — `tokenize`, `LexError`, and `LexError.pos` — exactly
as described. The five kind strings are `"NUMBER"`, `"NAME"`, `"OP"`, `"LPAREN"` and
`"RPAREN"`.
