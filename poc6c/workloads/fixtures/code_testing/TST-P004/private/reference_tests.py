import unittest

from weighted import weighted_average


class ReferenceWeightedTests(unittest.TestCase):
    def test_lengths_must_match(self):
        with self.assertRaises(ValueError):
            weighted_average([1, 2], [1])

    def test_negative_weight_is_rejected(self):
        with self.assertRaises(ValueError):
            weighted_average([1, 2], [1, -1])

    def test_result_is_not_rounded(self):
        self.assertAlmostEqual(weighted_average([0, 1], [2, 1]), 1 / 3)


if __name__ == "__main__":
    unittest.main()
