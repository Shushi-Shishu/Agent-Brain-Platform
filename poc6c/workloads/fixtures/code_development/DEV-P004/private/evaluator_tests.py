"""Evaluator checks for DEV-P004."""

import os
from pathlib import Path
import sys
import unittest


PUBLIC_ROOT = Path(
    os.environ.get("POC6C_PUBLIC_ROOT", Path(__file__).parents[1] / "public")
)
sys.path.insert(0, str(PUBLIC_ROOT))

from sales import summarize_sales


class SalesEvaluatorTests(unittest.TestCase):
    def test_quoted_region_with_comma(self):
        text = 'region,amount\n"North, East",12.50\n"North, East",7.50\n'
        self.assertEqual(summarize_sales(text), {"North, East": 20.0})

    def test_blank_rows_are_ignored(self):
        text = "region,amount\n\nWest,3\n \nWest,4\n"
        self.assertEqual(summarize_sales(text), {"West": 7.0})

    def test_non_numeric_amount_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize_sales("region,amount\nSouth,many\n")


if __name__ == "__main__":
    unittest.main()
