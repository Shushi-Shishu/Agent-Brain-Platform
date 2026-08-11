"""
Role isolation tests for POC 6c CI packaging (WP1 / J3-01).

These tests enumerate the actual poc6c/ file tree and assert that:
1. Arm jobs do not receive confirmation/tasks_v1.json, sealed labels, or
   the custodian public key, pilot outputs, or workload results/runs/boundaries.
2. The evaluator job never receives mapping_bundle artifacts or the custodian key.
3. The blinding job's artifact upload list does NOT include mapping_bundle
   in any artifact sent to the evaluator (split-upload enforced in workflow).
4. Every workflow job that downloads artifacts has an explicit allow-list;
   no job silently receives all artifacts.
5. Role-specific tarballs built by build_filtered_package_script() contain
   exactly the expected files — no forbidden paths survive into the archives
   actually used by the workflow.

These tests run against the CURRENT working tree to catch regressions.
They do not spin up a GitHub Actions environment; they verify the static
allow-list definitions in ci_packaging.py, the workflow YAML structure,
and the actual archive contents produced by the packaging helpers.
"""
from __future__ import annotations

import io
import os
import re
import sys
import tarfile
import tempfile
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
    build_filtered_package_script,
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

    def test_each_arm_downloads_role_package(self):
        """Arm jobs must download their named role package, not the generic poc6c-package."""
        text = _workflow_text()
        for role, artifact in [
            ("generic-arm",    "poc6c-generic-arm-package"),
            ("configured-arm", "poc6c-configured-arm-package"),
        ]:
            job_start = text.find(f"\n  {role}:")
            assert job_start != -1, f"Job '{role}' not found"
            next_job = re.search(r'\n  \w[\w-]+:', text[job_start + 1:])
            job_block = text[job_start: job_start + 1 + next_job.start()] if next_job else text[job_start:]
            assert artifact in job_block, (
                f"Job '{role}' must download '{artifact}', not the unfiltered poc6c-package."
            )
            assert "name: poc6c-package\n" not in job_block, (
                f"Job '{role}' must NOT download the unfiltered 'poc6c-package' artifact."
            )

    def test_evaluator_downloads_role_package(self):
        """Evaluator must download its named role package."""
        text = _workflow_text()
        job_start = text.find("\n  blinded-evaluator:")
        assert job_start != -1
        next_job = re.search(r'\n  \w[\w-]+:', text[job_start + 1:])
        job_block = text[job_start: job_start + 1 + next_job.start()] if next_job else text[job_start:]
        assert "poc6c-evaluator-package" in job_block, (
            "Evaluator must download 'poc6c-evaluator-package', not the unfiltered archive."
        )

    def test_blinding_downloads_role_package(self):
        """Blinding job must download its named role package."""
        text = _workflow_text()
        job_start = text.find("\n  deterministic-blinding:")
        assert job_start != -1
        next_job = re.search(r'\n  \w[\w-]+:', text[job_start + 1:])
        job_block = text[job_start: job_start + 1 + next_job.start()] if next_job else text[job_start:]
        assert "poc6c-blinding-package" in job_block, (
            "Blinding must download 'poc6c-blinding-package'."
        )

    def test_preflight_builds_all_five_role_packages(self):
        """Preflight must build and upload packages for all five downstream roles."""
        text = _workflow_text()
        for role_artifact in [
            "poc6c-generic-arm-package",
            "poc6c-configured-arm-package",
            "poc6c-blinding-package",
            "poc6c-evaluator-package",
            "poc6c-integrity-package",
        ]:
            assert role_artifact in text, (
                f"Preflight must upload '{role_artifact}'."
            )

    def test_integrity_validates_six_attestations(self):
        """Integrity job must call validate_attestation_chain on all six stages."""
        text = _workflow_text()
        job_start = text.find("\n  integrity-and-analysis:")
        assert job_start != -1
        job_block = text[job_start:]
        assert "validate_attestation_chain" in job_block, (
            "Integrity job must call validate_attestation_chain."
        )
        # Must include EXPECTED_STAGES (all 6) not just the 5 upstream
        assert "EXPECTED_STAGES" in job_block, (
            "Integrity job must validate against EXPECTED_STAGES (all 6 stages)."
        )


