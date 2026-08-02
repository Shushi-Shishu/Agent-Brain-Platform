import unittest

from buckets import bucket_index


class BucketIndexCandidateTests(unittest.TestCase):
    def test_empty_boundaries_has_only_bucket_zero(self):
        self.assertEqual(bucket_index(-12.5, []), 0)
        self.assertEqual(bucket_index(99, ()), 0)

    def test_values_equal_to_boundaries_enter_the_next_bucket(self):
        boundaries = [-3, 0, 4.5]
        self.assertEqual(bucket_index(-3, boundaries), 1)
        self.assertEqual(bucket_index(0.0, boundaries), 2)
        self.assertEqual(bucket_index(4.5, boundaries), 3)

    def test_values_outside_all_boundaries(self):
        boundaries = [-10, -2, 6]
        self.assertEqual(bucket_index(-10.01, boundaries), 0)
        self.assertEqual(bucket_index(100, boundaries), 3)

    def test_boundaries_may_be_a_one_pass_iterable(self):
        boundaries = (point for point in [-5, 2.5, 8])
        self.assertEqual(bucket_index(2.5, boundaries), 2)

    def test_non_numeric_and_boolean_values_are_rejected(self):
        for value in (True, False, "7", None, object()):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    bucket_index(value, [0, 5])

    def test_non_finite_values_are_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    bucket_index(value, [0, 5])

    def test_invalid_boundary_elements_are_rejected(self):
        invalid_points = (True, "5", None, float("nan"), float("inf"), float("-inf"))
        for point in invalid_points:
            with self.subTest(point=point):
                with self.assertRaises(TypeError):
                    bucket_index(3, [0, point, 10])

    def test_boundaries_must_be_strictly_increasing(self):
        for boundaries in ([0, 5, 5, 10], [0, 7, 3, 10]):
            with self.subTest(boundaries=boundaries):
                with self.assertRaises(ValueError):
                    bucket_index(4, boundaries)


if __name__ == "__main__":
    unittest.main()
