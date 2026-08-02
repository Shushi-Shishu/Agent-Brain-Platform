"""Integrity and executable-defect checks for code-development pilot fixtures."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest

from workloads.fixture_integrity import (
    FORBIDDEN_PUBLIC_MARKERS,
    FixturePackage,
    FixtureTask,
    LeakageCanary,
    snapshot_package,
    validate_fixture_task,
    validate_split_isolation,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "code_development"
TASK_SPECS = (
    ("DEV-P001", "POC6C-DEV-P001-LEAK-C9E7F13A2D48"),
    ("DEV-P002", "POC6C-DEV-P002-LEAK-71B4A08EFD36"),
    ("DEV-P003", "POC6C-DEV-P003-LEAK-4D92BC610AF5"),
    ("DEV-P004", "POC6C-DEV-P004-LEAK-A8350E72C1D9"),
    ("DEV-P005", "POC6C-DEV-P005-LEAK-5F16DCA903B7"),
)


def fixture_tasks() -> tuple[FixtureTask, ...]:
    tasks = []
    for task_id, token in TASK_SPECS:
        root = FIXTURE_ROOT / task_id
        tasks.append(
            FixtureTask(
                task_id=task_id,
                workload="code_development",
                split="pilot",
                public=FixturePackage("public", root / "public"),
                private=FixturePackage("private", root / "private"),
                canaries=(LeakageCanary(f"canary-{task_id}", token),),
            )
        )
    return tuple(tasks)


class CodeDevelopmentFixtureTests(unittest.TestCase):
    def test_all_five_tasks_pass_integrity_validation(self):
        tasks = fixture_tasks()
        self.assertEqual(len(tasks), 5)
        for task in tasks:
            with self.subTest(task_id=task.task_id):
                self.assertEqual(validate_fixture_task(task), [])
                self.assertEqual(task.split, "pilot")
                self.assertEqual(task.workload, "code_development")

    def test_task_and_package_content_is_unique(self):
        tasks = fixture_tasks()
        self.assertEqual(validate_split_isolation(tasks), [])
        public_hashes = {
            snapshot_package(task.public.root).sha256 for task in tasks
        }
        private_hashes = {
            snapshot_package(task.private.root).sha256 for task in tasks
        }
        self.assertEqual(len(public_hashes), len(tasks))
        self.assertEqual(len(private_hashes), len(tasks))

    def test_each_public_package_has_task_and_seeded_source(self):
        for task in fixture_tasks():
            with self.subTest(task_id=task.task_id):
                task_file = task.public.root / "TASK.md"
                source_files = tuple(task.public.root.glob("*.py"))
                self.assertTrue(task_file.is_file())
                self.assertGreaterEqual(len(task_file.read_text(encoding="utf-8")), 120)
                self.assertEqual(len(source_files), 1)

    def test_public_names_and_bytes_exclude_forbidden_words(self):
        for task in fixture_tasks():
            for path in task.public.root.rglob("*"):
                relative = path.relative_to(task.public.root).as_posix().casefold()
                content = path.read_bytes().lower() if path.is_file() else b""
                with self.subTest(task_id=task.task_id, path=relative):
                    for marker in FORBIDDEN_PUBLIC_MARKERS:
                        self.assertNotIn(marker, relative)
                        self.assertNotIn(marker.encode("ascii"), content)

    def test_private_packages_have_inventory_tests_and_unique_canary(self):
        tokens = set()
        for task in fixture_tasks():
            with self.subTest(task_id=task.task_id):
                self.assertTrue(
                    (task.private.root / "defect_inventory.json").is_file()
                )
                self.assertTrue(
                    (task.private.root / "evaluator_tests.py").is_file()
                )
                self.assertTrue((task.private.root / "canary.txt").is_file())
                token = task.canaries[0].token
                self.assertEqual(
                    (task.private.root / "canary.txt")
                    .read_text(encoding="utf-8")
                    .strip(),
                    token,
                )
                tokens.add(token)
        self.assertEqual(len(tokens), len(TASK_SPECS))

    def test_every_seeded_defect_is_observed_by_evaluator(self):
        for task in fixture_tasks():
            test_program = task.private.root / "evaluator_tests.py"
            environment = os.environ.copy()
            environment["POC6C_PUBLIC_ROOT"] = str(task.public.root.resolve())
            completed = subprocess.run(
                [sys.executable, str(test_program)],
                cwd=task.private.root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            with self.subTest(task_id=task.task_id):
                self.assertNotEqual(
                    completed.returncode,
                    0,
                    "seeded defect was not detected by evaluator checks",
                )
                self.assertIn("FAILED", completed.stderr + completed.stdout)


if __name__ == "__main__":
    unittest.main()
