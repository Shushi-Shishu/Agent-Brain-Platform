"""Tests for blinded score validation and diagnostic summaries."""

from __future__ import annotations

import copy
import unittest

from evaluation import (
    deblind_score_rows,
    evaluator_agreement,
    pilot_descriptive_summary,
    validate_blind_scores,
)


def blind_cases():
    return [
        {
            "case_id": "Q001",
            "question": "Question",
            "answers": [
                {"blind_output_id": "B-AAA"},
                {"blind_output_id": "B-BBB"},
            ],
        }
    ]


def scores():
    components = {
        "claim_support": 25,
        "question_coverage": 15,
        "gap_handling": 12,
        "unsupported_claim_avoidance": 13,
        "practical_usefulness": 8,
        "citation_precision": 9,
        "critical_failure": False,
        "notes": "Diagnostic score.",
    }
    return {
        "schema_version": 1,
        "stage": "instrumentation_only",
        "cases": [
            {
                "case_id": "Q001",
                "scores": [
                    {"blind_output_id": "B-AAA", **components},
                    {"blind_output_id": "B-BBB", **components},
                ],
            }
        ],
    }


class EvaluationTests(unittest.TestCase):
    def test_valid_scores(self):
        self.assertEqual(validate_blind_scores(scores(), blind_cases()), [])

    def test_out_of_range_component_is_rejected(self):
        changed = scores()
        changed["cases"][0]["scores"][0]["claim_support"] = 31
        self.assertIn(
            "Q001: claim_support must be integer 0..30",
            validate_blind_scores(changed, blind_cases()),
        )

    def test_wrong_blind_ids_are_rejected(self):
        changed = copy.deepcopy(scores())
        changed["cases"][0]["scores"][0]["blind_output_id"] = "B-UNKNOWN"
        self.assertIn(
            "Q001: blind output IDs do not match",
            validate_blind_scores(changed, blind_cases()),
        )

    def test_deblind_and_summary_are_descriptive(self):
        rows = deblind_score_rows(
            scores(),
            {"B-AAA": "generic", "B-BBB": "configured"},
        )
        summary = pilot_descriptive_summary(rows)
        self.assertEqual(summary["task_count"], 1)
        self.assertEqual(
            summary["status"],
            "instrumentation_only_no_efficacy_claim",
        )
        self.assertEqual(
            summary["arm_descriptives"]["generic"]["mean_quality"],
            82,
        )
        self.assertEqual(
            summary["paired_descriptives"][
                "mean_quality_delta_configured_minus_generic"
            ],
            0,
        )
        self.assertEqual(summary["paired_descriptives"]["ties"], 1)

    def test_missing_mapping_fails_closed(self):
        with self.assertRaises(ValueError):
            deblind_score_rows(scores(), {"B-AAA": "generic"})

    def test_evaluator_agreement_detects_score_and_preference_differences(self):
        first = scores()
        second = scores()
        second["cases"][0]["scores"][0]["claim_support"] -= 5
        report = evaluator_agreement(first, second)
        self.assertEqual(report["blind_output_count"], 2)
        self.assertEqual(report["mean_absolute_total_score_difference"], 2.5)
        self.assertEqual(report["max_absolute_total_score_difference"], 5)
        self.assertEqual(report["critical_failure_agreement_rate"], 1)
        self.assertEqual(report["pair_preference_agreement_rate"], 0)


if __name__ == "__main__":
    unittest.main()
