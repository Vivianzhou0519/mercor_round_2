from datetime import datetime, timedelta


def render(events, start, days, generated_at):
    """Render a per-category, per-day count matrix as fixed-width text."""
    first = datetime.fromtimestamp(start).date()
    columns = [first + timedelta(days=i) for i in range(days)]
    grid = {}
    for category, at in events:
        day = datetime.fromtimestamp(at).date()
        if day in columns:
            row = grid.setdefault(category, [0] * days)
            row[columns.index(day)] += 1

    stamp = datetime.fromtimestamp(generated_at).strftime("%Y-%m-%d %H:%M")
    lines = ["generated %s UTC" % stamp]
    lines.append("      " + " ".join(day.strftime("%m-%d") for day in columns))
    for name in grid:
        lines.append(name + " " + " ".join(str(count) for count in grid[name]))
    return "\n".join(lines)
