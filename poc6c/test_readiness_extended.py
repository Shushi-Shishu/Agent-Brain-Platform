"""
Extended readiness tests for T4B-04 / R08 findings.

Covers:
- R08 vault-absent makes passed=False (both check_hash_reverification and
  check_vault_hashes_with_actual_vault)
- R08 requires both corpus_manifest AND indexed_body to pass
- No hardcoded developer vault path
- run_preflight() reports infra checks (not discarded)
- run_diagnostic_preflight() raises when R08 is PENDING (vault absent)
"""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from readiness import (
    check_hash_reverification,
    check_vault_hashes_with_actual_vault,
    run_preflight,
    run_diagnostic_preflight,
    PreflightFailed,
    DiagnosticPreflightFailed,
)


class TestVaultHashNoHardcodedPath:
    def test_no_project008_path_env_no_vault_root_returns_error(self, monkeypatch):
        """Without PROJECT008_PATH or explicit vault_root, must return error — no hardcoded default."""
        monkeypatch.delenv("PROJECT008_PATH", raising=False)
        result = check_vault_hashes_with_actual_vault(vault_root=None)
        assert result["passed"] is False
        assert result["vault_present"] is False
        error_text = " ".join(result["errors"])
        assert "PROJECT008_PATH" in error_text or "Vault path not" in error_text

    def test_explicit_nonexistent_vault_root_returns_error(self, tmp_path):
        """Explicit vault_root that does not exist returns vault_present=False."""
        result = check_vault_hashes_with_actual_vault(vault_root=tmp_path / "does_not_exist")
        assert result["passed"] is False
        assert result["vault_present"] is False

    def test_project008_path_env_nonexistent_returns_error(self, monkeypatch, tmp_path):
        """PROJECT008_PATH pointing to nonexistent dir returns error."""
        monkeypatch.setenv("PROJECT008_PATH", str(tmp_path / "no_vault"))
        result = check_vault_hashes_with_actual_vault(vault_root=None)
        assert result["passed"] is False
        assert result["vault_present"] is False


class TestVaultHashRequiresBothCommitments:
    def _make_vault_with_only_manifest(self, tmp_path: Path) -> Path:
        """Create a fake vault with identity-manifest.json but no indexed_body.json."""
        state_dir = tmp_path / "0. Exploration & Applicability Engine" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "identity-manifest.json").write_bytes(b"fake manifest content")
        return tmp_path

    def test_only_manifest_present_not_passing(self, tmp_path):
        """vault with only corpus_manifest (no indexed_body) must not pass R08."""
        vault = self._make_vault_with_only_manifest(tmp_path)
        result = check_vault_hashes_with_actual_vault(vault_root=vault)
        assert result["passed"] is False
        assert result["vault_present"] is True
        errors = result["errors"]
        assert any("indexed_body" in e for e in errors)

    def test_both_missing_not_passing(self, tmp_path):
        """vault root exists but neither file present."""
        state_dir = tmp_path / "0. Exploration & Applicability Engine" / "state"
        state_dir.mkdir(parents=True)
        result = check_vault_hashes_with_actual_vault(vault_root=tmp_path)
        assert result["passed"] is False
        errors = result["errors"]
        assert any("identity-manifest" in e or "corpus_manifest" in e for e in errors)
        assert any("indexed_body" in e for e in errors)

    def test_both_present_wrong_hashes_not_passing(self, tmp_path):
        """Both files exist but content does not match frozen commitments."""
        state_dir = tmp_path / "0. Exploration & Applicability Engine" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "identity-manifest.json").write_bytes(b"wrong content")
        (state_dir / "indexed_body.json").write_bytes(b"wrong indexed body")
        result = check_vault_hashes_with_actual_vault(vault_root=tmp_path)
        assert result["passed"] is False
        errors = result["errors"]
        assert any("mismatch" in e.lower() for e in errors)


