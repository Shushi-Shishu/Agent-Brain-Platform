import unittest

from gate import SlidingGate


class SlidingGateTests(unittest.TestCase):
    def test_rejects_when_full(self):
        gate = SlidingGate(1, 10)
        self.assertTrue(gate.allow(2))
        self.assertFalse(gate.allow(3))


if __name__ == "__main__":
    unittest.main()
