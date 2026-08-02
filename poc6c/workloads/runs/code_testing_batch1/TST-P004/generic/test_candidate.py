import math
import unittest

from weighted import weighted_average


class WeightedAverageCandidateTests(unittest.TestCase):
    def test_unequal_weights_and_zero_weight_observations(self):
        self.assertEqual(weighted_average([100, 3, -100], [0, 2, 0]), 3)
        self.assertEqual(weighted_average([-10, 2, 8], [1, 2, 1]), 0.5)

    def test_fractional_weights_are_normalized_by_their_total(self):
        self.assertEqual(weighted_average([2, 10, 20], [0.5, 0.25, 0.25]), 8.5)

    def test_scaling_all_weights_does_not_change_the_result(self):
        values = [-4.5, 3.0, 12.0]
        expected = weighted_average(values, [1.0, 2.0, 3.0])
        self.assertAlmostEqual(weighted_average(values, [10.0, 20.0, 30.0]), expected)

    def test_accepts_one_shot_iterables(self):
        values = (value for value in [1, 7, 10])
        weights = (weight for weight in [2, 1, 3])
        self.assertEqual(weighted_average(values, weights), 6.5)

    def test_rejects_empty_and_differently_sized_inputs(self):
        for values, weights in (([], []), ([1], []), ([1], [1, 2])):
            with self.subTest(values=values, weights=weights):
                with self.assertRaises(ValueError):
                    weighted_average(values, weights)

    def test_rejects_non_numeric_or_nonfinite_values(self):
        for invalid in ("4", None, math.inf, -math.inf, math.nan):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    weighted_average([1, invalid], [1, 1])

    def test_rejects_negative_non_numeric_or_nonfinite_weights(self):
        for invalid in (-0.01, "1", None, math.inf, -math.inf, math.nan):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    weighted_average([1, 2], [1, invalid])

    def test_rejects_an_all_zero_weight_set(self):
        with self.assertRaises(ValueError):
            weighted_average([1, 2, 3], [0, 0.0, 0])


if __name__ == "__main__":
    unittest.main()
