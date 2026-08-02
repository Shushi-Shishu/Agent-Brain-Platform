"""Focused integrity and report tests for the code-testing harness."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from workloads.code_testing_harness import (
    BOUNDARY_SCHEMA,
    INSTRUCTION_PATHS,
    TestingHarnessError,
    begin_arm_run,
    complete_arm_run,
    load_arm_boundary,
    load_code_testing_fixtures,
    prepare_matched_pair,
    save_arm_boundary,
    summarize_code_testing_reports,
)


class CodeTestingHarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="poc6c-tst-harness-")
        self.root = Path(self.temp.name)
        self.task = load_code_testing_fixtures()[0]

    def tearDown(self):
        self.temp.cleanup()

    def _pair(self):
        return prepare_matched_pair(
            self.task,
            self.root / "runs",
            matched_conditions={
                "model_id": "same-test-model",
                "max_candidate_tests": 8,
            },
        )

    def _reference_candidate(self, workspace: Path):
        shutil.copy2(
            self.task.private.root / "reference_tests.py",
            workspace / "test_candidate.py",
        )

    def test_prepare_creates_fresh_byte_identical_arms(self):
        pair = self._pair()
        self.assertEqual(
            pair.source_public_snapshot.sha256,
            pair.arm_start_snapshot.sha256,
        )
        self.assertEqual(
            pair.arm_start_snapshot.sha256,
            __import__(
                "workloads.fixture_integrity",
                fromlist=["snapshot_package"],
            ).snapshot_package(pair.configured_root).sha256,
        )
        with self.assertRaises(TestingHarnessError):
            prepare_matched_pair(self.task, self.root / "runs")

    def test_boundary_round_trip_and_reference_suite_scores(self):
        pair = self._pair()
        boundary = begin_arm_run(pair, "generic")
        path = self.root / "boundaries" / "generic.json"
        save_arm_boundary(boundary, path)
        self.assertEqual(
            json.loads(path.read_text(encoding="utf-8"))["schema"],
            BOUNDARY_SCHEMA,
        )
        loaded = load_arm_boundary(path)
        self._reference_candidate(loaded.workspace)
        report = complete_arm_run(loaded, agent_result="done")
        self.assertTrue(report["valid_run"], report)
        self.assertTrue(report["evaluator"]["executed"])
        metrics = report["evaluator"]["metrics"]
        self.assertEqual(metrics["fault_exposure_rate"], 1.0)
        self.assertEqual(metrics["distinct_faults_exposed"], 3)
        self.assertTrue(metrics["valid"])
        self.assertTrue(metrics["stable"])
        self.assertEqual(metrics["implementation_coupling_findings"], [])
        self.assertTrue(metrics["runtime_within_budget"])
        self.assertIsNone(report["provider"]["total_tokens"])
        self.assertIsNone(report["provider"]["cost_amount"])

    def test_only_candidate_test_may_be_created(self):
        pair = self._pair()
        boundary = begin_arm_run(pair, "configured")
        self._reference_candidate(boundary.workspace)
        (boundary.workspace / "notes.txt").write_text("extra", encoding="utf-8")
        report = complete_arm_run(boundary)
        self.assertFalse(report["valid_run"])
        self.assertTrue(report["integrity"]["unauthorized_edit_detected"])
        self.assertIn(
            "agent changed files other than the candidate test output",
            report["integrity"]["violations"],
        )
        self.assertTrue(report["evaluator"]["executed"])

    def test_interpreter_cache_files_do_not_invalidate_a_valid_run(self):
        pair = self._pair()
        boundary = begin_arm_run(pair, "generic")
        self._reference_candidate(boundary.workspace)
        cache = boundary.workspace / "__pycache__"
        cache.mkdir(exist_ok=True)
        (cache / "module.cpython-312.pyc").write_bytes(b"cache")
        report = complete_arm_run(boundary)
        self.assertTrue(report["valid_run"], report)
        self.assertFalse(report["integrity"]["unauthorized_edit_detected"])

    def test_canary_leak_invalidates_and_is_redacted(self):
        pair = self._pair()
        boundary = begin_arm_run(pair, "generic")
        token = self.task.canaries[0].token
        (boundary.workspace / "test_candidate.py").write_text(
            f"# {token}\n", encoding="utf-8"
        )
        report = complete_arm_run(boundary, agent_result=token)
        self.assertFalse(report["valid_run"])
        self.assertEqual(
            report["integrity"]["leakage_canary_ids"],
            [f"canary-{self.task.task_id}"],
        )
        self.assertNotIn(token, json.dumps(report))

    def test_missing_candidate_skips_private_scorer(self):
        report = complete_arm_run(begin_arm_run(self._pair(), "generic"))
        self.assertFalse(report["valid_run"])
        self.assertFalse(report["evaluator"]["executed"])
        self.assertEqual(
            report["evaluator"]["skip_reason"],
            "candidate test output is missing",
        )

    def test_private_change_prevents_scorer_execution(self):
        fixture_copy = self.root / "fixture-copy"
        shutil.copytree(
            Path(__file__).parent / "fixtures" / "code_testing",
            fixture_copy,
        )
        copied_task = load_code_testing_fixtures(fixture_copy)[0]
        pair = prepare_matched_pair(copied_task, self.root / "copied-runs")
        boundary = begin_arm_run(pair, "generic")
        shutil.copy2(
            copied_task.private.root / "reference_tests.py",
            boundary.workspace / "test_candidate.py",
        )
        canary_path = copied_task.private.root / "canary.txt"
        canary_path.write_text(
            canary_path.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
        report = complete_arm_run(boundary)
        self.assertFalse(report["valid_run"])
        self.assertFalse(report["evaluator"]["executed"])
        self.assertIn(
            "private scorer package changed during agent run",
            report["integrity"]["violations"],
        )

    def test_summary_preserves_pairing_and_null_usage(self):
        pair = self._pair()
        reports = []
        for arm in ("generic", "configured"):
            boundary = begin_arm_run(pair, arm)
            self._reference_candidate(boundary.workspace)
            reports.append(complete_arm_run(boundary))
        summary = summarize_code_testing_reports(reports)
        self.assertEqual(
            summary["status"], "instrumentation_only_no_efficacy_claim"
        )
        self.assertEqual(summary["valid_pair_count"], 1)
        self.assertEqual(
            summary["mean_paired_deltas"][
                "configured_minus_generic_fault_exposure_rate"
            ],
            0.0,
        )
        self.assertFalse(
            summary["arm_descriptives"]["generic"][
                "provider_usage_complete"
            ]
        )

    def test_configured_instruction_is_the_only_arm_with_architecture(self):
        generic = INSTRUCTION_PATHS["generic"].read_text(encoding="utf-8")
        configured = INSTRUCTION_PATHS["configured"].read_text(
            encoding="utf-8"
        )
        for phrase in (
            "Risk/value schedule",
            "Budget allocator",
            "Test critic",
            "Marginal-value stopper",
        ):
            self.assertNotIn(phrase, generic)
            self.assertIn(phrase, configured)


if __name__ == "__main__":
    unittest.main()
