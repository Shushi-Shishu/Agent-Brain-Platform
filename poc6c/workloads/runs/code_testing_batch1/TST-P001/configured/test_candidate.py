import unittest

from buckets import bucket_index


class BucketIndexCandidateTests(unittest.TestCase):
    def test_each_bucket_and_exact_boundary_inclusivity(self):
        boundaries = [0, 5, 10]
        cases = [
            (-1, 0),
            (0, 1),
            (4.5, 1),
            (5, 2),
            (9.5, 2),
            (10, 3),
            (11, 3),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(bucket_index(value, boundaries), expected)

    def test_empty_and_single_boundary(self):
        self.assertEqual(bucket_index(3, []), 0)
        self.assertEqual(bucket_index(-2, [-2]), 1)

    def test_generator_boundaries_are_supported(self):
        boundaries = (point for point in (-10, -1, 2.5))
        self.assertEqual(bucket_index(0, boundaries), 2)

    def test_rejects_non_numeric_values(self):
        for value in (True, False, "5", None, 3 + 0j):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    bucket_index(value, [0, 10])

    def test_rejects_non_finite_values(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    bucket_index(value, [0, 10])

    def test_rejects_invalid_boundary_members(self):
        for point in (True, "5", None, float("nan"), float("inf"), float("-inf")):
            with self.subTest(point=point):
                with self.assertRaises(TypeError):
                    bucket_index(3, [0, point, 10])

    def test_rejects_duplicate_boundaries(self):
        with self.assertRaises(ValueError):
            bucket_index(3, [0, 5, 5, 10])

    def test_rejects_descending_boundaries(self):
        with self.assertRaises(ValueError):
            bucket_index(3, [0, 10, 5])


if __name__ == "__main__":
    unittest.main()
