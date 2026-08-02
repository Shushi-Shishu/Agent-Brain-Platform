"""Focused tests for the matched code-review pilot harness."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from workloads.code_review import (
    MAX_FINDINGS,
    OUTPUT_NAME,
    ReviewHarnessError,
    begin_arm_run,
    complete_arm_run,
    load_arm_boundary,
    load_code_review_fixtures,
    prepare_matched_pair,
    save_arm_boundary,
    summarize_code_review_reports,
    validate_findings,
)


def _perfect_findings(task):
    inventory = json.loads(
        (task.private.root / "defect_inventory.json").read_text(
            encoding="utf-8"
        )
    )
    return [
        {
            "file": item["file"],
            "line": item["line"],
            "category": item["category"],
            "severity": item["severity"],
            "explanation": (
                f"{item['title']}. {item['expected_finding']}"
            ),
        }
        for item in inventory["defects"]
    ]


class CodeReviewHarnessTests(unittest.TestCase):
    def test_instructions_share_contract_and_only_strategy_block_differs(self):
        root = Path(__file__).parent
        generic = (root / "GENERIC_CODE_REVIEW_AGENT.md").read_text(
            encoding="utf-8"
        )
        configured = (root / "CONFIGURED_CODE_REVIEW_AGENT.md").read_text(
            encoding="utf-8"
        )

        def normalize(value):
            start = value.index("<!-- experimental-arm-begin -->")
            end = value.index("<!-- experimental-arm-end -->")
            value = (
                value[:start]
                + "<!-- experimental-arm -->"
                + value[end + len("<!-- experimental-arm-end -->") :]
            )
            return value.replace("generic", "ARM").replace("configured", "ARM")

        self.assertEqual(normalize(generic), normalize(configured))
        self.assertIn("risk", configured)
        self.assertNotIn("risk", generic)
        self.assertIn(f"at most {MAX_FINDINGS}", generic)
        self.assertIn(f"at most {MAX_FINDINGS}", configured)

    def test_prepare_creates_fresh_byte_identical_public_copies(self):
        task = load_code_review_fixtures()[0]
        with tempfile.TemporaryDirectory() as temp:
            pair = prepare_matched_pair(task, Path(temp))
            self.assertEqual(
                pair.source_public_snapshot.sha256,
                pair.arm_start_snapshot.sha256,
            )
            self.assertEqual(
                (pair.generic_root / "access.py").read_bytes(),
                (pair.configured_root / "access.py").read_bytes(),
            )
            self.assertFalse((pair.generic_root / "private").exists())
            with self.assertRaisesRegex(ReviewHarnessError, "already exists"):
                prepare_matched_pair(task, Path(temp))

    def test_strict_findings_schema_rejects_budget_extra_path_and_duplicate(self):
        task = load_code_review_fixtures()[0]
        with tempfile.TemporaryDirectory() as temp:
            pair = prepare_matched_pair(task, Path(temp))
            valid = _perfect_findings(task)
            findings, errors = validate_findings(valid, pair.generic_root)
            self.assertEqual(findings, valid)
            self.assertEqual(errors, [])
            too_many = [dict(valid[0], line=1 + index) for index in range(7)]
            _, errors = validate_findings(too_many, pair.generic_root)
            self.assertTrue(any("budget" in item for item in errors))
            extra = dict(valid[0], confidence=0.9)
            _, errors = validate_findings([extra], pair.generic_root)
            self.assertTrue(any("exactly" in item for item in errors))
            escaped = dict(valid[0], file="../private/oracle.py")
            _, errors = validate_findings([escaped], pair.generic_root)
            self.assertTrue(any("safe relative" in item for item in errors))
            _, errors = validate_findings([valid[0], valid[0]], pair.generic_root)
            self.assertTrue(any("duplicates" in item for item in errors))

    def test_manual_boundary_round_trip_and_private_evaluation(self):
        task = load_code_review_fixtures()[0]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pair = prepare_matched_pair(task, root / "runs")
            boundary = begin_arm_run(pair, "generic")
            boundary_file = root / "boundaries" / "boundary.json"
            save_arm_boundary(boundary, boundary_file)
            restored = load_arm_boundary(boundary_file)
            findings = _perfect_findings(task)
            (restored.workspace / OUTPUT_NAME).write_text(
                json.dumps(findings), encoding="utf-8"
            )
            report = complete_arm_run(restored)
            self.assertTrue(report["valid_run"])
            self.assertTrue(report["findings"]["schema_valid"])
            self.assertEqual(
                report["evaluator"]["metrics"]["severity_weighted_recall"],
                1.0,
            )
            self.assertEqual(report["evaluator"]["metrics"]["precision"], 1.0)
            self.assertIsNone(report["provider"]["total_tokens"])
            self.assertIsNone(report["provider"]["cost_amount"])
            self.assertEqual(
                report["integrity"]["workspace_changes"],
                [f"created:{OUTPUT_NAME}"],
            )

    def test_invalid_json_skips_private_evaluator(self):
        task = load_code_review_fixtures()[0]
        with tempfile.TemporaryDirectory() as temp:
            pair = prepare_matched_pair(task, Path(temp))
            boundary = begin_arm_run(pair, "configured")
            (boundary.workspace / OUTPUT_NAME).write_text(
                "not json", encoding="utf-8"
            )
            report = complete_arm_run(boundary)
            self.assertFalse(report["valid_run"])
            self.assertFalse(report["findings"]["schema_valid"])
            self.assertFalse(report["evaluator"]["executed"])
            self.assertIn(
                "review findings schema invalid",
                report["integrity"]["violations"],
            )

    def test_canary_and_unauthorized_source_edit_invalidate_run(self):
        task = load_code_review_fixtures()[0]
        with tempfile.TemporaryDirectory() as temp:
            pair = prepare_matched_pair(task, Path(temp))
            boundary = begin_arm_run(pair, "generic")
            findings = _perfect_findings(task)
            findings[0]["explanation"] = (
                "Supported defect repair guidance: " + task.canaries[0].token
            )
            (boundary.workspace / OUTPUT_NAME).write_text(
                json.dumps(findings), encoding="utf-8"
            )
            source = next(boundary.workspace.glob("*.py"))
            source.write_text(
                source.read_text(encoding="utf-8") + "\n# edit\n",
                encoding="utf-8",
            )
            report = complete_arm_run(boundary)
            self.assertFalse(report["valid_run"])
            self.assertEqual(
                report["integrity"]["leakage_canary_ids"],
                [f"canary-{task.task_id}"],
            )
            self.assertTrue(report["integrity"]["unauthorized_edit_detected"])
            serialized = json.dumps(report)
            self.assertNotIn(task.canaries[0].token, serialized)

    def test_summary_reports_paired_recall_precision_and_false_positives(self):
        task = load_code_review_fixtures()[0]
        with tempfile.TemporaryDirectory() as temp:
            pair = prepare_matched_pair(task, Path(temp))
            reports = []
            for arm in ("generic", "configured"):
                boundary = begin_arm_run(pair, arm)
                findings = _perfect_findings(task)
                if arm == "generic":
                    findings.append(
                        {
                            "file": findings[0]["file"],
                            "line": 1,
                            "category": "style",
                            "severity": "low",
                            "explanation": (
                                "This intentionally unsupported item is a "
                                "measured false positive."
                            ),
                        }
                    )
                (boundary.workspace / OUTPUT_NAME).write_text(
                    json.dumps(findings), encoding="utf-8"
                )
                reports.append(complete_arm_run(boundary))
            summary = summarize_code_review_reports(reports)
            self.assertEqual(summary["valid_pair_count"], 1)
            self.assertEqual(
                summary["paired_task_deltas"][0][
                    "generic_minus_configured_false_positives"
                ],
                1,
            )
            self.assertGreater(
                summary["mean_paired_deltas"][
                    "configured_minus_generic_precision"
                ],
                0,
            )
            self.assertEqual(
                summary["mean_paired_deltas"][
                    "configured_minus_generic_severity_weighted_recall"
                ],
                0,
            )


if __name__ == "__main__":
    unittest.main()
