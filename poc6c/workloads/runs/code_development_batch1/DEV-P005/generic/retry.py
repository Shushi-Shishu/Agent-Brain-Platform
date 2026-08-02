"""Deterministic retry schedule calculation."""


def retry_delays(attempts, base_seconds, cap_seconds):
    """Return capped exponential delays."""

    if attempts < 0:
        raise ValueError("attempts cannot be negative")
    if base_seconds <= 0 or cap_seconds < base_seconds:
        raise ValueError("invalid delay bounds")

    delays = []
    delay = base_seconds
    for _ in range(attempts):
        delays.append(delay)
        delay = min(delay * 2, cap_seconds)
    return delays
