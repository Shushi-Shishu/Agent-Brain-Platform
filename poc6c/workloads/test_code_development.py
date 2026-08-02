"""Tests for the provider-independent code-development run harness."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from workloads.code_development import (
    CONFIGURED_INSTRUCTIONS,
    GENERIC_INSTRUCTIONS,
    HarnessError,
    begin_arm_run,
    complete_arm_run,
    load_arm_boundary,
    load_code_development_fixtures,
    prepare_matched_pair,
    run_arm,
    save_arm_boundary,
    summarize_code_development_reports,
)
from workloads.fixture_integrity import snapshot_package


class CodeDevelopmentHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = load_code_development_fixtures()

    def test_prompts_are_strong_and_configured_adds_only_architecture(self):
        generic = GENERIC_INSTRUCTIONS.read_text(encoding="utf-8").casefold()
        configured = CONFIGURED_INSTRUCTIONS.read_text(encoding="utf-8").casefold()
        for phrase in ("task.md", "correct", "boundary", "remaining uncertainty"):
            self.assertIn(phrase, generic)
            self.assertIn(phrase, configured)
        for phrase in (
            "value of information",
            "smallest patch",
            "test critic",
            "stop on evidence",
            "same tools and budget",
        ):
            self.assertIn(phrase, configured)

    def test_prepare_creates_fresh_byte_identical_isolated_copies(self):
        with tempfile.TemporaryDirectory() as temporary:
            pair = prepare_matched_pair(
                self.tasks[0],
                Path(temporary),
                matched_conditions={"max_tool_calls": 8},
            )
            source = snapshot_package(self.tasks[0].public.root)
            generic = snapshot_package(pair.generic_root)
            configured = snapshot_package(pair.configured_root)
            self.assertEqual(source.sha256, generic.sha256)
            self.assertEqual(generic.sha256, configured.sha256)
            self.assertNotEqual(pair.generic_root, pair.configured_root)
            self.assertNotEqual(pair.generic_root, self.tasks[0].public.root)
            with self.assertRaises(HarnessError):
                prepare_matched_pair(self.tasks[0], Path(temporary))

    def test_unchanged_seeded_fixture_is_evaluated_after_agent(self):
        with tempfile.TemporaryDirectory() as temporary:
            pair = prepare_matched_pair(self.tasks[0], Path(temporary))
            observed = {}

            def runner(workspace, instruction):
                observed["workspace"] = workspace
                observed["private_visible"] = (workspace / "private").exists()
                observed["prompt"] = instruction
                return {"summary": "inspected but made no change"}

            report = run_arm(pair, "generic", runner)
            self.assertEqual(observed["workspace"], pair.generic_root)
            self.assertFalse(observed["private_visible"])
            self.assertIn("strong, careful software engineer", observed["prompt"])
            self.assertTrue(report["evaluator"]["executed"])
            self.assertEqual(report["evaluator"]["total"], 3)
            self.assertGreater(report["evaluator"]["failures"], 0)
            self.assertEqual(report["provider"]["input_tokens"], None)
            self.assertTrue(report["diagnostic_only"])
            json.dumps(report)

    def test_agent_patch_gets_post_hash_and_pass_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            pair = prepare_matched_pair(self.tasks[0], Path(temporary))

            def fix_slugify(workspace, _instruction):
                (workspace / "slugify.py").write_text(
                    "import re\n\n"
                    "def slugify(text):\n"
                    "    return re.sub(r'[^a-z0-9]+', '-', "
                    "text.strip().lower()).strip('-')\n",
                    encoding="utf-8",
                )
                return "implemented scoped fix"

            report = run_arm(
                pair,
                "configured",
                fix_slugify,
                provider_metadata={
                    "provider": "test-adapter",
                    "input_tokens": 120,
                    "output_tokens": 30,
                    "cost_amount": None,
                },
            )
            self.assertTrue(report["valid_run"])
            self.assertEqual(report["evaluator"]["returncode"], 0)
            self.assertEqual(report["evaluator"]["passed"], 3)
            self.assertEqual(report["evaluator"]["failures"], 0)
            self.assertNotEqual(
                report["integrity"]["workspace_sha256_pre"],
                report["integrity"]["workspace_sha256_post_agent"],
            )
            self.assertIn(
                "modified:slugify.py",
                report["integrity"]["workspace_changes"],
            )
            self.assertEqual(report["provider"]["total_tokens"], None)

    def test_canary_is_reported_by_id_and_token_is_redacted(self):
        with tempfile.TemporaryDirectory() as temporary:
            pair = prepare_matched_pair(self.tasks[0], Path(temporary))
            token = self.tasks[0].canaries[0].token

            def leaking_runner(workspace, _instruction):
                (workspace / f"notes-{token}.txt").write_text(token, encoding="utf-8")
                return {"raw": f"accidental {token}"}

            report = run_arm(pair, "generic", leaking_runner)
            serialized = json.dumps(report)
            self.assertNotIn(token, serialized)
            self.assertEqual(
                report["integrity"]["leakage_canary_ids"],
                ["canary-DEV-P001"],
            )
            self.assertIn("leakage canary detected", report["integrity"]["violations"])
            self.assertFalse(report["valid_run"])

    def test_change_outside_assigned_workspace_invalidates_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            pair = prepare_matched_pair(self.tasks[0], Path(temporary))

            def bad_runner(_workspace, _instruction):
                (pair.configured_root / "intrusion.txt").write_text(
                    "bad", encoding="utf-8"
                )
                return "done"

            report = run_arm(pair, "generic", bad_runner)
            self.assertFalse(report["valid_run"])
            self.assertTrue(report["integrity"]["unauthorized_edit_detected"])
            self.assertIn(
                "other arm workspace changed during agent run",
                report["integrity"]["violations"],
            )
            self.assertIn(
                "path outside assigned workspace changed during agent run",
                report["integrity"]["violations"],
            )

    def test_tampered_private_evaluator_is_rejected_without_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            fixture_copy = temporary_root / "fixture-copy"
            shutil.copytree(
                self.tasks[0].public.root.parents[1],
                fixture_copy,
            )
            copied_task = load_code_development_fixtures(fixture_copy)[0]
            pair = prepare_matched_pair(copied_task, temporary_root / "runs")

            def bad_runner(_workspace, _instruction):
                (copied_task.private.root / "evaluator_tests.py").write_text(
                    "raise RuntimeError('must not execute')\n",
                    encoding="utf-8",
                )
                return "done"

            report = run_arm(pair, "generic", bad_runner)
            self.assertFalse(report["valid_run"])
            self.assertFalse(report["evaluator"]["executed"])
            self.assertIn(
                "private evaluator integrity changed",
                report["evaluator"]["skip_reason"],
            )

    def test_two_phase_api_and_adapter_error_are_recorded(self):
        with tempfile.TemporaryDirectory() as temporary:
            pair = prepare_matched_pair(self.tasks[1], Path(temporary))
            boundary = begin_arm_run(pair, "generic")
            report = complete_arm_run(
                boundary,
                agent_error={"type": "ProviderError", "message": "offline"},
            )
            self.assertFalse(report["valid_run"])
            self.assertEqual(report["agent"]["error"]["type"], "ProviderError")

        with tempfile.TemporaryDirectory() as temporary:
            pair = prepare_matched_pair(self.tasks[1], Path(temporary))

            def broken_adapter(_workspace, _instruction):
                raise RuntimeError("provider unavailable")

            report = run_arm(pair, "generic", broken_adapter)
            self.assertFalse(report["valid_run"])
            self.assertEqual(report["agent"]["error"]["type"], "RuntimeError")

    def test_two_phase_boundary_survives_process_style_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pair = prepare_matched_pair(self.tasks[2], root / "runs")
            boundary_path = root / "boundaries" / "DEV-P003-generic.json"
            save_arm_boundary(
                begin_arm_run(pair, "generic"),
                boundary_path,
            )
            reloaded = load_arm_boundary(boundary_path)
            self.assertEqual(reloaded.arm, "generic")
            self.assertEqual(reloaded.pair.task.task_id, "DEV-P003")
            self.assertEqual(
                reloaded.workspace_pre.sha256,
                pair.arm_start_snapshot.sha256,
            )
            report = complete_arm_run(reloaded, agent_result="no change")
            self.assertTrue(report["valid_run"])
            self.assertGreater(report["evaluator"]["failures"], 0)

    def test_all_five_seeded_fixtures_produce_structured_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            for task in self.tasks:
                with self.subTest(task_id=task.task_id):
                    pair = prepare_matched_pair(task, Path(temporary))
                    report = run_arm(pair, "generic", lambda _root, _prompt: None)
                    self.assertEqual(report["task_id"], task.task_id)
                    self.assertEqual(report["evaluator"]["total"], 3)
                    self.assertNotEqual(report["evaluator"]["returncode"], 0)

    def test_bad_provider_counts_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pair = prepare_matched_pair(self.tasks[0], Path(temporary))
            with self.assertRaises(HarnessError):
                run_arm(
                    pair,
                    "generic",
                    lambda _root, _prompt: None,
                    provider_metadata={"input_tokens": -1},
                )

    def test_paired_summary_is_diagnostic_and_requires_both_arms(self):
        with tempfile.TemporaryDirectory() as temporary:
            pair = prepare_matched_pair(self.tasks[4], Path(temporary))
            generic = run_arm(pair, "generic", lambda _root, _prompt: None)
            configured = run_arm(
                pair,
                "configured",
                lambda _root, _prompt: None,
            )
            summary = summarize_code_development_reports(
                [generic, configured]
            )
            self.assertEqual(summary["task_count"], 1)
            self.assertEqual(
                summary["status"],
                "instrumentation_only_no_efficacy_claim",
            )
            self.assertEqual(
                summary["paired_outcomes"]["neither_succeeded"],
                1,
            )
            with self.assertRaises(HarnessError):
                summarize_code_development_reports([generic])


if __name__ == "__main__":
    unittest.main()
