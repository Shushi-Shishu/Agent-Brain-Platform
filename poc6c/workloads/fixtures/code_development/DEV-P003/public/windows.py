"""Booking-window operations."""


def merge_windows(windows):
    """Merge overlapping half-open integer windows."""

    ordered = sorted(windows)
    for start, end in ordered:
        if start >= end:
            raise ValueError("window start must be before end")
    merged = []
    for start, end in ordered:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            old_start, old_end = merged[-1]
            merged[-1] = (old_start, max(old_end, end))
    return merged
