import string


class LexError(ValueError):
    """Raised on a character that cannot start a token."""

    def __init__(self, message, pos):
        super().__init__(message)
        self.pos = pos


def tokenize(source):
    """Split `source` into a list of (kind, text) tokens."""
    tokens = []
    for chunk in source.split():
        if chunk[0] in string.digits:
            tokens.append(("NUMBER", chunk))
        elif chunk[0] in "+-*/%()":
            tokens.append(("OP", chunk))
        else:
            tokens.append(("NAME", chunk))
    return tokens
