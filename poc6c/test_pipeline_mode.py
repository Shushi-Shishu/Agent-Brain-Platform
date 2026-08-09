"""Tests for pipeline_mode.py (T4B-01)."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from pipeline_mode import PipelineMode, InvalidMode, validate_mode


class TestValidateMode:
    def test_diagnostic_valid(self):
        assert validate_mode("diagnostic") == PipelineMode.DIAGNOSTIC

    def test_production_valid(self):
        assert validate_mode("production") == PipelineMode.PRODUCTION

    def test_case_insensitive(self):
        assert validate_mode("DIAGNOSTIC") == PipelineMode.DIAGNOSTIC
        assert validate_mode("Production") == PipelineMode.PRODUCTION

    def test_none_raises(self):
        with pytest.raises(InvalidMode):
            validate_mode(None)

    def test_empty_raises(self):
        with pytest.raises(InvalidMode):
            validate_mode("")

    def test_whitespace_raises(self):
        with pytest.raises(InvalidMode):
            validate_mode("   ")

    def test_unknown_raises(self):
        with pytest.raises(InvalidMode):
            validate_mode("staging")

    def test_unknown_dry_run_raises(self):
        with pytest.raises(InvalidMode):
            validate_mode("dry_run")

    def test_mode_enum_values(self):
        assert PipelineMode.DIAGNOSTIC.value == "diagnostic"
        assert PipelineMode.PRODUCTION.value == "production"
        assert len(PipelineMode) == 2


class TestDiagnosticPreflight:
    def test_diagnostic_preflight_passes_with_skip_vault(self):
        """run_diagnostic_preflight(skip_r08_vault=True) must succeed in synthetic context."""
        from readiness import run_diagnostic_preflight
        matrix, infra = run_diagnostic_preflight(skip_r08_vault=True)
        assert matrix is not None
        assert infra is not None
        assert isinstance(infra, dict)
        for key in ("provider_adapter", "github_actions_workflow", "custody_key",
                    "blinding_module", "pricing_lock", "vault_hashes"):
            assert key in infra

    def test_diagnostic_preflight_raises_without_vault(self):
        """run_diagnostic_preflight() without skip_r08_vault raises when vault absent."""
        import os
        from readiness import run_diagnostic_preflight, DiagnosticPreflightFailed
        # Remove PROJECT008_PATH if set so vault is truly absent
        old = os.environ.pop("PROJECT008_PATH", None)
        try:
            with pytest.raises(DiagnosticPreflightFailed) as exc_info:
                run_diagnostic_preflight()
            assert "R08" in exc_info.value.unmet
        finally:
            if old is not None:
                os.environ["PROJECT008_PATH"] = old

    def test_production_preflight_always_fails(self):
        """run_preflight() must raise PreflightFailed because R01-R05 are blocked."""
        from readiness import run_preflight, PreflightFailed
        with pytest.raises(PreflightFailed) as exc_info:
            run_preflight()
        e = exc_info.value
        # Must report R01-R05 in unmet
        assert any(r in e.unmet for r in ("R01", "R02", "R03", "R04", "R05"))
        # Infra checks must be attached to exception
        assert hasattr(e, "infra_checks")
        assert isinstance(e.infra_checks, dict)

    def test_production_preflight_infra_checks_not_discarded(self):
        """Infrastructure check results must be on the exception, not silently dropped."""
        from readiness import run_preflight, PreflightFailed
        with pytest.raises(PreflightFailed) as exc_info:
            run_preflight()
        infra = exc_info.value.infra_checks
        assert "provider_adapter" in infra
        assert "vault_hashes" in infra
