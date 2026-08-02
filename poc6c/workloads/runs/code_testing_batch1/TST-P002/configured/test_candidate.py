import math
import unittest

from gate import SlidingGate


class SlidingGateCandidateTests(unittest.TestCase):
    def test_limit_must_be_a_positive_non_boolean_integer(self):
        for bad_limit in (0, -1, True, 1.0, "2", None):
            with self.subTest(limit=bad_limit):
                with self.assertRaises(ValueError):
                    SlidingGate(bad_limit, 10)

    def test_window_must_be_positive_and_numeric(self):
        for bad_window in (0, -0.25, "10", None):
            with self.subTest(window=bad_window):
                with self.assertRaises(ValueError):
                    SlidingGate(2, bad_window)

    def test_now_must_be_numeric_and_finite_without_corrupting_state(self):
        gate = SlidingGate(1, 2)
        self.assertTrue(gate.allow(5))

        for bad_now in ("6", None, math.nan, math.inf, -math.inf):
            with self.subTest(now=bad_now):
                with self.assertRaises(ValueError):
                    gate.allow(bad_now)

        self.assertTrue(gate.allow(7))

    def test_admits_exactly_the_configured_limit(self):
        gate = SlidingGate(3, 10)

        self.assertEqual(
            [gate.allow(timestamp) for timestamp in (0, 1, 2, 3)],
            [True, True, True, False],
        )

    def test_rejected_attempts_do_not_refresh_the_window(self):
        gate = SlidingGate(1, 10)

        self.assertTrue(gate.allow(0))
        self.assertFalse(gate.allow(1))
        self.assertFalse(gate.allow(9.999))
        self.assertTrue(gate.allow(10))

    def test_event_expires_at_the_exact_fractional_cutoff(self):
        gate = SlidingGate(1, 2.5)
        self.assertTrue(gate.allow(10))
        self.assertTrue(gate.allow(12.5))

        just_inside = SlidingGate(1, 2.5)
        self.assertTrue(just_inside.allow(10))
        self.assertFalse(just_inside.allow(12.499999))

    def test_window_slides_per_event_instead_of_resetting_as_a_block(self):
        gate = SlidingGate(2, 10)

        self.assertTrue(gate.allow(0))
        self.assertTrue(gate.allow(9))
        self.assertTrue(gate.allow(10))
        self.assertFalse(gate.allow(18))
        self.assertTrue(gate.allow(19))

    def test_equal_times_count_separately_and_backwards_time_is_rejected(self):
        gate = SlidingGate(2, 10)

        self.assertTrue(gate.allow(5))
        self.assertTrue(gate.allow(5))
        self.assertFalse(gate.allow(5))
        with self.assertRaises(ValueError):
            gate.allow(4.999)
        self.assertTrue(gate.allow(15))


if __name__ == "__main__":
    unittest.main()
