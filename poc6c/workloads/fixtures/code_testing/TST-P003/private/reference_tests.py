import unittest

from labels import parse_labels


class ReferenceLabelTests(unittest.TestCase):
    def test_value_may_contain_separator(self):
        self.assertEqual(parse_labels("route=a=b"), {"route": "a=b"})

    def test_comment_and_blank_lines_are_ignored(self):
        self.assertEqual(parse_labels("# note\n\n active = yes "), {"active": "yes"})

    def test_duplicate_key_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_labels("mode=one\nmode=two")


if __name__ == "__main__":
    unittest.main()