class TestHashReverificationVaultRequired:
    """check_hash_reverification must require vault for passed=True."""

    def test_vault_absent_no_env_no_arg_makes_passed_false(self, monkeypatch):
        """Without PROJECT008_PATH or vault_root, passed must be False."""
        monkeypatch.delenv("PROJECT008_PATH", raising=False)
        result = check_hash_reverification()
        assert result["passed"] is False
        assert result["vault_pending"] is True
        assert len(result["vault_errors"]) > 0

    def test_vault_absent_sets_vault_pending_true(self, monkeypatch, tmp_path):
        """Nonexistent vault_root → vault_pending=True, passed=False."""
        monkeypatch.delenv("PROJECT008_PATH", raising=False)
        result = check_hash_reverification(vault_root=tmp_path / "no_such_vault")
        assert result["passed"] is False
        assert result["vault_pending"] is True

    def test_local_errors_still_reported_alongside_vault_errors(self, monkeypatch, tmp_path):
        """Local hash failures and vault errors both appear in their respective lists."""
        monkeypatch.delenv("PROJECT008_PATH", raising=False)
        # Pass a bogus path dict so local hashes fail too
        from readiness import _PATHS, EXPECTED_HASHES
        bad_paths = {k: tmp_path / "missing.txt" for k in _PATHS}
        result = check_hash_reverification(paths=bad_paths, vault_root=tmp_path / "no_vault")
        assert result["passed"] is False
        assert len(result["errors"]) > 0       # local failures
        assert len(result["vault_errors"]) > 0  # vault failures

    def test_vault_with_both_correct_files_makes_passed_true(self, monkeypatch, tmp_path):
        """vault_root with both files hashing correctly → passed=True, vault_pending=False."""
        import hashlib, json
        monkeypatch.delenv("PROJECT008_PATH", raising=False)

        state_dir = tmp_path / "0. Exploration & Applicability Engine" / "state"
        state_dir.mkdir(parents=True)

        from readiness import EXPECTED_HASHES, _PATHS, LOCAL_HASH_KEYS

        # Write real local files to satisfy local hashes
        import shutil
        real_paths = _PATHS
        fake_paths = {}
        for key in LOCAL_HASH_KEYS:
            src = real_paths.get(key)
            if src and Path(src).exists():
                dst = tmp_path / f"{key}.txt"
                shutil.copy(src, dst)
                fake_paths[key] = dst
            else:
                fake_paths[key] = src  # keep original — may or may not exist

        # Write vault files with correct content (content that hashes to frozen value)
        # We need files whose sha256 matches EXPECTED_HASHES exactly.
        # Since we can't reverse hashes, write placeholder content and patch expected.
        manifest_content = b"manifest_content_for_test"
        indexed_content  = b"indexed_body_content_for_test"
        manifest_sha = hashlib.sha256(manifest_content).hexdigest().upper()
        indexed_sha  = hashlib.sha256(indexed_content).hexdigest().upper()

        (state_dir / "identity-manifest.json").write_bytes(manifest_content)
        (state_dir / "indexed_body.json").write_bytes(indexed_content)

        patched_expected = dict(EXPECTED_HASHES)
        patched_expected["corpus_manifest"] = manifest_sha
        patched_expected["indexed_body"]    = indexed_sha

        result = check_hash_reverification(
            paths=fake_paths,
            expected=patched_expected,
            vault_root=tmp_path,
        )
        assert result["vault_pending"] is False
        if result["errors"]:
            pytest.skip(f"Local files not available for full pass test: {result['errors']}")
        assert result["passed"] is True

    def test_project008_path_env_used_when_no_vault_root(self, monkeypatch, tmp_path):
        """PROJECT008_PATH env var is used when vault_root not supplied."""
        monkeypatch.setenv("PROJECT008_PATH", str(tmp_path / "no_vault"))
        result = check_hash_reverification()
        assert result["passed"] is False
        assert result["vault_pending"] is True


class TestPreflightReportsInfraChecks:
    def test_infra_checks_attached_on_failure(self):
        """PreflightFailed must carry infra_checks dict — not silently discarded."""
        with pytest.raises(PreflightFailed) as exc_info:
            run_preflight()
        e = exc_info.value
        assert hasattr(e, "infra_checks"), "infra_checks not attached to PreflightFailed"
        infra = e.infra_checks
        assert isinstance(infra, dict)
        for key in ("provider_adapter", "github_actions_workflow", "custody_key",
                    "blinding_module", "pricing_lock", "vault_hashes"):
            assert key in infra, f"infra_checks missing '{key}'"

    def test_diagnostic_preflight_raises_when_r08_vault_absent(self, monkeypatch):
        """run_diagnostic_preflight() must raise DiagnosticPreflightFailed when vault absent."""
        monkeypatch.delenv("PROJECT008_PATH", raising=False)
        with pytest.raises(DiagnosticPreflightFailed) as exc_info:
            run_diagnostic_preflight()
        e = exc_info.value
        assert "R08" in e.unmet
        assert hasattr(e, "infra_checks")

    def test_diagnostic_preflight_infra_checks_present_on_failure(self, monkeypatch):
        """DiagnosticPreflightFailed carries infra_checks dict."""
        monkeypatch.delenv("PROJECT008_PATH", raising=False)
        with pytest.raises(DiagnosticPreflightFailed) as exc_info:
            run_diagnostic_preflight()
        e = exc_info.value
        assert hasattr(e, "infra_checks")
        infra = e.infra_checks
        assert isinstance(infra, dict)
        for key in ("provider_adapter", "github_actions_workflow", "custody_key",
                    "blinding_module", "pricing_lock", "vault_hashes"):
            assert key in infra, f"infra_checks missing '{key}'"
