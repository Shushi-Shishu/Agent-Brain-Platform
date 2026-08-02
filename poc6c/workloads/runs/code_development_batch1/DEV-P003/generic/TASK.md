# Merge booking windows

`merge_windows(windows)` receives `(start, end)` integer pairs and returns a
sorted list with overlapping windows merged.

Each pair uses a half-open interval: the start is included and the end is
excluded. Therefore `(1, 3)` and `(3, 5)` merely touch and must remain separate.
Raise `ValueError` when a window has `start >= end`. The input may be unsorted
and must not be modified.
