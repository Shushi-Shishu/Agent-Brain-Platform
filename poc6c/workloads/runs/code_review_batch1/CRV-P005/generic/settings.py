"""Validation helpers for service settings."""

def normalize_label(value):
    return " ".join(value.strip().split())


def parse_retry_count(value):
    if not isinstance(value, int):
        raise TypeError("retry count must be an integer")
    if not 0 <= value <= 10:
        raise ValueError("retry count must be between zero and ten")
    return value


def bounded_timeout(seconds, minimum, maximum):
    if minimum > maximum:
        raise ValueError("minimum cannot exceed maximum")
    return min(max(seconds, minimum), maximum)
