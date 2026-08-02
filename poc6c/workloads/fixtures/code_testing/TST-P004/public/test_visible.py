import unittest

from weighted import weighted_average


class WeightedAverageTests(unittest.TestCase):
    def test_balanced_integer_inputs(self):
        self.assertEqual(weighted_average([2, 4], [1, 1]), 3)


if __name__ == "__main__":
    unittest.main()
