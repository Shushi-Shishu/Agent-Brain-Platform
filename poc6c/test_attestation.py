"""Tests for attestation.py (T4B-02)."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from attestation import (
    Attestation,
    ChainValidationError,
    EXPECTED_STAGES,
    aggregate_attestations,
    create_attestation,
    validate_attestation_chain,
)

_RUN_ID    = "test-run-001"
_COMMIT    = "abc123def456"
_RUNNER    = "test-runner"
_TIMESTAMP = "2026-08-04T00:00:00Z"


def _make_att(stage: str, mode: str = "diagnostic", run_id: str = _RUN_ID,
              commit: str = _COMMIT, is_diagnostic: bool = True,
              in_hashes: dict | None = None, out_hashes: dict | None = None) -> Attestation:
    return create_attestation(
        stage            = stage,
        mode             = mode,
        run_id           = run_id,
        commit_sha       = commit,
        input_hashes     = in_hashes or {},
        output_hashes    = out_hashes or {f"{stage}_out": "AABBCC"},
        runner_identity  = _RUNNER,
        timestamp_utc    = _TIMESTAMP,
        provider_model_id = None,
        is_diagnostic    = is_diagnostic,
    )


def _full_chain(mode: str = "diagnostic", run_id: str = _RUN_ID,
                commit: str = _COMMIT) -> list[Attestation]:
    return [_make_att(s, mode=mode, run_id=run_id, commit=commit,
                      is_diagnostic=(mode == "diagnostic"))
            for s in EXPECTED_STAGES]


class TestCreateAttestation:
    def test_creates_valid(self):
        att = _make_att("preflight")
        assert att.stage == "preflight"
        assert att.schema_version == "poc6c-attestation-v1"
        assert att.is_diagnostic is True

    def test_sha256_stable(self):
        att = _make_att("preflight")
        assert att.sha256() == att.sha256()
        assert len(att.sha256()) == 64

    def test_roundtrip_dict(self):
        att = _make_att("preflight")
        d   = att.to_dict()
        att2 = Attestation.from_dict(d)
        assert att2.stage == att.stage
        assert att2.run_id == att.run_id


class TestChainValidation:
    def test_full_chain_passes(self):
        chain = _full_chain()
        validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_wrong_run_id_raises(self):
        chain = _full_chain()
        chain[0] = _make_att(chain[0].stage, run_id="wrong-run")
        with pytest.raises(ChainValidationError, match="run_id"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_wrong_commit_raises(self):
        chain = _full_chain()
        chain[1] = _make_att(chain[1].stage, commit="badc0de")
        with pytest.raises(ChainValidationError, match="commit_sha"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_mode_mismatch_raises(self):
        chain = _full_chain(mode="production")
        with pytest.raises(ChainValidationError, match="mode"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_missing_stage_raises(self):
        chain = [a for a in _full_chain() if a.stage != "blinded-evaluator"]
        with pytest.raises(ChainValidationError, match="Missing"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_duplicate_stage_raises(self):
        chain = _full_chain()
        chain.append(_make_att("preflight"))
        with pytest.raises(ChainValidationError, match="Duplicate"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_diagnostic_in_production_raises(self):
        # diagnostic attestations must not appear in a production chain
        chain = [_make_att(s, mode="production", is_diagnostic=True)
                 for s in EXPECTED_STAGES]
        with pytest.raises(ChainValidationError, match="is_diagnostic"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "production")

    def test_hash_chain_mismatch_raises(self):
        chain = _full_chain()
        # stage 0 output key matches stage 1 input key but hashes differ
        chain[0] = _make_att(
            EXPECTED_STAGES[0],
            out_hashes={"shared_artifact": "HASH_A"},
        )
        chain[1] = _make_att(
            EXPECTED_STAGES[1],
            in_hashes={"shared_artifact": "HASH_B"},
            out_hashes={},
        )
        with pytest.raises(ChainValidationError, match="Hash mismatch"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_empty_chain_raises(self):
        with pytest.raises(ChainValidationError, match="empty"):
            validate_attestation_chain([], _RUN_ID, _COMMIT, "diagnostic")

    def test_hash_chain_match_passes(self):
        chain = _full_chain()
        chain[0] = _make_att(EXPECTED_STAGES[0], out_hashes={"shared": "SAME"})
        chain[1] = _make_att(EXPECTED_STAGES[1], in_hashes={"shared": "SAME"}, out_hashes={})
        validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")


class TestAggregateAttestations:
    def test_aggregate_passes(self):
        result = aggregate_attestations(_full_chain(), _RUN_ID, _COMMIT, "diagnostic")
        assert result["chain_valid"] is True
        assert result["confirmation_ready"] is False
        assert set(result["stages_verified"]) == set(EXPECTED_STAGES)
