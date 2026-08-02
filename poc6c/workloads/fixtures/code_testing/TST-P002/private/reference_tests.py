import unittest

from gate import SlidingGate


class ReferenceGateTests(unittest.TestCase):
    def test_event_expires_at_exact_window(self):
        gate = SlidingGate(1, 10)
        self.assertTrue(gate.allow(0))
        self.assertTrue(gate.allow(10))

    def test_rejection_still_advances_observed_time(self):
        gate = SlidingGate(1, 10)
        gate.allow(0)
        self.assertFalse(gate.allow(5))
        with self.assertRaises(ValueError):
            gate.allow(4)

    def test_rejected_event_does_not_consume_future_capacity(self):
        gate = SlidingGate(1, 10)
        gate.allow(0)
        self.assertFalse(gate.allow(9))
        self.assertTrue(gate.allow(10))


if __name__ == "__main__":
    unittest.main()
