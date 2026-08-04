"""
Extended readiness tests for T4B-04 findings.

Covers:
- R08 vault-absent is not passing when vault path unconfigured
- R08 requires both corpus_manifest AND indexed_body
- No hardcoded developer vault path
- run_preflight() reports infra checks (not discarded)
"""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from readiness import (
    check_vault_hashes_with_actual_vault,
    run_preflight,
    run_diagnostic_preflight,
    PreflightFailed,
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

    def test_diagnostic_preflight_returns_infra_checks(self):
        """run_diagnostic_preflight() must return infra checks in second tuple element."""
        matrix, infra = run_diagnostic_preflight()
        assert infra is not None
        assert "provider_adapter" in infra
        assert "vault_hashes" in infra
