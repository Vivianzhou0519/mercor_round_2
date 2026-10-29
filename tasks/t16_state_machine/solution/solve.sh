#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/lexer.py" << '__HARBOR_EOF__'
import string

WHITESPACE = " \t\r\n"
NAME_START = string.ascii_letters + "_"
NAME_BODY = string.ascii_letters + string.digits + "_"
OPERATORS = ("**", "+", "-", "*", "/", "%")


class LexError(ValueError):
    """Raised on a character that cannot start a token."""

    def __init__(self, message, pos):
        super().__init__(message)
        self.pos = pos


def _scan_number(source, start):
    """Index just past the NUMBER beginning at `start`."""
    end = start
    while end < len(source) and source[end] in string.digits:
        end += 1
    # The dot belongs to the number only when at least one digit follows it.
    if end + 1 < len(source) and source[end] == "." and source[end + 1] in string.digits:
        end += 1
        while end < len(source) and source[end] in string.digits:
            end += 1
    return end


def _scan_name(source, start):
    """Index just past the NAME beginning at `start`."""
    end = start + 1
    while end < len(source) and source[end] in NAME_BODY:
        end += 1
    return end


def tokenize(source):
    """Split `source` into a list of (kind, text) tokens."""
    tokens = []
    i = 0
    while i < len(source):
        ch = source[i]
        if ch in WHITESPACE:
            i += 1
        elif ch == "(":
            tokens.append(("LPAREN", ch))
            i += 1
        elif ch == ")":
            tokens.append(("RPAREN", ch))
            i += 1
        elif ch in string.digits:
            end = _scan_number(source, i)
            tokens.append(("NUMBER", source[i:end]))
            i = end
        elif ch in NAME_START:
            end = _scan_name(source, i)
            tokens.append(("NAME", source[i:end]))
            i = end
        else:
            # Longest match first, so "**" wins over "*".
            for op in OPERATORS:
                if source.startswith(op, i):
                    tokens.append(("OP", op))
                    i += len(op)
                    break
            else:
                raise LexError("unexpected character %r at %d" % (ch, i), i)
    return tokens
__HARBOR_EOF__
