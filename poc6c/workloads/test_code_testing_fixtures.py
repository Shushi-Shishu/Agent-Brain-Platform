"""Integrity and executable scorer checks for code-testing pilot fixtures."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from workloads.fixture_integrity import (
    FORBIDDEN_PUBLIC_MARKERS,
    FixturePackage,
    FixtureTask,
    LeakageCanary,
    fixture_identity,
    snapshot_package,
    validate_fixture_task,
    validate_split_isolation,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "code_testing"
TASK_SPECS = (
    ("TST-P001", "POC6C-TST-P001-LEAK-4A8D1C73F2B9"),
    ("TST-P002", "POC6C-TST-P002-LEAK-9F31B6E047AC"),
    ("TST-P003", "POC6C-TST-P003-LEAK-2D74A91EC563"),
    ("TST-P004", "POC6C-TST-P004-LEAK-B80F23D169E5"),
    ("TST-P005", "POC6C-TST-P005-LEAK-63C0A7E24B91"),
)


def fixture_tasks() -> tuple[FixtureTask, ...]:
    return tuple(
        FixtureTask(
            task_id=task_id,
            workload="code_testing",
            split="pilot",
            public=FixturePackage("public", FIXTURE_ROOT / task_id / "public"),
            private=FixturePackage("private", FIXTURE_ROOT / task_id / "private"),
            canaries=(LeakageCanary(f"canary-{task_id}", token),),
        )
        for task_id, token in TASK_SPECS
    )


def load_scorer(task: FixtureTask):
    path = task.private.root / "score_tests.py"
    spec = importlib.util.spec_from_file_location(
        f"poc6c_testing_scorer_{task.task_id.lower()}", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load scorer for {task.task_id}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CodeTestingFixtureTests(unittest.TestCase):
    def test_all_five_tasks_pass_sealed_fixture_integrity(self):
        tasks = fixture_tasks()
        self.assertEqual(len(tasks), 5)
        for task in tasks:
            with self.subTest(task_id=task.task_id):
                self.assertEqual(validate_fixture_task(task), [])
                self.assertEqual(task.workload, "code_testing")
                self.assertEqual(task.split, "pilot")

    def test_every_task_and_package_identity_is_unique(self):
        tasks = fixture_tasks()
        self.assertEqual(validate_split_isolation(tasks), [])
        self.assertEqual(len({fixture_identity(task) for task in tasks}), 5)
        self.assertEqual(
            len({snapshot_package(task.public.root).sha256 for task in tasks}), 5
        )
        self.assertEqual(
            len({snapshot_package(task.private.root).sha256 for task in tasks}), 5
        )

    def test_public_packages_obey_surface_and_language_constraints(self):
        module_names = set()
        for task in fixture_tasks():
            source_files = tuple(
                path
                for path in task.public.root.glob("*.py")
                if not path.name.startswith("test_")
            )
            with self.subTest(task_id=task.task_id):
                self.assertEqual(len(source_files), 1)
                self.assertTrue((task.public.root / "test_visible.py").is_file())
                task_text = (task.public.root / "TASK.md").read_text(encoding="utf-8")
                self.assertIn("at most 8", task_text)
                self.assertIn("3 seconds", task_text)
                self.assertGreaterEqual(len(task_text), 300)
            module_names.add(source_files[0].name)
            for path in task.public.root.rglob("*"):
                relative = path.relative_to(task.public.root).as_posix().casefold()
                content = path.read_bytes().lower() if path.is_file() else b""
                for marker in FORBIDDEN_PUBLIC_MARKERS:
                    self.assertNotIn(marker, relative)
                    self.assertNotIn(marker.encode("ascii"), content)
        self.assertEqual(len(module_names), 5)

    def test_visible_tests_pass_on_supplied_modules(self):
        for task in fixture_tasks():
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "unittest",
                    "-v",
                    "test_visible",
                ],
                cwd=task.public.root,
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            with self.subTest(task_id=task.task_id):
                self.assertEqual(
                    completed.returncode,
                    0,
                    completed.stdout + completed.stderr,
                )

    def test_reference_suite_exposes_every_distinct_fault(self):
        for task in fixture_tasks():
            scorer = load_scorer(task)
            result = scorer.evaluate(
                task.private.root / "reference_tests.py",
                task.public.root,
            )
            with self.subTest(task_id=task.task_id):
                self.assertTrue(result["valid"], result)
                self.assertTrue(result["baseline_passes"])
                self.assertTrue(result["stable"])
                self.assertTrue(result["runtime_within_budget"])
                self.assertLessEqual(result["declared_test_count"], 8)
                self.assertEqual(result["fault_count"], 3)
                self.assertEqual(result["distinct_faults_exposed"], 3)
                self.assertEqual(result["fault_exposure_rate"], 1.0)

    def test_scorer_rejects_source_coupled_submission(self):
        task = fixture_tasks()[0]
        scorer = load_scorer(task)
        source = """\
import inspect
import unittest
import buckets

class Coupled(unittest.TestCase):
    def test_source(self):
        self.assertIn("bucket_index", inspect.getsource(buckets))
"""
        with tempfile.TemporaryDirectory(prefix="poc6c-coupled-") as temp_name:
            candidate = Path(temp_name) / "test_candidate.py"
            candidate.write_text(source, encoding="utf-8")
            result = scorer.evaluate(candidate, task.public.root)
        self.assertFalse(result["valid"])
        self.assertIn("implementation_coupled", result["invalid_reasons"])
        self.assertIn("import:inspect", result["implementation_coupling_findings"])
        self.assertEqual(result["distinct_faults_exposed"], 0)

    def test_private_packages_have_three_faults_and_unique_canaries(self):
        all_fault_ids = set()
        tokens = set()
        for task in fixture_tasks():
            scorer = load_scorer(task)
            faults = scorer._faults()
            token = task.canaries[0].token
            with self.subTest(task_id=task.task_id):
                self.assertEqual(len(faults), 3)
                self.assertEqual(
                    (task.private.root / "canary.txt")
                    .read_text(encoding="utf-8")
                    .strip(),
                    token,
                )
                self.assertTrue((task.private.root / "reference_tests.py").is_file())
            for fault in faults:
                self.assertNotIn(fault["fault_id"], all_fault_ids)
                self.assertTrue(fault["source"].strip())
                all_fault_ids.add(fault["fault_id"])
            tokens.add(token)
        self.assertEqual(len(all_fault_ids), 15)
        self.assertEqual(len(tokens), 5)


if __name__ == "__main__":
    unittest.main()
