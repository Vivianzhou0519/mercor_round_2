def fill(text, width):
    """Reflow `text` into lines of at most `width` characters."""
    tokens = text.split(" ")
    lines = []
    line = ""
    for token in tokens:
        if line:
            line = line + " " + token
        else:
            line = token
        if len(line) > width:
            lines.append(line)
            line = ""
    if line:
        lines.append(line)
    return lines
