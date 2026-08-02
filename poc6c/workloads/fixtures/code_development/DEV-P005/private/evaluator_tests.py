"""Evaluator checks for DEV-P005."""

import os
from pathlib import Path
import sys
import unittest


PUBLIC_ROOT = Path(
    os.environ.get("POC6C_PUBLIC_ROOT", Path(__file__).parents[1] / "public")
)
sys.path.insert(0, str(PUBLIC_ROOT))

from retry import retry_delays


class RetryEvaluatorTests(unittest.TestCase):
    def test_delays_are_capped(self):
        self.assertEqual(retry_delays(6, 2, 9), [2, 4, 8, 9, 9, 9])

    def test_zero_attempts_is_empty(self):
        self.assertEqual(retry_delays(0, 3, 12), [])

    def test_invalid_bounds_are_rejected(self):
        with self.assertRaises(ValueError):
            retry_delays(2, 0, 5)
        with self.assertRaises(ValueError):
            retry_delays(2, 8, 7)


if __name__ == "__main__":
    unittest.main()
