"""Numerical helpers for finite weighted observations."""

import math


def weighted_average(values, weights):
    samples = list(values)
    factors = list(weights)
    if not samples or len(samples) != len(factors):
        raise ValueError("values and weights need equal nonzero length")
    if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in samples):
        raise ValueError("values must be finite numbers")
    if any(
        not isinstance(weight, (int, float))
        or not math.isfinite(weight)
        or weight < 0
        for weight in factors
    ):
        raise ValueError("weights must be finite and nonnegative")
    total = sum(factors)
    if total == 0:
        raise ValueError("total weight must be positive")
    return sum(value * weight for value, weight in zip(samples, factors)) / total
