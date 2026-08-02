"""Tests for confirmation task-set lock validation."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

try:
    from .validate_tasks import validate_payloads
except ImportError:
    from validate_tasks import validate_payloads


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class ConfirmationTaskValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = load_json(BASE / "tasks_v1.json")
        cls.batch1 = load_json(ROOT / "poc6c" / "pilot" / "tasks_batch1.json")
        cls.design = load_json(BASE / "sealed" / "design_labels_v1.json")

    def errors_for(self, tasks=None, batch1=None, design=None):
        return validate_payloads(
            copy.deepcopy(tasks if tasks is not None else self.tasks),
            copy.deepcopy(batch1 if batch1 is not None else self.batch1),
            copy.deepcopy(design if design is not None else self.design),
        )

    def test_frozen_set_is_valid(self):
        self.assertEqual(self.errors_for(), [])

    def test_duplicate_question_is_detected(self):
        tasks = copy.deepcopy(self.tasks)
        tasks["cases"][1]["question"] = tasks["cases"][0]["question"]
        errors = self.errors_for(tasks=tasks)
        self.assertTrue(
            any("duplicate confirmation questions" in error for error in errors)
        )

    def test_batch1_overlap_is_detected(self):
        tasks = copy.deepcopy(self.tasks)
        tasks["cases"][0]["question"] = self.batch1["cases"][0]["question"]
        errors = self.errors_for(tasks=tasks)
        self.assertTrue(any("duplicates excluded batch1:Q001" in error for error in errors))

    def test_malformed_id_is_detected(self):
        tasks = copy.deepcopy(self.tasks)
        tasks["cases"][0]["id"] = "Q001"
        errors = self.errors_for(tasks=tasks)
        self.assertTrue(any("malformed ID" in error for error in errors))
        self.assertTrue(any("C001-C032" in error for error in errors))

    def test_budget_and_hash_drift_are_detected(self):
        tasks = copy.deepcopy(self.tasks)
        tasks["per_case_budget"]["max_search_queries"] = 5
        tasks["corpus"]["project008_manifest_sha256"] = "0" * 64
        errors = self.errors_for(tasks=tasks)
        self.assertTrue(any("budget drifted" in error for error in errors))
        self.assertTrue(any("manifest hash drifted" in error for error in errors))

    def test_too_high_lexical_similarity_is_detected(self):
        tasks = copy.deepcopy(self.tasks)
        tasks["cases"][1]["question"] = (
            "How can a knowledge base be organized so people and AI tools can "
            "reliably find, connect, reuse, and govern its material?"
        )
        errors = self.errors_for(tasks=tasks)
        self.assertTrue(any("too-high lexical similarity" in error for error in errors))

    def test_public_cases_cannot_leak_designer_labels(self):
        tasks = copy.deepcopy(self.tasks)
        tasks["cases"][0]["coverage_likelihood"] = "answerable_likely"
        errors = self.errors_for(tasks=tasks)
        self.assertTrue(any("non-public fields" in error for error in errors))

    def test_sealed_balance_drift_is_detected(self):
        design = copy.deepcopy(self.design)
        design["labels"][0]["coverage_likelihood"] = "partial_likely"
        errors = self.errors_for(design=design)
        self.assertTrue(
            any("coverage-likelihood balance drifted" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
