import unittest

from labels import parse_labels


class ParseLabelsCandidateTests(unittest.TestCase):
    def test_rejects_non_string_input_with_contract_message(self):
        with self.assertRaisesRegex(TypeError, r"^text must be a string$"):
            parse_labels(None)

    def test_empty_blank_and_indented_comment_lines_are_ignored(self):
        text = "\n   \n  # comment with = separator  \n\t# another\n"
        self.assertEqual(parse_labels(text), {})

    def test_trims_fields_splits_only_first_separator_and_allows_empty_value(self):
        text = "  spaced key = left=middle=right  \nempty =   "
        self.assertEqual(
            parse_labels(text),
            {"spaced key": "left=middle=right", "empty": ""},
        )

    def test_hash_inside_value_is_data_not_a_comment(self):
        self.assertEqual(parse_labels("color=blue # preferred"), {"color": "blue # preferred"})

    def test_missing_separator_reports_physical_line_number(self):
        text = "\n# ignored\nvalid=yes\nmalformed"
        with self.assertRaisesRegex(ValueError, r"^line 4 has no separator$"):
            parse_labels(text)

    def test_empty_key_reports_its_line_number(self):
        with self.assertRaisesRegex(ValueError, r"^line 2 has an empty key$"):
            parse_labels("valid=yes\n   = value")

    def test_duplicate_is_detected_after_key_trimming(self):
        text = " name = first\n# ignored\nname=second"
        with self.assertRaisesRegex(ValueError, r"^line 3 repeats 'name'$"):
            parse_labels(text)

    def test_keys_remain_case_sensitive(self):
        self.assertEqual(parse_labels("Name=upper\nname=lower"), {"Name": "upper", "name": "lower"})


if __name__ == "__main__":
    unittest.main()
