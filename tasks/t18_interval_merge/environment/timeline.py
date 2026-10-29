"""Collapse reported maintenance windows into the schedule's canonical cover."""


def merge(intervals):
    """Merge the half-open windows in `intervals` into a sorted, disjoint cover."""
    intervals.sort(key=lambda window: window[0])
    merged = []
    for window in intervals:
        start, end = window[0], window[1]
        if merged and start < merged[-1][1]:
            merged[-1] = [merged[-1][0], end]
        else:
            merged.append([start, end])
    return merged
