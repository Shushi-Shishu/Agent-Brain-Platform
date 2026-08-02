import unittest

from labels import parse_labels


class ParseLabelsTests(unittest.TestCase):
    def test_parses_two_fields(self):
        self.assertEqual(parse_labels("a=1\nb=2"), {"a": "1", "b": "2"})


if __name__ == "__main__":
    unittest.main()