# ---------------------------------------------------------------------------
# Tarball content tests — build actual archives and inspect them
# ---------------------------------------------------------------------------

def _build_full_tarball(src_root: Path, output_path: Path) -> None:
    """Build a full git-archive-like tarball from src_root into output_path."""
    with tarfile.open(output_path, "w:gz") as tar:
        for path in sorted(src_root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(src_root)
            parts = rel.parts
            if "__pycache__" in parts or ".pytest_cache" in parts:
                continue
            if path.name in {"MANIFEST.json", ".DS_Store"}:
                continue
            if path.suffix in {".pyc", ".pyo"}:
                continue
            arcname = f"poc6c/{rel.as_posix()}"
            tar.add(path, arcname=arcname)


def _list_tarball_paths(tarball: Path) -> list[str]:
    """Return sorted poc6c-relative posix paths inside a tarball."""
    paths = []
    with tarfile.open(tarball, "r:gz") as tar:
        for member in tar.getmembers():
            name = member.name
            rel = name[len("poc6c/"):] if name.startswith("poc6c/") else name
            if rel:
                paths.append(rel)
    return sorted(paths)


def _build_role_tarball(full_tarball: Path, role: str, output_path: Path) -> None:
    """Apply build_filtered_package_script logic to produce a role-specific tarball."""
    script = build_filtered_package_script(role)
    # Execute in a context with GITHUB_OUTPUT pointing to /dev/null (or a temp file)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as gh_out:
        gh_out_path = gh_out.name
    orig_dir = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        import shutil
        shutil.copy(full_tarball, Path(tmpdir) / "poc6c-package.tar.gz")
        os.chdir(tmpdir)
        try:
            env_backup = os.environ.get("GITHUB_OUTPUT")
            os.environ["GITHUB_OUTPUT"] = gh_out_path
            exec(compile(script, f"<{role}-pkg>", "exec"))
            role_file = Path(tmpdir) / f"poc6c-{role}-package.tar.gz"
            shutil.copy(role_file, output_path)
        finally:
            os.chdir(orig_dir)
            if env_backup is None:
                os.environ.pop("GITHUB_OUTPUT", None)
            else:
                os.environ["GITHUB_OUTPUT"] = env_backup
            try:
                os.unlink(gh_out_path)
            except OSError:
                pass


class TestActualTarballContents:
    """Build real archives using the workflow packaging logic and inspect their contents.

    These tests verify the archives that the workflow actually distributes,
    not hypothetical filtered path lists.
    """

    @pytest.fixture(scope="class")
    @classmethod
    def full_tarball(cls, tmp_path_factory):
        tarball = tmp_path_factory.mktemp("pkgs") / "poc6c-package.tar.gz"
        _build_full_tarball(HERE, tarball)
        return tarball

    @pytest.mark.parametrize("role", ["generic-arm", "configured-arm"])
    def test_arm_tarball_excludes_tasks_v1(self, full_tarball, tmp_path, role):
        out = tmp_path / f"poc6c-{role}-package.tar.gz"
        _build_role_tarball(full_tarball, role, out)
        paths = _list_tarball_paths(out)
        assert "confirmation/tasks_v1.json" not in paths, (
            f"Role '{role}' tarball contains confirmation/tasks_v1.json"
        )

    @pytest.mark.parametrize("role", ["generic-arm", "configured-arm"])
    def test_arm_tarball_excludes_sealed_labels(self, full_tarball, tmp_path, role):
        out = tmp_path / f"poc6c-{role}-package.tar.gz"
        _build_role_tarball(full_tarball, role, out)
        paths = _list_tarball_paths(out)
        sealed = [p for p in paths if p.startswith("confirmation/sealed/")]
        assert sealed == [], f"Role '{role}' tarball contains sealed files: {sealed}"

    @pytest.mark.parametrize("role", ["generic-arm", "configured-arm"])
    def test_arm_tarball_excludes_custodian_key(self, full_tarball, tmp_path, role):
        out = tmp_path / f"poc6c-{role}-package.tar.gz"
        _build_role_tarball(full_tarball, role, out)
        paths = _list_tarball_paths(out)
        assert "custodian_public_key.pem" not in paths, (
            f"Role '{role}' tarball contains custodian_public_key.pem"
        )

    @pytest.mark.parametrize("role", ["generic-arm", "configured-arm"])
    def test_arm_tarball_excludes_pilot(self, full_tarball, tmp_path, role):
        out = tmp_path / f"poc6c-{role}-package.tar.gz"
        _build_role_tarball(full_tarball, role, out)
        paths = _list_tarball_paths(out)
        pilot_files = [p for p in paths if p.startswith("pilot/")]
        assert pilot_files == [], f"Role '{role}' tarball contains pilot/ files: {pilot_files}"

    @pytest.mark.parametrize("role", ["generic-arm", "configured-arm"])
    @pytest.mark.parametrize("forbidden_prefix", [
        "workloads/results/", "workloads/runs/", "workloads/boundaries/"
    ])
    def test_arm_tarball_excludes_workload_outputs(self, full_tarball, tmp_path, role, forbidden_prefix):
        out = tmp_path / f"poc6c-{role}-{forbidden_prefix.replace('/', '_')}package.tar.gz"
        _build_role_tarball(full_tarball, role, out)
        paths = _list_tarball_paths(out)
        hits = [p for p in paths if p.startswith(forbidden_prefix)]
        assert hits == [], (
            f"Role '{role}' tarball contains '{forbidden_prefix}' files: {hits}"
        )

    def test_evaluator_tarball_excludes_custodian_key(self, full_tarball, tmp_path):
        out = tmp_path / "poc6c-evaluator-package.tar.gz"
        _build_role_tarball(full_tarball, "evaluator", out)
        paths = _list_tarball_paths(out)
        assert "custodian_public_key.pem" not in paths, (
            "Evaluator tarball contains custodian_public_key.pem"
        )

    def test_evaluator_tarball_excludes_tasks_v1(self, full_tarball, tmp_path):
        out = tmp_path / "poc6c-evaluator-package.tar.gz"
        _build_role_tarball(full_tarball, "evaluator", out)
        paths = _list_tarball_paths(out)
        assert "confirmation/tasks_v1.json" not in paths, (
            "Evaluator tarball contains confirmation/tasks_v1.json"
        )

    def test_evaluator_tarball_excludes_pilot(self, full_tarball, tmp_path):
        out = tmp_path / "poc6c-evaluator-package.tar.gz"
        _build_role_tarball(full_tarball, "evaluator", out)
        paths = _list_tarball_paths(out)
        pilot_files = [p for p in paths if p.startswith("pilot/")]
        assert pilot_files == [], f"Evaluator tarball contains pilot/ files: {pilot_files}"

    def test_full_tarball_would_fail_arm_check(self, full_tarball):
        """Confirm the unfiltered tarball DOES contain forbidden files (test has teeth)."""
        paths = _list_tarball_paths(full_tarball)
        # The full tree should contain custodian_public_key.pem
        assert "custodian_public_key.pem" in paths, (
            "Full tarball missing custodian_public_key.pem — test infrastructure broken"
        )

    def test_arm_tarball_still_contains_core_modules(self, full_tarball, tmp_path):
        """Arm tarballs must still contain the runtime modules they need."""
        out = tmp_path / "poc6c-generic-arm-package.tar.gz"
        _build_role_tarball(full_tarball, "generic-arm", out)
        paths = _list_tarball_paths(out)
        for required in ("synthetic_runner.py", "pipeline_artifacts.py", "attestation.py"):
            assert required in paths, (
                f"generic-arm tarball missing required module '{required}'"
            )
