"""Evaluator checks for DEV-P003."""

import os
from pathlib import Path
import sys
import unittest


PUBLIC_ROOT = Path(
    os.environ.get("POC6C_PUBLIC_ROOT", Path(__file__).parents[1] / "public")
)
sys.path.insert(0, str(PUBLIC_ROOT))

from windows import merge_windows


class WindowEvaluatorTests(unittest.TestCase):
    def test_touching_windows_remain_separate(self):
        self.assertEqual(merge_windows([(1, 3), (3, 5)]), [(1, 3), (3, 5)])

    def test_real_overlap_is_merged_after_sorting(self):
        source = [(8, 10), (2, 6), (4, 9)]
        self.assertEqual(merge_windows(source), [(2, 10)])
        self.assertEqual(source, [(8, 10), (2, 6), (4, 9)])

    def test_empty_window_is_rejected(self):
        with self.assertRaises(ValueError):
            merge_windows([(4, 4)])


if __name__ == "__main__":
    unittest.main()
