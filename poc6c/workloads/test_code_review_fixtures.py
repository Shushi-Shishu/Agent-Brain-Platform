"""Integrity, schema, and scorer checks for code-review pilot fixtures."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

from workloads.fixture_integrity import (
    FixturePackage,
    FixtureTask,
    LeakageCanary,
    fixture_identity,
    snapshot_package,
    validate_fixture_task,
    validate_split_isolation,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "code_review"
TASK_SPECS = (
    ("CRV-P001", "POC6C-CRV-P001-LEAK-8A31D7F2C904"),
    ("CRV-P002", "POC6C-CRV-P002-LEAK-17E4BC93A608"),
    ("CRV-P003", "POC6C-CRV-P003-LEAK-6FD20A51B873"),
    ("CRV-P004", "POC6C-CRV-P004-LEAK-B5429C0E7D16"),
    ("CRV-P005", "POC6C-CRV-P005-LEAK-C31958A7E024"),
)
SEVERITIES = {"low", "medium", "high", "critical"}


def fixture_tasks() -> tuple[FixtureTask, ...]:
    tasks = []
    for task_id, token in TASK_SPECS:
        root = FIXTURE_ROOT / task_id
        tasks.append(
            FixtureTask(
                task_id=task_id,
                workload="code_review",
                split="pilot",
                public=FixturePackage("public", root / "public"),
                private=FixturePackage("private", root / "private"),
                canaries=(LeakageCanary(f"canary-{task_id}", token),),
            )
        )
    return tuple(tasks)


def load_inventory(task: FixtureTask) -> dict:
    return json.loads(
        (task.private.root / "defect_inventory.json").read_text(encoding="utf-8")
    )


def load_evaluator(task: FixtureTask):
    path = task.private.root / "evaluate_review.py"
    spec = importlib.util.spec_from_file_location(
        f"poc6c_review_evaluator_{task.task_id.lower()}", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load evaluator for {task.task_id}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CodeReviewFixtureTests(unittest.TestCase):
    def test_all_five_tasks_pass_sealed_fixture_integrity(self):
        tasks = fixture_tasks()
        self.assertEqual(len(tasks), 5)
        for task in tasks:
            with self.subTest(task_id=task.task_id):
                self.assertEqual(validate_fixture_task(task), [])
                self.assertEqual(task.workload, "code_review")
                self.assertEqual(task.split, "pilot")

    def test_task_package_and_content_identities_are_unique(self):
        tasks = fixture_tasks()
        self.assertEqual(validate_split_isolation(tasks), [])
        self.assertEqual(len({task.task_id for task in tasks}), len(tasks))
        self.assertEqual(len({fixture_identity(task) for task in tasks}), len(tasks))
        self.assertEqual(
            len({snapshot_package(task.public.root).sha256 for task in tasks}),
            len(tasks),
        )
        self.assertEqual(
            len({snapshot_package(task.private.root).sha256 for task in tasks}),
            len(tasks),
        )
        content_ids = {load_inventory(task)["content_id"] for task in tasks}
        self.assertEqual(len(content_ids), len(tasks))

    def test_public_packages_are_small_review_surfaces(self):
        for task in fixture_tasks():
            with self.subTest(task_id=task.task_id):
                task_text = (task.public.root / "TASK.md").read_text(encoding="utf-8")
                source_files = tuple(task.public.root.glob("*.py"))
                self.assertGreaterEqual(len(task_text), 180)
                self.assertEqual(len(source_files), 1)
                self.assertLessEqual(len(source_files[0].read_text().splitlines()), 30)

    def test_inventory_has_precise_machine_readable_defects(self):
        defect_ids = set()
        observed_severities = set()
        observed_categories = set()
        surfaces = []
        for task in fixture_tasks():
            inventory = load_inventory(task)
            surfaces.append(inventory["surface"])
            with self.subTest(task_id=task.task_id):
                self.assertEqual(inventory["schema_version"], 1)
                self.assertEqual(inventory["task_id"], task.task_id)
                self.assertIn(inventory["surface"], {"seeded", "near_clean"})
                self.assertEqual(inventory["location_tolerance_lines"], 1)
                self.assertGreaterEqual(len(inventory["defects"]), 1)
                self.assertLessEqual(len(inventory["defects"]), 3)
            for defect in inventory["defects"]:
                source = task.public.root / defect["file"]
                lines = source.read_text(encoding="utf-8").splitlines()
                with self.subTest(task_id=task.task_id, defect=defect["defect_id"]):
                    self.assertTrue(source.is_file())
                    self.assertIsInstance(defect["line"], int)
                    self.assertGreater(defect["line"], 0)
                    self.assertLessEqual(defect["line"], len(lines))
                    self.assertIn(defect["evidence"], lines[defect["line"] - 1])
                    self.assertIn(defect["severity"], SEVERITIES)
                    self.assertTrue(defect["category"])
                    self.assertTrue(defect["title"])
                    self.assertTrue(defect["expected_finding"])
                    self.assertNotIn(defect["defect_id"], defect_ids)
                defect_ids.add(defect["defect_id"])
                observed_severities.add(defect["severity"])
                observed_categories.add(defect["category"])
        self.assertIn("near_clean", surfaces)
        self.assertEqual(observed_severities, SEVERITIES)
        self.assertGreaterEqual(len(observed_categories), 5)

    def test_near_clean_surface_limits_false_positive_opportunity(self):
        near_clean = [
            load_inventory(task)
            for task in fixture_tasks()
            if load_inventory(task)["surface"] == "near_clean"
        ]
        self.assertEqual(len(near_clean), 1)
        self.assertEqual(len(near_clean[0]["defects"]), 1)

    def test_private_evaluator_matches_once_and_counts_noise(self):
        for task in fixture_tasks():
            inventory = load_inventory(task)
            evaluator = load_evaluator(task)
            exact_findings = [
                {
                    "file": defect["file"],
                    "line": defect["line"],
                    "category": defect["category"],
                    "severity": defect["severity"],
                }
                for defect in inventory["defects"]
            ]
            perfect = evaluator.evaluate(exact_findings)
            with self.subTest(task_id=task.task_id, case="perfect"):
                self.assertEqual(perfect["task_id"], task.task_id)
                self.assertEqual(
                    perfect["true_positive_count"], len(inventory["defects"])
                )
                self.assertEqual(perfect["missed_count"], 0)
                self.assertEqual(perfect["false_positive_count"], 0)
                self.assertEqual(perfect["severity_weighted_recall"], 1.0)

            synonym_categories = [
                {**finding, "category": f"alternate_{index}"}
                for index, finding in enumerate(exact_findings, start=1)
            ]
            synonym_result = evaluator.evaluate(synonym_categories)
            with self.subTest(task_id=task.task_id, case="category_synonym"):
                self.assertEqual(
                    synonym_result["true_positive_count"],
                    len(inventory["defects"]),
                )
                self.assertEqual(synonym_result["false_positive_count"], 0)

            repeated_and_bogus = exact_findings + [
                exact_findings[0],
                {
                    "file": exact_findings[0]["file"],
                    "line": 999,
                    "category": "style",
                    "severity": "low",
                },
            ]
            noisy = evaluator.evaluate(repeated_and_bogus)
            with self.subTest(task_id=task.task_id, case="noise"):
                self.assertEqual(
                    noisy["true_positive_count"], len(inventory["defects"])
                )
                self.assertEqual(noisy["false_positive_count"], 2)

    def test_each_private_package_has_unique_canary_and_evaluator(self):
        tokens = set()
        for task in fixture_tasks():
            token = task.canaries[0].token
            with self.subTest(task_id=task.task_id):
                self.assertEqual(
                    (task.private.root / "canary.txt")
                    .read_text(encoding="utf-8")
                    .strip(),
                    token,
                )
                self.assertTrue((task.private.root / "evaluate_review.py").is_file())
            tokens.add(token)
        self.assertEqual(len(tokens), len(TASK_SPECS))


if __name__ == "__main__":
    unittest.main()
