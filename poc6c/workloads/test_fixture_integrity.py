"""Tests for sealed POC 6c code-workload fixtures."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from workloads.fixture_integrity import (
    FileFingerprint,
    FixturePackage,
    FixtureTask,
    IntegrityError,
    LeakageCanary,
    PackageSnapshot,
    detect_canary_leakage,
    fixture_identity,
    snapshot_package,
    stable_hash_bytes,
    stable_hash_text,
    validate_fixture_task,
    validate_matched_public_copies,
    validate_split_isolation,
)


class FixtureIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, content: str | bytes) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def make_task(
        self,
        task_id: str = "DEV-P001",
        split: str = "pilot",
        suffix: str = "one",
    ) -> FixtureTask:
        public = self.root / split / task_id / "public"
        private = self.root / split / task_id / "private"
        public.mkdir(parents=True)
        private.mkdir(parents=True)
        self.write(
            f"{split}/{task_id}/public/src/math_{suffix}.py",
            f"def add_{suffix}(a, b):\n    return a + b\n",
        )
        token = f"POC6C-CANARY-{split}-{task_id}-{suffix}-8675309"
        self.write(
            f"{split}/{task_id}/private/evaluator_{suffix}.json",
            json.dumps({"canary": token, "expected": suffix}),
        )
        return FixtureTask(
            task_id=task_id,
            workload="code_development",
            split=split,
            public=FixturePackage("public", public),
            private=FixturePackage("private", private),
            canaries=(LeakageCanary(f"canary-{task_id}", token),),
        )

    def test_stable_hash_primitives_are_uppercase_sha256(self):
        self.assertEqual(stable_hash_text("abc"), stable_hash_bytes(b"abc"))
        self.assertEqual(
            stable_hash_text("abc"),
            "BA7816BF8F01CFEA414140DE5DAE2223"
            "B00361A396177A9CB410FF61F20015AD",
        )

    def test_snapshot_is_location_and_enumeration_independent(self):
        first = self.root / "first"
        second = self.root / "second"
        self.write("first/z.txt", "last")
        self.write("first/nested/a.txt", "first")
        self.write("second/nested/a.txt", "first")
        self.write("second/z.txt", "last")
        first_snapshot = snapshot_package(first)
        second_snapshot = snapshot_package(second)
        self.assertEqual(first_snapshot, second_snapshot)
        self.assertEqual(
            [record.path for record in first_snapshot.files],
            ["nested/a.txt", "z.txt"],
        )

    def test_snapshot_changes_for_content_path_or_size(self):
        root = self.root / "package"
        path = self.write("package/source.py", "x = 1\n")
        original = snapshot_package(root)
        path.write_text("x = 2\n", encoding="utf-8")
        changed_content = snapshot_package(root)
        self.assertNotEqual(original.sha256, changed_content.sha256)
        path.rename(root / "renamed.py")
        changed_path = snapshot_package(root)
        self.assertNotEqual(changed_content.sha256, changed_path.sha256)

    def test_snapshot_rejects_missing_root_and_file_root(self):
        with self.assertRaisesRegex(IntegrityError, "does not exist"):
            snapshot_package(self.root / "missing")
        file_path = self.write("single.txt", "content")
        with self.assertRaisesRegex(IntegrityError, "not a directory"):
            snapshot_package(file_path)

    def test_snapshot_rejects_symlinks_when_supported(self):
        package = self.root / "package"
        package.mkdir()
        target = self.write("outside.txt", "private")
        link = package / "link.txt"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("symlink creation is unavailable on this platform")
        with self.assertRaisesRegex(IntegrityError, "symlink"):
            snapshot_package(package)

    def test_snapshot_rejects_symlink_root_when_supported(self):
        real = self.root / "real-package"
        real.mkdir()
        self.write("real-package/source.py", "x = 1\n")
        alias = self.root / "package-alias"
        try:
            alias.symlink_to(real, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation is unavailable on this platform")
        with self.assertRaisesRegex(IntegrityError, "root cannot be a symlink"):
            snapshot_package(alias)

    def test_snapshot_dataclass_rejects_tampering(self):
        file_record = FileFingerprint(
            path="a.txt",
            size_bytes=1,
            sha256=stable_hash_bytes(b"a"),
        )
        with self.assertRaisesRegex(IntegrityError, "does not match"):
            PackageSnapshot(files=(file_record,), sha256="A" * 64)

    def test_valid_public_private_fixture_passes(self):
        task = self.make_task()
        self.assertEqual(validate_fixture_task(task), [])
        self.assertEqual(len(fixture_identity(task)), 64)

    def test_nested_or_identical_roots_are_rejected(self):
        root = self.root / "overlap"
        private = root / "private"
        private.mkdir(parents=True)
        self.write("overlap/source.py", "x = 1\n")
        task = FixtureTask(
            task_id="DEV-P002",
            workload="code_development",
            split="pilot",
            public=FixturePackage("public", root),
            private=FixturePackage("private", private),
        )
        self.assertIn(
            "public and private package roots overlap",
            validate_fixture_task(task),
        )

    def test_public_path_markers_are_rejected_case_insensitively(self):
        for index, marker in enumerate(("hidden_case.py", "ORACLE.txt", "mutants.js")):
            with self.subTest(marker=marker):
                task = self.make_task(
                    task_id=f"DEV-P1{index:02}",
                    suffix=f"path{index}",
                )
                self.write(
                    f"pilot/{task.task_id}/public/src/{marker}",
                    "safe content\n",
                )
                errors = validate_fixture_task(task)
                self.assertTrue(
                    any("public path contains forbidden marker" in error for error in errors)
                )

    def test_hidden_dot_paths_are_rejected(self):
        task = self.make_task(task_id="DEV-P200", suffix="dot")
        self.write("pilot/DEV-P200/public/.answers", "safe-looking data")
        self.assertTrue(
            any("public path is hidden" in error for error in validate_fixture_task(task))
        )

    def test_public_text_and_binary_marker_content_are_rejected(self):
        task = self.make_task(task_id="DEV-P201", suffix="content")
        self.write(
            "pilot/DEV-P201/public/src/answer.py",
            b"\x00metadata:MuTaNt-case-7\xff",
        )
        errors = validate_fixture_task(task)
        self.assertTrue(
            any("content contains forbidden marker 'mutant'" in error for error in errors)
        )

    def test_private_markers_are_allowed(self):
        task = self.make_task(task_id="DEV-P202", suffix="private")
        self.write(
            "pilot/DEV-P202/private/hidden_mutant_oracle.json",
            '{"purpose": "hidden oracle for mutant scoring"}',
        )
        self.assertEqual(validate_fixture_task(task), [])

    def test_canary_must_be_private_and_absent_from_public(self):
        task = self.make_task(task_id="DEV-P203", suffix="boundary")
        canary = task.canaries[0]
        public_file = task.public.root / "README.txt"
        public_file.write_text(f"accidental {canary.token}", encoding="utf-8")
        errors = validate_fixture_task(task)
        self.assertTrue(any("appears in public package" in error for error in errors))
        self.assertNotIn(canary.token, "\n".join(errors))

        public_file.write_text("safe", encoding="utf-8")
        for path in task.private.root.rglob("*"):
            if path.is_file():
                path.write_text("canary was removed", encoding="utf-8")
        errors = validate_fixture_task(task)
        self.assertTrue(any("absent from private package" in error for error in errors))

    def test_canary_output_interface_handles_text_bytes_and_records(self):
        first = LeakageCanary("private-a", "CANARY-SECRET-ALPHA-1234")
        second = LeakageCanary("private-b", "CANARY-SECRET-BRAVO-5678")
        self.assertEqual(
            detect_canary_leakage(
                f"answer contains {first.token}",
                (first, second),
            ),
            ("private-a",),
        )
        self.assertEqual(
            detect_canary_leakage(second.token.encode("utf-8"), (first, second)),
            ("private-b",),
        )
        self.assertEqual(
            detect_canary_leakage(
                {"trace": [{"payload": first.token}, second.token]},
                (first, second),
            ),
            ("private-a", "private-b"),
        )
        self.assertEqual(detect_canary_leakage("clean", (first, second)), ())
        self.assertNotEqual(first.token_sha256, first.token)

    def test_canary_validation_rejects_weak_and_duplicate_values(self):
        with self.assertRaisesRegex(IntegrityError, "16"):
            LeakageCanary("short", "tiny")
        with self.assertRaisesRegex(IntegrityError, "invalid"):
            LeakageCanary("bad id!", "long-enough-private-token")
        task = self.make_task(task_id="DEV-P204", suffix="duplicate")
        with self.assertRaisesRegex(IntegrityError, "duplicate leakage canary ids"):
            FixtureTask(
                task_id=task.task_id,
                workload=task.workload,
                split=task.split,
                public=task.public,
                private=task.private,
                canaries=(
                    task.canaries[0],
                    LeakageCanary(task.canaries[0].canary_id, "DIFFERENT-CANARY-TOKEN-123"),
                ),
            )

    def test_split_isolation_accepts_unique_tasks(self):
        tasks = [
            self.make_task("DEV-P300", "pilot", "p"),
            self.make_task("DEV-S300", "selection", "s"),
            self.make_task("DEV-C300", "confirmation", "c"),
        ]
        self.assertEqual(validate_split_isolation(tasks), [])

    def test_split_isolation_rejects_duplicate_ids(self):
        first = self.make_task("DEV-DUP", "pilot", "pilot")
        second = self.make_task("DEV-DUP", "selection", "selection")
        errors = validate_split_isolation((first, second))
        self.assertTrue(any("duplicate task_id" in error for error in errors))

    def test_split_isolation_rejects_duplicate_public_hashes(self):
        first = self.make_task("DEV-P400", "pilot", "same")
        second = self.make_task("DEV-S400", "selection", "different")
        shutil.rmtree(second.public.root)
        shutil.copytree(first.public.root, second.public.root)
        errors = validate_split_isolation((first, second))
        self.assertTrue(any("duplicate public hash" in error for error in errors))

    def test_split_isolation_rejects_duplicate_private_hashes(self):
        first = self.make_task("DEV-P401", "pilot", "private-a")
        second = self.make_task("DEV-C401", "confirmation", "private-b")
        shutil.rmtree(second.private.root)
        shutil.copytree(first.private.root, second.private.root)
        errors = validate_split_isolation((first, second))
        self.assertTrue(any("duplicate private hash" in error for error in errors))

    def test_matched_public_copies_pass_when_byte_identical(self):
        task = self.make_task(task_id="DEV-P500", suffix="matched")
        generic = self.root / "runs" / "generic"
        configured = self.root / "runs" / "configured"
        shutil.copytree(task.public.root, generic)
        shutil.copytree(task.public.root, configured)
        self.assertEqual(
            validate_matched_public_copies(task.public.root, generic, configured),
            [],
        )

    def test_matched_public_copies_report_changed_missing_and_extra_files(self):
        task = self.make_task(task_id="DEV-P501", suffix="drift")
        generic = self.root / "runs" / "generic-drift"
        configured = self.root / "runs" / "configured-drift"
        shutil.copytree(task.public.root, generic)
        shutil.copytree(task.public.root, configured)
        source_path = next(path for path in generic.rglob("*.py"))
        source_path.write_text("changed\n", encoding="utf-8")
        configured_source = next(path for path in configured.rglob("*.py"))
        configured_source.unlink()
        (configured / "extra.txt").write_text("extra\n", encoding="utf-8")

        errors = validate_matched_public_copies(
            task.public.root,
            generic,
            configured,
        )
        self.assertTrue(any("generic public snapshot changed paths" in e for e in errors))
        self.assertTrue(any("configured public snapshot missing paths" in e for e in errors))
        self.assertTrue(any("configured public snapshot has extra paths" in e for e in errors))
        self.assertIn(
            "generic and configured public snapshots do not match",
            errors,
        )

    def test_matched_public_copies_require_isolated_workspace_roots(self):
        task = self.make_task(task_id="DEV-P502", suffix="isolation")
        shared = self.root / "runs" / "shared"
        shutil.copytree(task.public.root, shared)
        errors = validate_matched_public_copies(
            task.public.root,
            shared,
            shared,
        )
        self.assertIn(
            "generic and configured public roots overlap",
            errors,
        )

    def test_invalid_fixture_metadata_is_rejected_early(self):
        root = self.root / "metadata"
        root.mkdir()
        with self.assertRaisesRegex(IntegrityError, "role"):
            FixturePackage("agent", root)
        with self.assertRaisesRegex(IntegrityError, "unknown fixture split"):
            FixtureTask(
                task_id="DEV-X",
                workload="code_development",
                split="training",
                public=FixturePackage("public", root),
                private=FixturePackage("private", self.root / "other"),
            )


if __name__ == "__main__":
    unittest.main()
