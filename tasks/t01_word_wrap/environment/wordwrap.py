def wrap(text, width):
    """Wrap `text` so that no line exceeds `width` characters."""
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        if current == "":
            current = word
        else:
            current = current + " " + word
        if len(current) >= width:
            lines.append(current)
            current = ""
    if current:
        lines.append(current)
    return lines
