import unittest

from labels import parse_labels


class ParseLabelsCandidateTests(unittest.TestCase):
    def test_non_string_inputs_are_rejected_with_contract_message(self):
        for value in (None, b"a=1", 12, ["a=1"]):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    TypeError, r"^text must be a string$"
                ):
                    parse_labels(value)

    def test_empty_blank_and_comment_lines_are_ignored(self):
        text = "\n  \t  \n# first comment\n   # indented comment   \n\r\n"
        self.assertEqual(parse_labels(text), {})

    def test_surrounding_whitespace_is_trimmed_from_fields(self):
        text = "  animal name \t = \t red fox  \nplain=value"
        self.assertEqual(
            parse_labels(text),
            {"animal name": "red fox", "plain": "value"},
        )

    def test_only_first_separator_is_structural_and_empty_value_is_valid(self):
        self.assertEqual(
            parse_labels("equation = left=middle=right\nempty =   "),
            {"equation": "left=middle=right", "empty": ""},
        )

    def test_splitlines_line_endings_are_supported(self):
        self.assertEqual(
            parse_labels("one=1\r\ntwo=2\rthree=3\vfour=4"),
            {"one": "1", "two": "2", "three": "3", "four": "4"},
        )

    def test_missing_separator_reports_physical_line_number(self):
        text = "# ignored\n\nfirst=ok\n   malformed line   \nlast=unreached"
        with self.assertRaisesRegex(
            ValueError, r"^line 4 has no separator$"
        ):
            parse_labels(text)

    def test_empty_key_reports_its_line_number(self):
        with self.assertRaisesRegex(ValueError, r"^line 2 has an empty key$"):
            parse_labels("valid=yes\n   = some value")

    def test_duplicate_keys_are_detected_after_trimming(self):
        with self.assertRaisesRegex(
            ValueError, r"^line 3 repeats 'color'$"
        ):
            parse_labels("color=blue\n# ignored\n  color  = red")


if __name__ == "__main__":
    unittest.main()
