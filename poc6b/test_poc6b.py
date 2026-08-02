"""Validation checks for the draft POC 6b review package."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from build_review_pack import build_cases


HERE = Path(__file__).resolve().parent


class GoldSetDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = build_cases()

    def test_case_counts_are_locked(self):
        cases = self.package["cases"]
        self.assertEqual(len(cases), 30)
        self.assertEqual(
            sum(case["expected_behavior"] == "answer" for case in cases),
            25,
        )
        self.assertEqual(
            sum(case["expected_behavior"] == "abstain" for case in cases),
            5,
        )

    def test_case_ids_are_unique(self):
        ids = [case["id"] for case in self.package["cases"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_answer_cases_have_candidates_and_hard_negatives(self):
        for case in self.package["cases"]:
            if case["expected_behavior"] != "answer":
                continue
            self.assertEqual(len(case["candidate_relevant"]), 3)
            self.assertEqual(
                len(case["hard_negatives_or_abstention_challenges"]),
                2,
            )

    def test_abstention_cases_have_only_challenge_results(self):
        for case in self.package["cases"]:
            if case["expected_behavior"] != "abstain":
                continue
            self.assertEqual(case["candidate_relevant"], [])
            self.assertEqual(
                len(case["hard_negatives_or_abstention_challenges"]),
                5,
            )

    def test_all_human_labels_start_unreviewed(self):
        for case in self.package["cases"]:
            self.assertEqual(
                case["status"],
                "draft_requires_human_review",
            )
            self.assertIsNone(case["review"]["question_is_realistic"])
            for candidate in (
                case["candidate_relevant"]
                + case["hard_negatives_or_abstention_challenges"]
            ):
                self.assertIsNone(candidate["human_relevance"])
                self.assertIsNone(candidate["human_evidence_quality"])

    def test_seed_file_is_valid_json(self):
        seed = json.loads(
            (HERE / "cases_seed.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(seed["cases"]), 30)

    def test_review_batch_size_is_ten(self):
        cases = self.package["cases"]
        batches = [cases[start : start + 10] for start in range(0, 30, 10)]
        self.assertEqual([len(batch) for batch in batches], [10, 10, 10])


if __name__ == "__main__":
    unittest.main()
