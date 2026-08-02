"""Evaluator checks for DEV-P001."""

import os
from pathlib import Path
import sys
import unittest


PUBLIC_ROOT = Path(
    os.environ.get("POC6C_PUBLIC_ROOT", Path(__file__).parents[1] / "public")
)
sys.path.insert(0, str(PUBLIC_ROOT))

from slugify import slugify


class SlugifyEvaluatorTests(unittest.TestCase):
    def test_separator_runs_collapse(self):
        self.assertEqual(slugify("A___B   C"), "a-b-c")

    def test_edges_are_removed(self):
        self.assertEqual(slugify("***Release 7***"), "release-7")

    def test_punctuation_only_is_empty(self):
        self.assertEqual(slugify(" ... "), "")


if __name__ == "__main__":
    unittest.main()
