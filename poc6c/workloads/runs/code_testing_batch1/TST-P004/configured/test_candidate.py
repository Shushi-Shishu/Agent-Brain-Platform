import math
import unittest

from weighted import weighted_average


class WeightedAverageCandidateTests(unittest.TestCase):
    def test_asymmetric_weights_zero_weight_and_negative_sample(self):
        self.assertEqual(weighted_average([10, -4, 100], [0, 3, 1]), 22)

    def test_fractional_values_and_weights(self):
        self.assertEqual(
            weighted_average([-2.5, 4.0, 10.5], [0.5, 1.5, 2.0]),
            6.4375,
        )

    def test_accepts_one_shot_iterables(self):
        values = (value for value in [4, 10, -2])
        weights = (weight for weight in [1, 2, 3])
        self.assertEqual(weighted_average(values, weights), 3)

    def test_very_small_positive_weights_are_not_treated_as_zero(self):
        self.assertAlmostEqual(
            weighted_average([2.0, 6.0], [1e-200, 3e-200]),
            5.0,
        )

    def test_rejects_empty_or_unequal_lengths(self):
        cases = [([], []), ([1], []), ([], [1]), ([1, 2], [1])]
        for values, weights in cases:
            with self.subTest(values=values, weights=weights):
                with self.assertRaises(ValueError):
                    weighted_average(values, weights)

    def test_rejects_non_numeric_or_nonfinite_values(self):
        invalid_values = ["3", None, 1 + 2j, math.inf, -math.inf, math.nan]
        for invalid in invalid_values:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    weighted_average([1, invalid], [1, 1])

    def test_rejects_negative_non_numeric_or_nonfinite_weights(self):
        invalid_weights = [-1, -1e-300, "1", None, math.inf, -math.inf, math.nan]
        for invalid in invalid_weights:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    weighted_average([1, 2], [1, invalid])

    def test_rejects_zero_total_weight(self):
        with self.assertRaises(ValueError):
            weighted_average([1, 2, 3], [0, 0.0, 0])


if __name__ == "__main__":
    unittest.main()
