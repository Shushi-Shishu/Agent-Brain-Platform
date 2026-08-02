"""A small timestamped sliding-window admission gate."""

import math


class SlidingGate:
    def __init__(self, limit, window):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if not isinstance(window, (int, float)) or window <= 0:
            raise ValueError("window must be positive")
        self.limit = limit
        self.window = window
        self._events = []
        self._last_seen = None

    def allow(self, now):
        if not isinstance(now, (int, float)) or not math.isfinite(now):
            raise ValueError("now must be finite")
        if self._last_seen is not None and now < self._last_seen:
            raise ValueError("timestamps must not move backwards")
        self._last_seen = now
        cutoff = now - self.window
        self._events = [timestamp for timestamp in self._events if timestamp > cutoff]
        if len(self._events) >= self.limit:
            return False
        self._events.append(now)
        return True
