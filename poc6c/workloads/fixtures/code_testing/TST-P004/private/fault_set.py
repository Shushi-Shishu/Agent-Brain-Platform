"""Evaluator-only deterministic faults for TST-P004."""

FAULTS = [
    {
        "fault_id": "TST-P004-F01-truncated-pairs",
        "source": '''import math
def weighted_average(values, weights):
    samples, factors = list(values), list(weights)
    if not samples or not factors:
        raise ValueError("values and weights need nonzero length")
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in samples):
        raise ValueError("values must be finite numbers")
    if any(not isinstance(w, (int, float)) or not math.isfinite(w) or w < 0 for w in factors):
        raise ValueError("weights must be finite and nonnegative")
    pairs = list(zip(samples, factors))
    total = sum(w for _, w in pairs)
    if total == 0:
        raise ValueError("total weight must be positive")
    return sum(v * w for v, w in pairs) / total
''',
    },
    {
        "fault_id": "TST-P004-F02-negative-weight-absolute",
        "source": '''import math
def weighted_average(values, weights):
    samples, factors = list(values), [abs(w) for w in weights]
    if not samples or len(samples) != len(factors):
        raise ValueError("values and weights need equal nonzero length")
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in samples):
        raise ValueError("values must be finite numbers")
    if any(not isinstance(w, (int, float)) or not math.isfinite(w) for w in factors):
        raise ValueError("weights must be finite and nonnegative")
    total = sum(factors)
    if total == 0:
        raise ValueError("total weight must be positive")
    return sum(v * w for v, w in zip(samples, factors)) / total
''',
    },
    {
        "fault_id": "TST-P004-F03-rounded-result",
        "source": '''import math
def weighted_average(values, weights):
    samples, factors = list(values), list(weights)
    if not samples or len(samples) != len(factors):
        raise ValueError("values and weights need equal nonzero length")
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in samples):
        raise ValueError("values must be finite numbers")
    if any(not isinstance(w, (int, float)) or not math.isfinite(w) or w < 0 for w in factors):
        raise ValueError("weights must be finite and nonnegative")
    total = sum(factors)
    if total == 0:
        raise ValueError("total weight must be positive")
    return round(sum(v * w for v, w in zip(samples, factors)) / total, 2)
''',
    },
]
