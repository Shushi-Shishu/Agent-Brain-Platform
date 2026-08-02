import unittest

from buckets import bucket_index


class ReferenceBucketTests(unittest.TestCase):
    def test_exact_boundaries_use_right_bucket(self):
        self.assertEqual(bucket_index(5, [0, 5, 10]), 2)

    def test_duplicate_boundaries_are_rejected(self):
        with self.assertRaises(ValueError):
            bucket_index(2, [1, 1, 3])

    def test_boolean_value_is_rejected(self):
        with self.assertRaises(TypeError):
            bucket_index(True, [0, 1])


if __name__ == "__main__":
    unittest.main()
