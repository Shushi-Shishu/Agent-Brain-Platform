import math
import unittest

from gate import SlidingGate


class SlidingGateCandidateTests(unittest.TestCase):
    def test_allows_up_to_limit_then_rejects(self):
        gate = SlidingGate(3, 10)
        self.assertTrue(gate.allow(1))
        self.assertTrue(gate.allow(2))
        self.assertTrue(gate.allow(3))
        self.assertFalse(gate.allow(4))

    def test_equal_timestamps_are_allowed_up_to_capacity(self):
        gate = SlidingGate(2, 5)
        self.assertTrue(gate.allow(7.5))
        self.assertTrue(gate.allow(7.5))
        self.assertFalse(gate.allow(7.5))

    def test_event_expires_at_exact_window_boundary(self):
        gate = SlidingGate(1, 10)
        self.assertTrue(gate.allow(2))
        self.assertFalse(gate.allow(11.999))
        self.assertTrue(gate.allow(12))

    def test_only_expired_events_are_removed(self):
        gate = SlidingGate(2, 10)
        self.assertTrue(gate.allow(0))
        self.assertTrue(gate.allow(4))
        self.assertTrue(gate.allow(10))
        self.assertFalse(gate.allow(13))
        self.assertTrue(gate.allow(14))

    def test_rejected_attempts_do_not_consume_capacity(self):
        gate = SlidingGate(1, 5)
        self.assertTrue(gate.allow(0))
        self.assertFalse(gate.allow(1))
        self.assertFalse(gate.allow(4))
        self.assertTrue(gate.allow(5))

    def test_backwards_timestamp_is_rejected_without_poisoning_gate(self):
        gate = SlidingGate(2, 10)
        self.assertTrue(gate.allow(10))
        with self.assertRaises(ValueError):
            gate.allow(9)
        self.assertTrue(gate.allow(10))

    def test_invalid_constructor_arguments_are_rejected(self):
        for limit, window in ((0, 1), (-1, 1), (1.5, 1), (True, 1), (1, 0), (1, -1), (1, "5")):
            with self.subTest(limit=limit, window=window):
                with self.assertRaises(ValueError):
                    SlidingGate(limit, window)

    def test_nonfinite_and_nonnumeric_timestamps_are_rejected(self):
        gate = SlidingGate(1, 1)
        for now in (math.nan, math.inf, -math.inf, "0", None):
            with self.subTest(now=now):
                with self.assertRaises(ValueError):
                    gate.allow(now)


if __name__ == "__main__":
    unittest.main()
