import unittest

from buckets import bucket_index


class BucketIndexTests(unittest.TestCase):
    def test_value_between_two_boundaries(self):
        self.assertEqual(bucket_index(7, [0, 5, 10]), 2)


if __name__ == "__main__":
    unittest.main()
