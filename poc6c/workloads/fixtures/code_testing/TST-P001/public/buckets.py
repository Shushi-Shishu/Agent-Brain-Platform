"""Assign finite numeric values to ordered boundary buckets."""

import math


def bucket_index(value, boundaries):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be a number")
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    points = tuple(boundaries)
    if any(
        isinstance(point, bool)
        or not isinstance(point, (int, float))
        or not math.isfinite(point)
        for point in points
    ):
        raise TypeError("boundaries must be finite numbers")
    if any(left >= right for left, right in zip(points, points[1:])):
        raise ValueError("boundaries must be strictly increasing")
    return sum(value >= point for point in points)
