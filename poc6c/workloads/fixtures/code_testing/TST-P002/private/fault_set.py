"""Evaluator-only deterministic faults for TST-P002."""

FAULTS = [
    {
        "fault_id": "TST-P002-F01-expiry-boundary",
        "source": '''import math
class SlidingGate:
    def __init__(self, limit, window):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if not isinstance(window, (int, float)) or window <= 0:
            raise ValueError("window must be positive")
        self.limit, self.window, self._events, self._last_seen = limit, window, [], None
    def allow(self, now):
        if not isinstance(now, (int, float)) or not math.isfinite(now):
            raise ValueError("now must be finite")
        if self._last_seen is not None and now < self._last_seen:
            raise ValueError("timestamps must not move backwards")
        self._last_seen = now
        cutoff = now - self.window
        self._events = [t for t in self._events if t >= cutoff]
        if len(self._events) >= self.limit:
            return False
        self._events.append(now)
        return True
''',
    },
    {
        "fault_id": "TST-P002-F02-rejection-does-not-advance-time",
        "source": '''import math
class SlidingGate:
    def __init__(self, limit, window):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if not isinstance(window, (int, float)) or window <= 0:
            raise ValueError("window must be positive")
        self.limit, self.window, self._events, self._last_seen = limit, window, [], None
    def allow(self, now):
        if not isinstance(now, (int, float)) or not math.isfinite(now):
            raise ValueError("now must be finite")
        if self._last_seen is not None and now < self._last_seen:
            raise ValueError("timestamps must not move backwards")
        cutoff = now - self.window
        self._events = [t for t in self._events if t > cutoff]
        if len(self._events) >= self.limit:
            return False
        self._last_seen = now
        self._events.append(now)
        return True
''',
    },
    {
        "fault_id": "TST-P002-F03-rejected-event-is-recorded",
        "source": '''import math
class SlidingGate:
    def __init__(self, limit, window):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if not isinstance(window, (int, float)) or window <= 0:
            raise ValueError("window must be positive")
        self.limit, self.window, self._events, self._last_seen = limit, window, [], None
    def allow(self, now):
        if not isinstance(now, (int, float)) or not math.isfinite(now):
            raise ValueError("now must be finite")
        if self._last_seen is not None and now < self._last_seen:
            raise ValueError("timestamps must not move backwards")
        self._last_seen = now
        cutoff = now - self.window
        self._events = [t for t in self._events if t > cutoff]
        if len(self._events) >= self.limit:
            self._events.append(now)
            return False
        self._events.append(now)
        return True
''',
    },
]
