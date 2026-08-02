"""Evaluator-only deterministic faults for TST-P001."""

FAULTS = [
    {
        "fault_id": "TST-P001-F01-boundary-side",
        "source": '''import math
def bucket_index(value, boundaries):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be a number")
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    points = tuple(boundaries)
    if any(isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) for p in points):
        raise TypeError("boundaries must be finite numbers")
    if any(a >= b for a, b in zip(points, points[1:])):
        raise ValueError("boundaries must be strictly increasing")
    return sum(value > point for point in points)
''',
    },
    {
        "fault_id": "TST-P001-F02-duplicate-boundaries",
        "source": '''import math
def bucket_index(value, boundaries):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be a number")
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    points = tuple(boundaries)
    if any(isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) for p in points):
        raise TypeError("boundaries must be finite numbers")
    if any(a > b for a, b in zip(points, points[1:])):
        raise ValueError("boundaries must be increasing")
    return sum(value >= point for point in points)
''',
    },
    {
        "fault_id": "TST-P001-F03-boolean-value",
        "source": '''import math
def bucket_index(value, boundaries):
    if not isinstance(value, (int, float)):
        raise TypeError("value must be a number")
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    points = tuple(boundaries)
    if any(isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) for p in points):
        raise TypeError("boundaries must be finite numbers")
    if any(a >= b for a, b in zip(points, points[1:])):
        raise ValueError("boundaries must be strictly increasing")
    return sum(value >= point for point in points)
''',
    },
]
