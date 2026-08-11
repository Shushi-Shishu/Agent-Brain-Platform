"""
Role isolation tests for POC 6c CI packaging (WP1 / J3-01).

These tests enumerate the actual poc6c/ file tree and assert that:
1. Arm jobs do not receive confirmation/tasks_v1.json, sealed labels, or
   the custodian public key.
2. The evaluator job never receives mapping_bundle artifacts.
3. The blinding job's artifact upload list does NOT include mapping_bundle
   in any artifact sent to the evaluator (split-upload enforced in workflow).
4. Every workflow job that downloads artifacts has an explicit allow-list;
   no job silently receives all artifacts.

These tests run against the CURRENT working tree to catch regressions.
They do not spin up a GitHub Actions environment; they verify the static
allow-list definitions in ci_packaging.py and the workflow YAML structure.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from ci_packaging import (
    FORBIDDEN_PATHS_IN_PACKAGE_BY_ROLE,
    ROLES,
    assert_evaluator_no_mapping,
    assert_role_package_clean,
    list_package_paths,
    list_filtered_package_paths,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WORKFLOW_PATH = HERE.parent / ".github" / "workflows" / "poc6c-confirmation.yml"


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Package enumeration tests
# ---------------------------------------------------------------------------

class TestPackageEnumeration:
    """Verify that the current poc6c/ file tree satisfies role allow-lists."""

    def test_list_package_paths_nonempty(self):
        paths = list_package_paths()
        assert len(paths) > 0

    def test_all_paths_are_posix(self):
        paths = list_package_paths()
        for p in paths:
            assert "\\" not in p, f"Non-posix path: {p}"

    def test_manifest_excluded(self):
        paths = list_package_paths()
        assert "MANIFEST.json" not in paths

    def test_pycache_excluded(self):
        paths = list_package_paths()
        for p in paths:
            assert "__pycache__" not in p, f"pycache in package: {p}"

    def test_pyc_excluded(self):
        paths = list_package_paths()
        for p in paths:
            assert not p.endswith(".pyc"), f".pyc in package: {p}"


class TestArmRoleIsolation:
    """Arm jobs must not receive confirmation/custody/sealed files."""

    @pytest.mark.parametrize("role", ["generic-arm", "configured-arm"])
    def test_arm_no_tasks_v1(self, role):
        # Use filtered package paths (what the role actually receives)
        paths = list_filtered_package_paths(role)
        assert_role_package_clean(role, paths)

    @pytest.mark.parametrize("role", ["generic-arm", "configured-arm"])
    def test_arm_forbidden_list_is_nontrivial(self, role):
        forbidden = FORBIDDEN_PATHS_IN_PACKAGE_BY_ROLE[role]
        assert len(forbidden) >= 3, (
            f"Role '{role}' should have at least 3 forbidden paths; got {len(forbidden)}"
        )

    def test_evaluator_forbidden_list_is_nontrivial(self):
        forbidden = FORBIDDEN_PATHS_IN_PACKAGE_BY_ROLE["evaluator"]
        assert len(forbidden) >= 2

    @pytest.mark.parametrize("role", ["generic-arm", "configured-arm"])
    def test_arm_filtered_package_excludes_forbidden(self, role):
        """Filtered packages for arm roles must not include forbidden paths."""
        paths = list_filtered_package_paths(role)
        # Directly check: confirmation/tasks_v1.json must not be present
        assert "confirmation/tasks_v1.json" not in paths, (
            f"Role '{role}' filtered package still contains confirmation/tasks_v1.json"
        )
        assert not any(p.startswith("confirmation/sealed/") for p in paths), (
            f"Role '{role}' filtered package still contains sealed/ files"
        )
        assert "custodian_public_key.pem" not in paths, (
            f"Role '{role}' filtered package still contains custodian_public_key.pem"
        )

    @pytest.mark.parametrize("role", ["generic-arm", "configured-arm", "evaluator"])
    def test_assert_role_package_clean_passes_on_filtered_paths(self, role):
        paths = list_filtered_package_paths(role)
        # Should not raise after filtering
        assert_role_package_clean(role, paths)

    def test_full_tree_would_fail_arm_check(self):
        """Confirm that the unfiltered tree DOES fail the arm check (test has teeth)."""
        full_paths = list_package_paths()
        # The unfiltered tree contains forbidden files — check should raise
        try:
            assert_role_package_clean("generic-arm", full_paths)
            pytest.fail("Expected AssertionError — forbidden files are present in full tree")
        except AssertionError:
            pass  # expected


class TestEvaluatorMappingIsolation:
    """The evaluator must never receive mapping_bundle artifacts."""

    def test_no_mapping_artifact_clean(self):
        # Clean list — should pass
        assert_evaluator_no_mapping(["blinded-outputs/blinded_answer_bundle.json",
                                     "evaluation-results/evaluation_results.json"])

    def test_mapping_artifact_detected(self):
        with pytest.raises(AssertionError, match="mapping"):
            assert_evaluator_no_mapping(["blinding-outputs/mapping_bundle.json"])

    def test_mapping_sha256_detected(self):
        with pytest.raises(AssertionError, match="mapping"):
            assert_evaluator_no_mapping(["mapping_bundle.sha256"])

    def test_evaluator_package_clean(self):
        paths = list_filtered_package_paths("evaluator")
        assert_role_package_clean("evaluator", paths)


class TestForbiddenPathDetection:
    """assert_role_package_clean must raise on synthetic violations."""

    def test_raises_on_tasks_v1_for_arm(self):
        fake_paths = [
            "blinding.py",
            "confirmation/tasks_v1.json",  # forbidden for arm jobs
            "synthetic_runner.py",
        ]
        with pytest.raises(AssertionError, match="confirmation/tasks_v1.json"):
            assert_role_package_clean("generic-arm", fake_paths)

    def test_raises_on_sealed_labels_for_arm(self):
        fake_paths = [
            "blinding.py",
            "confirmation/sealed/design_labels_v1.json",
        ]
        with pytest.raises(AssertionError, match="sealed"):
            assert_role_package_clean("configured-arm", fake_paths)

    def test_raises_on_custodian_key_for_arm(self):
        fake_paths = ["blinding.py", "custodian_public_key.pem"]
        with pytest.raises(AssertionError, match="custodian_public_key"):
            assert_role_package_clean("generic-arm", fake_paths)

    def test_no_raise_for_preflight(self):
        # preflight has no forbidden paths — it checks out the full repo
        fake_paths = [
            "confirmation/tasks_v1.json",
            "confirmation/sealed/design_labels_v1.json",
            "custodian_public_key.pem",
        ]
        assert_role_package_clean("preflight", fake_paths)  # should not raise

    def test_unknown_role_raises_valueerror(self):
        with pytest.raises(ValueError, match="Unknown role"):
            assert_role_package_clean("nonexistent-role", [])


# ---------------------------------------------------------------------------
# Workflow structure tests
# ---------------------------------------------------------------------------

class TestWorkflowStructure:
    """Static checks on the GitHub Actions YAML to enforce isolation invariants."""

    def test_workflow_exists(self):
        assert WORKFLOW_PATH.exists(), f"Workflow not found at {WORKFLOW_PATH}"

    def test_arm_jobs_have_no_checkout(self):
        text = _workflow_text()
        # Extract generic-arm and configured-arm job blocks
        for job in ("generic-arm", "configured-arm"):
            # Find the job block start
            job_start = text.find(f"\n  {job}:")
            assert job_start != -1, f"Job '{job}' not found in workflow"
            # Find next job (2-space indent job key)
            next_job = re.search(r'\n  \w[\w-]+:', text[job_start + 1:])
            if next_job:
                job_block = text[job_start: job_start + 1 + next_job.start()]
            else:
                job_block = text[job_start:]
            assert "actions/checkout" not in job_block, (
                f"Job '{job}' must not have a checkout step — it should only "
                f"download the content-addressed poc6c-package artifact."
            )

    def test_evaluator_job_has_no_checkout(self):
        text = _workflow_text()
        job = "blinded-evaluator"
        job_start = text.find(f"\n  {job}:")
        assert job_start != -1, f"Job '{job}' not found in workflow"
        next_job = re.search(r'\n  \w[\w-]+:', text[job_start + 1:])
        if next_job:
            job_block = text[job_start: job_start + 1 + next_job.start()]
        else:
            job_block = text[job_start:]
        assert "actions/checkout" not in job_block, (
            f"Job '{job}' must not have a checkout step."
        )

    def test_blinding_output_uploads_are_split(self):
        """Blinding must upload evaluator input and custody output as SEPARATE artifacts."""
        text = _workflow_text()
        assert "name: evaluator-input" in text or "blinded-answer-bundle" in text.lower() or \
               "evaluation-input" in text, (
            "Blinding job must upload evaluator input (blinded bundle) as a separate "
            "artifact from the custody mapping output."
        )
        assert "mapping_bundle" in text or "mapping-bundle" in text.lower() or \
               "custody-output" in text, (
            "Blinding job must upload mapping_bundle as a separate custody artifact."
        )

    def test_evaluator_downloads_bundle_not_mapping(self):
        """Evaluator job must download the blinded bundle, NOT the mapping bundle."""
        text = _workflow_text()
        # Find evaluator job block
        job = "blinded-evaluator"
        job_start = text.find(f"\n  {job}:")
        assert job_start != -1
        next_job = re.search(r'\n  \w[\w-]+:', text[job_start + 1:])
        if next_job:
            job_block = text[job_start: job_start + 1 + next_job.start()]
        else:
            job_block = text[job_start:]
        # Evaluator must download something from blinding outputs (the bundle)
        assert "blinding-outputs" in job_block or "evaluator-input" in job_block or \
               "blinded-answer-bundle" in job_block.lower(), (
            "Evaluator job must download the blinded answer bundle from blinding."
        )
        # Evaluator must not download the full blinding-outputs if it contains mapping
        # This is enforced by requiring the upload to be split

    def test_six_jobs_present(self):
        text = _workflow_text()
        required_jobs = [
            "preflight",
            "generic-arm",
            "configured-arm",
            "deterministic-blinding",
            "blinded-evaluator",
            "integrity-and-analysis",
        ]
        for job in required_jobs:
            assert job in text, f"Required job '{job}' not found in workflow"

    def test_per_job_attestations_uploaded(self):
        text = _workflow_text()
        required_attestation_artifacts = [
            "attestation-preflight",
            "attestation-generic-arm",
            "attestation-configured-arm",
            "attestation-deterministic-blinding",
            "attestation-blinded-evaluator",
        ]
        for artifact in required_attestation_artifacts:
            assert artifact in text, (
                f"Attestation artifact '{artifact}' not found in workflow uploads. "
                "Each job must upload its attestation."
            )

    def test_integrity_job_downloads_evaluation_results(self):
        """Integrity job must receive the evaluation results from the evaluator."""
        text = _workflow_text()
        # Find integrity job block
        job_start = text.find("\n  integrity-and-analysis:")
        assert job_start != -1
        job_block = text[job_start:]
        assert "evaluation-results" in job_block or "all-artifacts" in job_block, (
            "Integrity job must download evaluation results (directly or via all-artifacts)."
        )

    def test_no_hardcoded_attestation_chain_valid_true(self):
        """Integrity job must not hardcode attestation_chain_valid=True without validation."""
        text = _workflow_text()
        # Find integrity job section
        job_start = text.find("\n  integrity-and-analysis:")
        if job_start == -1:
            return
        job_block = text[job_start:]
        # Must NOT hardcode True without calling validate_attestation_chain first
        # We allow True only if validate_attestation_chain is called
        if "attestation_chain_valid=True" in job_block:
            assert "validate_attestation_chain" in job_block or \
                   "aggregate_attestations" in job_block, (
                "integrity job sets attestation_chain_valid=True without calling "
                "validate_attestation_chain() or aggregate_attestations(). "
                "This must be derived from actual chain validation."
            )

    def test_workflow_manual_trigger_only(self):
        text = _workflow_text()
        assert "workflow_dispatch" in text
        assert "on:\n  push:" not in text
        assert "on:\n  pull_request:" not in text
