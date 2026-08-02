"""Evaluator checks for DEV-P002."""

import os
from pathlib import Path
import sys
import unittest


PUBLIC_ROOT = Path(
    os.environ.get("POC6C_PUBLIC_ROOT", Path(__file__).parents[1] / "public")
)
sys.path.insert(0, str(PUBLIC_ROOT))

from invoice import invoice_total


class InvoiceEvaluatorTests(unittest.TestCase):
    def test_discounts_are_line_specific(self):
        lines = [
            {"unit_price": 100.0, "quantity": 1, "discount_rate": 0.50},
            {"unit_price": 10.0, "quantity": 2, "discount_rate": 0.00},
        ]
        self.assertEqual(invoice_total(lines, 0.10), 77.00)

    def test_empty_invoice_is_zero(self):
        self.assertEqual(invoice_total([], 0.20), 0.00)

    def test_negative_quantity_is_rejected(self):
        lines = [{"unit_price": 5.0, "quantity": -1, "discount_rate": 0.0}]
        with self.assertRaises(ValueError):
            invoice_total(lines, 0.0)


if __name__ == "__main__":
    unittest.main()
