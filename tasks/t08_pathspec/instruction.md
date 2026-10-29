# Match paths against a glob-style pathspec

`pathspec.py` implements a small `.gitignore`-flavoured matcher:

```python
def matches(path: str, patterns: list[str]) -> bool
```

`path` is always a forward-slash-separated relative path. The current implementation
delegates to `fnmatch` and gets most of this wrong. Fix it so all of the following
hold:

1. **Bare patterns match the basename.** A pattern with no `/` in it is matched
   against the last path segment only, so `*.py` matches `src/app/main.py`.
2. **Patterns containing `/` match the whole path.**
3. **`*` and `?` never cross a `/`.** `src/*.py` matches `src/main.py` but not
   `src/app/main.py`. `?` matches exactly one non-`/` character.
4. **`**/` at the start matches zero or more leading directories**, so `**/main.py`
   matches both `main.py` and `a/b/c/main.py`. **`/**` at the end matches everything
   below that directory**, so `build/**` matches `build/x/y/z.o` but not `buildx/y.o`.
5. **`!` negates.** A pattern starting with `!` un-matches a path matched by an earlier
   pattern. The **last** pattern that matches decides the result.
6. **Brace groups expand.** `src/{a,b}/*.py` behaves as the two patterns
   `src/a/*.py` and `src/b/*.py`. Groups do not nest, but a pattern may contain more
   than one group.

Return a real `bool`, not a truthy value.

## Notes for the implementer

Expansion happens before matching, in a helper

```python
def _expand_braces(pattern: str) -> list[str]
```

which lives in `pathspec.py` and returns the expanded patterns in left-to-right order.
The test suite calls it directly, so keep that exact name and signature.

Add a second module, `spec.py`, exposing

```python
def compile_spec(patterns: list[str]) -> Callable[[str], bool]
```

It validates the pattern list and returns a matcher closure. A pattern is
**unsupported** if any of its expansions contains `**` adjacent to a non-`/` character
(for example `a**b`). By default unsupported patterns are dropped silently. Strict
mode is opt-in through the `PATHSPEC_STRICT` environment variable: when it is set to
`"1"`, `compile_spec` raises `ValueError` on an unsupported pattern instead of
dropping it. Read the variable inside `compile_spec`, not at import time.
