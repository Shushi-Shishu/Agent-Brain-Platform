"""Data-integrity and mechanics checks for POC 6a."""

from __future__ import annotations

import unittest

import numpy as np

from experiment import (
    ARM_NAMES,
    BUDGET,
    EXPECTED_ELIGIBLE_QUERIES,
    EXPECTED_MANIFEST_SHA256,
    K,
    POLICY_CLASSES,
    QueryCase,
    arm_for_path,
    build_query_cases,
    load_documents,
    manifest_sha256,
    parse_tags,
    query_tokens,
    run_policy,
    split_frontmatter,
)


class HistoricalTransferDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents, cls.integrity = load_documents()
        cls.cases = build_query_cases(cls.documents)

    def test_locked_manifest_snapshot_matches(self):
        self.assertEqual(manifest_sha256(), EXPECTED_MANIFEST_SHA256)

    def test_twelve_arms_and_other_mapping(self):
        self.assertEqual(len(ARM_NAMES), K)
        self.assertEqual(arm_for_path("Mathematics/example.md"), "Mathematics")
        self.assertEqual(arm_for_path("Geopolitics/example.md"), "Other")

    def test_frontmatter_tags_are_not_indexed(self):
        content = "---\ntags: [hidden-label, other]\ntitle: Test\n---\nVisible body"
        frontmatter, body = split_frontmatter(content)
        self.assertEqual(parse_tags(frontmatter), {"hidden-label", "other"})
        self.assertEqual(body, "Visible body")
        self.assertNotIn("hidden-label", body)
        self.assertTrue(self.integrity["all_indexed_frontmatter_removed"])

    def test_query_tokens_normalize_tag_punctuation(self):
        self.assertEqual(
            query_tokens("model-context_protocol"),
            ("model", "context", "protocol"),
        )

    def test_locked_query_and_split_counts(self):
        self.assertEqual(len(self.cases), EXPECTED_ELIGIBLE_QUERIES)
        counts = {
            (split, stratum): sum(
                case.split == split and case.stratum == stratum
                for case in self.cases
            )
            for split in ("selection", "confirmation")
            for stratum in ("concentrated", "diffuse")
        }
        self.assertEqual(counts[("selection", "concentrated")], 37)
        self.assertEqual(counts[("selection", "diffuse")], 58)
        self.assertEqual(counts[("confirmation", "concentrated")], 72)
        self.assertEqual(counts[("confirmation", "diffuse")], 73)

    def test_every_candidate_policy_runs_on_shared_outcomes(self):
        outcomes = np.zeros((K, BUDGET), dtype=np.int8)
        outcomes[:, 0] = 1
        scores = [
            run_policy(policy, outcomes, seed=index + 1)
            for index, policy in enumerate(POLICY_CLASSES)
        ]
        self.assertEqual(len(scores), len(POLICY_CLASSES))
        self.assertTrue(all(0 <= score <= BUDGET for score in scores))

    def test_query_case_contract_is_explicit(self):
        case = QueryCase(
            tag="test-tag",
            query_tokens=("test", "tag"),
            stratum="diffuse",
            split="confirmation",
            relevant_count=5,
            relevant_arm_count=2,
            maximum_arm_share=0.6,
        )
        self.assertEqual(case.query_tokens, ("test", "tag"))


if __name__ == "__main__":
    unittest.main()
