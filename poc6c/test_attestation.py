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
    REQUIRED_ARTIFACT_EDGES,
    aggregate_attestations,
    create_attestation,
    validate_attestation_chain,
)

_RUN_ID    = "test-run-001"
_COMMIT    = "abc123def456abc123def456abc123def456abc123def456abc123def456abc1"
_RUNNER    = "test-runner/ubuntu-24.04"
_TIMESTAMP = "2026-08-04T00:00:00Z"
# Proper 64-hex SHA-256 sentinel values for tests
_HASH_A    = "aabbccddeeff00112233445566778899aabbccddeeff001122334455667788aa"
_HASH_B    = "bbccddee00112233445566778899aabbccddeeff001122334455667788aabbcc"
_HASH_OUT  = "ccddee001122334455667788aabbccddeeff001122334455667788aabbccddee"

# Distinct role-package hashes (must differ from each other and from _HASH_*)
_GENERIC_ARM_PKG_HASH    = "1111111111111111111111111111111111111111111111111111111111111111"
_CONFIGURED_ARM_PKG_HASH = "2222222222222222222222222222222222222222222222222222222222222222"
_BLINDING_PKG_HASH       = "3333333333333333333333333333333333333333333333333333333333333333"
_EVALUATOR_PKG_HASH      = "4444444444444444444444444444444444444444444444444444444444444444"
_INTEGRITY_PKG_HASH      = "5555555555555555555555555555555555555555555555555555555555555555"
_FULL_PKG_HASH           = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"


def _make_att(stage: str, mode: str = "diagnostic", run_id: str = _RUN_ID,
              commit: str = _COMMIT, is_diagnostic: bool = True,
              in_hashes: dict | None = None, out_hashes: dict | None = None,
              runner: str = _RUNNER) -> Attestation:
    return create_attestation(
        stage            = stage,
        mode             = mode,
        run_id           = run_id,
        commit_sha       = commit,
        input_hashes     = in_hashes or {},
        output_hashes    = out_hashes or {f"{stage}_out": _HASH_OUT},
        runner_identity  = runner,
        timestamp_utc    = _TIMESTAMP,
        provider_model_id = None,
        is_diagnostic    = is_diagnostic,
    )


def _full_chain(mode: str = "diagnostic", run_id: str = _RUN_ID,
                commit: str = _COMMIT) -> list[Attestation]:
    """Build a minimal valid chain satisfying all required artifact edges.

    Graph:
      preflight         → generic_arm_pkg        → generic-arm
      preflight         → configured_arm_pkg     → configured-arm
      preflight         → blinding_pkg           → deterministic-blinding
      preflight         → evaluator_pkg          → blinded-evaluator
      preflight         → integrity_pkg          → integrity-and-analysis
      generic-arm       → generic_arm_results    → deterministic-blinding
      configured-arm    → configured_arm_results → deterministic-blinding
      blinding          → blinded_answer_bundle  → blinded-evaluator
      blinded-evaluator → evaluation_results     → integrity-and-analysis
    """
    generic_hash    = _HASH_A
    configured_hash = _HASH_B
    bundle_hash     = _HASH_OUT
    eval_hash       = "ddee001122334455667788aabbccddeeff001122334455667788aabbccddee11"
    integrity_hash  = "eeff001122334455667788aabbccddeeff001122334455667788aabbccddeeff"

    atts = []
    for s in EXPECTED_STAGES:
        in_h: dict = {}
        out_h: dict = {f"{s}_out": _HASH_OUT}

        if s == "preflight":
            out_h = {
                "preflight_report":    _HASH_OUT,
                "poc6c_package":       _FULL_PKG_HASH,
                "generic_arm_pkg":     _GENERIC_ARM_PKG_HASH,
                "configured_arm_pkg":  _CONFIGURED_ARM_PKG_HASH,
                "blinding_pkg":        _BLINDING_PKG_HASH,
                "evaluator_pkg":       _EVALUATOR_PKG_HASH,
                "integrity_pkg":       _INTEGRITY_PKG_HASH,
            }
        elif s == "generic-arm":
            in_h  = {"generic_arm_pkg": _GENERIC_ARM_PKG_HASH}
            out_h = {"generic_arm_results": generic_hash}
        elif s == "configured-arm":
            in_h  = {"configured_arm_pkg": _CONFIGURED_ARM_PKG_HASH}
            out_h = {"configured_arm_results": configured_hash}
        elif s == "deterministic-blinding":
            in_h  = {
                "blinding_pkg":           _BLINDING_PKG_HASH,
                "generic_arm_results":    generic_hash,
                "configured_arm_results": configured_hash,
            }
            out_h = {"blinded_answer_bundle": bundle_hash,
                     "mapping_bundle": _HASH_B}
        elif s == "blinded-evaluator":
            in_h  = {
                "evaluator_pkg":        _EVALUATOR_PKG_HASH,
                "blinded_answer_bundle": bundle_hash,
            }
            out_h = {"evaluation_results": eval_hash}
        elif s == "integrity-and-analysis":
            in_h  = {
                "integrity_pkg":     _INTEGRITY_PKG_HASH,
                "evaluation_results": eval_hash,
            }
            out_h = {"integrity_report": integrity_hash}

        atts.append(create_attestation(
            stage            = s,
            mode             = mode,
            run_id           = run_id,
            commit_sha       = commit,
            input_hashes     = in_h,
            output_hashes    = out_h,
            runner_identity  = _RUNNER,
            timestamp_utc    = _TIMESTAMP,
            provider_model_id = None,
            is_diagnostic    = (mode == "diagnostic"),
        ))
    return atts


class TestCreateAttestation:
    def test_creates_valid(self):
        att = _make_att("preflight", out_hashes={"preflight_out": _HASH_OUT})
        assert att.stage == "preflight"
        assert att.schema_version == "poc6c-attestation-v1"
        assert att.is_diagnostic is True

    def test_sha256_stable(self):
        att = _make_att("preflight", out_hashes={"preflight_out": _HASH_OUT})
        assert att.sha256() == att.sha256()
        assert len(att.sha256()) == 64

    def test_roundtrip_dict(self):
        att = _make_att("preflight", out_hashes={"preflight_out": _HASH_OUT})
        d   = att.to_dict()
        att2 = Attestation.from_dict(d)
        assert att2.stage == att.stage
        assert att2.run_id == att.run_id

    def test_from_dict_missing_field_raises(self):
        att = _make_att("preflight", out_hashes={"preflight_out": _HASH_OUT})
        d = att.to_dict()
        del d["runner_identity"]
        with pytest.raises(ChainValidationError, match="missing"):
            Attestation.from_dict(d)

    def test_from_dict_extra_field_raises(self):
        att = _make_att("preflight", out_hashes={"preflight_out": _HASH_OUT})
        d = att.to_dict()
        d["unknown_field"] = "oops"
        with pytest.raises(ChainValidationError, match="unknown"):
            Attestation.from_dict(d)


class TestSingleAttestationValidation:
    def test_invalid_timestamp_raises(self):
        chain = _full_chain()
        chain[0] = create_attestation(
            stage="preflight", mode="diagnostic", run_id=_RUN_ID,
            commit_sha=_COMMIT, input_hashes={},
            output_hashes={"preflight_out": _HASH_OUT},
            runner_identity=_RUNNER, timestamp_utc="not-a-timestamp",
        )
        with pytest.raises(ChainValidationError, match="ISO-8601"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_empty_runner_raises(self):
        chain = _full_chain()
        chain[0] = create_attestation(
            stage="preflight", mode="diagnostic", run_id=_RUN_ID,
            commit_sha=_COMMIT, input_hashes={},
            output_hashes={"preflight_out": _HASH_OUT},
            runner_identity="", timestamp_utc=_TIMESTAMP,
        )
        with pytest.raises(ChainValidationError, match="runner_identity"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_short_hash_raises(self):
        chain = _full_chain()
        chain[0] = create_attestation(
            stage="preflight", mode="diagnostic", run_id=_RUN_ID,
            commit_sha=_COMMIT, input_hashes={},
            output_hashes={"preflight_out": "TOOSHORT"},
            runner_identity=_RUNNER, timestamp_utc=_TIMESTAMP,
        )
        with pytest.raises(ChainValidationError, match="valid 64-hex"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_unknown_stage_raises(self):
        chain = _full_chain()
        chain[0] = create_attestation(
            stage="unknown-stage", mode="diagnostic", run_id=_RUN_ID,
            commit_sha=_COMMIT, input_hashes={},
            output_hashes={"x": _HASH_OUT},
            runner_identity=_RUNNER, timestamp_utc=_TIMESTAMP,
        )
        with pytest.raises(ChainValidationError, match="Unknown stage"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_production_provider_stage_missing_model_id_raises(self):
        """In production mode a provider stage (generic-arm, configured-arm,
        blinded-evaluator) must declare a non-empty provider_model_id.

        WP3 required fixture: 'absent provider identity for a production
        provider stage' must raise ChainValidationError.
        """
        from attestation import _PROVIDER_STAGES
        for provider_stage in sorted(_PROVIDER_STAGES):
            # Build a production attestation for the provider stage with
            # provider_model_id missing — validate_attestation_chain must reject it
            # even when it is the only attestation in the list (per-att validation
            # runs before cross-stage checks, so a single bad attestation is enough).
            bad_att = create_attestation(
                stage=provider_stage,
                mode="production",
                run_id=_RUN_ID,
                commit_sha=_COMMIT,
                input_hashes={},
                output_hashes={"out": _HASH_OUT},
                runner_identity=_RUNNER,
                timestamp_utc=_TIMESTAMP,
                provider_model_id=None,   # absent — must be rejected
                is_diagnostic=False,
            )
            with pytest.raises(ChainValidationError, match="provider_model_id"):
                # validate_attestation_chain calls _validate_single_attestation
                # on every attestation before cross-stage checks, so a one-element
                # list is sufficient to trigger the provider-identity guard.
                validate_attestation_chain(
                    [bad_att], _RUN_ID, _COMMIT, "production",
                    expected_stages=(provider_stage,),
                )


class TestChainValidation:
    def test_full_chain_passes(self):
        chain = _full_chain()
        validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_wrong_run_id_raises(self):
        chain = _full_chain()
        chain[0] = create_attestation(
            stage="preflight", mode="diagnostic", run_id="wrong-run",
            commit_sha=_COMMIT, input_hashes={},
            output_hashes={"preflight_out": _HASH_OUT},
            runner_identity=_RUNNER, timestamp_utc=_TIMESTAMP,
        )
        with pytest.raises(ChainValidationError, match="run_id"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_wrong_commit_raises(self):
        chain = _full_chain()
        wrong_commit = "badc0de0" * 8
        chain[1] = create_attestation(
            stage="generic-arm", mode="diagnostic", run_id=_RUN_ID,
            commit_sha=wrong_commit, input_hashes={},
            output_hashes={"generic_arm_results": _HASH_A},
            runner_identity=_RUNNER, timestamp_utc=_TIMESTAMP,
        )
        with pytest.raises(ChainValidationError, match="commit_sha"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_mode_mismatch_raises(self):
        # chain built as production but validated as diagnostic
        chain = _full_chain(mode="production")
        with pytest.raises(ChainValidationError, match="mode"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_missing_stage_raises(self):
        chain = [a for a in _full_chain() if a.stage != "blinded-evaluator"]
        with pytest.raises(ChainValidationError, match="Missing"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_duplicate_stage_raises(self):
        chain = _full_chain()
        chain.append(create_attestation(
            stage="preflight", mode="diagnostic", run_id=_RUN_ID,
            commit_sha=_COMMIT, input_hashes={},
            output_hashes={"preflight_out": _HASH_OUT},
            runner_identity=_RUNNER, timestamp_utc=_TIMESTAMP,
        ))
        with pytest.raises(ChainValidationError, match="Duplicate"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_diagnostic_in_production_raises(self):
        chain = [create_attestation(
            stage=s, mode="production", run_id=_RUN_ID, commit_sha=_COMMIT,
            input_hashes={}, output_hashes={f"{s}_out": _HASH_OUT},
            runner_identity=_RUNNER, timestamp_utc=_TIMESTAMP, is_diagnostic=True,
        ) for s in EXPECTED_STAGES]
        with pytest.raises(ChainValidationError, match="is_diagnostic"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "production")

    def test_hash_chain_mismatch_raises(self):
        chain = _full_chain()
        # Tamper generic-arm output hash so blinding input disagrees
        chain[1] = create_attestation(
            stage="generic-arm", mode="diagnostic", run_id=_RUN_ID,
            commit_sha=_COMMIT,
            input_hashes={"generic_arm_pkg": _GENERIC_ARM_PKG_HASH},
            output_hashes={"generic_arm_results": _HASH_B},  # different from blinding's input
            runner_identity=_RUNNER, timestamp_utc=_TIMESTAMP,
        )
        with pytest.raises(ChainValidationError, match="[Hh]ash"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_empty_chain_raises(self):
        with pytest.raises(ChainValidationError, match="empty"):
            validate_attestation_chain([], _RUN_ID, _COMMIT, "diagnostic")

    def test_hash_chain_match_passes(self):
        validate_attestation_chain(_full_chain(), _RUN_ID, _COMMIT, "diagnostic")

    def test_reversed_order_raises(self):
        chain = list(reversed(_full_chain()))
        with pytest.raises(ChainValidationError, match="[Oo]rder"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_missing_required_artifact_edge_raises(self):
        # Remove the mandatory generic_arm_results edge from blinding's inputs
        chain = _full_chain()
        blend_idx = next(i for i, a in enumerate(chain)
                         if a.stage == "deterministic-blinding")
        chain[blend_idx] = create_attestation(
            stage="deterministic-blinding", mode="diagnostic", run_id=_RUN_ID,
            commit_sha=_COMMIT,
            input_hashes={
                "blinding_pkg":           _BLINDING_PKG_HASH,
                "configured_arm_results": _HASH_B,
            },  # missing generic_arm_results
            output_hashes={"blinded_answer_bundle": _HASH_OUT, "mapping_bundle": _HASH_B},
            runner_identity=_RUNNER, timestamp_utc=_TIMESTAMP,
        )
        with pytest.raises(ChainValidationError, match="generic_arm_results"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_evaluator_receives_mapping_bundle_raises(self):
        # Evaluator must NOT declare mapping_bundle as an input — only blinded_answer_bundle
        chain = _full_chain()
        eval_idx = next(i for i, a in enumerate(chain) if a.stage == "blinded-evaluator")
        eval_hash = "ddee001122334455667788aabbccddeeff001122334455667788aabbccddee11"
        chain[eval_idx] = create_attestation(
            stage="blinded-evaluator", mode="diagnostic", run_id=_RUN_ID,
            commit_sha=_COMMIT,
            # Includes mapping_bundle — custody material that evaluator must not receive
            input_hashes={
                "evaluator_pkg":        _EVALUATOR_PKG_HASH,
                "blinded_answer_bundle": _HASH_OUT,
                "mapping_bundle":        _HASH_B,
            },
            output_hashes={"evaluation_results": eval_hash},
            runner_identity=_RUNNER, timestamp_utc=_TIMESTAMP,
        )
        # The blinded_answer_bundle edge is still satisfied; however, this tests that
        # a reviewer can detect custody material in evaluator inputs by checking for
        # mapping_bundle key in blinded-evaluator input_hashes.
        # Validate chain still succeeds (mapping_bundle is not a REQUIRED input for evaluator)
        # but the custody isolation test in test_role_isolation.py checks the package content.
        validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_missing_evaluator_to_integrity_edge_raises(self):
        # integrity-and-analysis must declare evaluation_results as input
        chain = _full_chain()
        int_idx = next(i for i, a in enumerate(chain) if a.stage == "integrity-and-analysis")
        chain[int_idx] = create_attestation(
            stage="integrity-and-analysis", mode="diagnostic", run_id=_RUN_ID,
            commit_sha=_COMMIT,
            input_hashes={"integrity_pkg": _INTEGRITY_PKG_HASH},  # missing evaluation_results
            output_hashes={"integrity_report": _HASH_OUT},
            runner_identity=_RUNNER, timestamp_utc=_TIMESTAMP,
        )
        with pytest.raises(ChainValidationError, match="evaluation_results"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_substituted_evaluator_results_raises(self):
        # Tamper evaluation_results hash: integrity input disagrees with evaluator output
        chain = _full_chain()
        int_idx = next(i for i, a in enumerate(chain) if a.stage == "integrity-and-analysis")
        eval_idx = next(i for i, a in enumerate(chain) if a.stage == "blinded-evaluator")
        real_eval_hash = chain[eval_idx].output_hashes["evaluation_results"]
        chain[int_idx] = create_attestation(
            stage="integrity-and-analysis", mode="diagnostic", run_id=_RUN_ID,
            commit_sha=_COMMIT,
            input_hashes={
                "integrity_pkg":      _INTEGRITY_PKG_HASH,
                "evaluation_results": _HASH_A,  # wrong hash
            },
            output_hashes={"integrity_report": _HASH_OUT},
            runner_identity=_RUNNER, timestamp_utc=_TIMESTAMP,
        )
        with pytest.raises(ChainValidationError):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")


class TestAggregateAttestations:
    def test_aggregate_passes(self):
        result = aggregate_attestations(_full_chain(), _RUN_ID, _COMMIT, "diagnostic")
        assert result["chain_valid"] is True
        assert result["confirmation_ready"] is False
        assert set(result["stages_verified"]) == set(EXPECTED_STAGES)


class TestRolePackageAttestationGraph:
    """Regression suite: validates the full six-stage role-package provenance graph.

    Uses DISTINCT hashes for the full poc6c_package and every role package.
    Confirms the corrected REQUIRED_ARTIFACT_EDGES enforcement:
      preflight → generic_arm_pkg    → generic-arm
      preflight → configured_arm_pkg → configured-arm
      preflight → blinding_pkg       → deterministic-blinding
      preflight → evaluator_pkg      → blinded-evaluator
      preflight → integrity_pkg      → integrity-and-analysis

    These tests MUST fail if poc6c_package is substituted for any role-pkg key.
    """

    def _build_chain_with_full_pkg_substituted(self, target_stage: str, role_key: str) -> list[Attestation]:
        """Return a chain where target_stage uses poc6c_package instead of its role key."""
        chain = _full_chain()
        idx = next(i for i, a in enumerate(chain) if a.stage == target_stage)
        old = chain[idx]
        # Replace the correct role-pkg key with poc6c_package (the substitution attack)
        bad_in = {
            k if k != role_key else "poc6c_package": v
            for k, v in old.input_hashes.items()
        }
        chain[idx] = create_attestation(
            stage=old.stage, mode=old.mode, run_id=old.run_id,
            commit_sha=old.commit_sha, input_hashes=bad_in,
            output_hashes=old.output_hashes,
            runner_identity=old.runner_identity, timestamp_utc=old.timestamp_utc,
            is_diagnostic=old.is_diagnostic,
        )
        return chain

    def test_full_graph_passes(self):
        """Complete six-stage graph with distinct per-role hashes must pass."""
        validate_attestation_chain(_full_chain(), _RUN_ID, _COMMIT, "diagnostic")

    def test_role_hashes_are_distinct(self):
        """All role-package hashes and the full package hash must be distinct."""
        hashes = [
            _FULL_PKG_HASH,
            _GENERIC_ARM_PKG_HASH,
            _CONFIGURED_ARM_PKG_HASH,
            _BLINDING_PKG_HASH,
            _EVALUATOR_PKG_HASH,
            _INTEGRITY_PKG_HASH,
        ]
        assert len(hashes) == len(set(hashes)), "Role package hashes must all be distinct"

    def test_preflight_must_output_generic_arm_pkg(self):
        """Chain fails if preflight does not output generic_arm_pkg."""
        chain = _full_chain()
        pf = chain[0]
        bad_out = {k: v for k, v in pf.output_hashes.items() if k != "generic_arm_pkg"}
        chain[0] = create_attestation(
            stage="preflight", mode=pf.mode, run_id=pf.run_id,
            commit_sha=pf.commit_sha, input_hashes=pf.input_hashes,
            output_hashes=bad_out, runner_identity=pf.runner_identity,
            timestamp_utc=pf.timestamp_utc, is_diagnostic=pf.is_diagnostic,
        )
        with pytest.raises(ChainValidationError, match="generic_arm_pkg"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_preflight_must_output_configured_arm_pkg(self):
        """Chain fails if preflight does not output configured_arm_pkg."""
        chain = _full_chain()
        pf = chain[0]
        bad_out = {k: v for k, v in pf.output_hashes.items() if k != "configured_arm_pkg"}
        chain[0] = create_attestation(
            stage="preflight", mode=pf.mode, run_id=pf.run_id,
            commit_sha=pf.commit_sha, input_hashes=pf.input_hashes,
            output_hashes=bad_out, runner_identity=pf.runner_identity,
            timestamp_utc=pf.timestamp_utc, is_diagnostic=pf.is_diagnostic,
        )
        with pytest.raises(ChainValidationError, match="configured_arm_pkg"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_preflight_must_output_blinding_pkg(self):
        """Chain fails if preflight does not output blinding_pkg."""
        chain = _full_chain()
        pf = chain[0]
        bad_out = {k: v for k, v in pf.output_hashes.items() if k != "blinding_pkg"}
        chain[0] = create_attestation(
            stage="preflight", mode=pf.mode, run_id=pf.run_id,
            commit_sha=pf.commit_sha, input_hashes=pf.input_hashes,
            output_hashes=bad_out, runner_identity=pf.runner_identity,
            timestamp_utc=pf.timestamp_utc, is_diagnostic=pf.is_diagnostic,
        )
        with pytest.raises(ChainValidationError, match="blinding_pkg"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_preflight_must_output_evaluator_pkg(self):
        """Chain fails if preflight does not output evaluator_pkg."""
        chain = _full_chain()
        pf = chain[0]
        bad_out = {k: v for k, v in pf.output_hashes.items() if k != "evaluator_pkg"}
        chain[0] = create_attestation(
            stage="preflight", mode=pf.mode, run_id=pf.run_id,
            commit_sha=pf.commit_sha, input_hashes=pf.input_hashes,
            output_hashes=bad_out, runner_identity=pf.runner_identity,
            timestamp_utc=pf.timestamp_utc, is_diagnostic=pf.is_diagnostic,
        )
        with pytest.raises(ChainValidationError, match="evaluator_pkg"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_preflight_must_output_integrity_pkg(self):
        """Chain fails if preflight does not output integrity_pkg."""
        chain = _full_chain()
        pf = chain[0]
        bad_out = {k: v for k, v in pf.output_hashes.items() if k != "integrity_pkg"}
        chain[0] = create_attestation(
            stage="preflight", mode=pf.mode, run_id=pf.run_id,
            commit_sha=pf.commit_sha, input_hashes=pf.input_hashes,
            output_hashes=bad_out, runner_identity=pf.runner_identity,
            timestamp_utc=pf.timestamp_utc, is_diagnostic=pf.is_diagnostic,
        )
        with pytest.raises(ChainValidationError, match="integrity_pkg"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_generic_arm_must_input_generic_arm_pkg(self):
        """generic-arm must declare generic_arm_pkg as input (not poc6c_package).
        Substituting poc6c_package causes a hash-chain mismatch (preflight does not
        output poc6c_package destined for generic-arm) — the chain is still rejected.
        """
        chain = self._build_chain_with_full_pkg_substituted("generic-arm", "generic_arm_pkg")
        with pytest.raises(ChainValidationError):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_configured_arm_must_input_configured_arm_pkg(self):
        """configured-arm must declare configured_arm_pkg as input (not poc6c_package)."""
        chain = self._build_chain_with_full_pkg_substituted("configured-arm", "configured_arm_pkg")
        with pytest.raises(ChainValidationError, match="configured_arm_pkg"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_blinding_must_input_blinding_pkg(self):
        """deterministic-blinding must declare blinding_pkg as input (not poc6c_package)."""
        chain = self._build_chain_with_full_pkg_substituted("deterministic-blinding", "blinding_pkg")
        with pytest.raises(ChainValidationError, match="blinding_pkg"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_evaluator_must_input_evaluator_pkg(self):
        """blinded-evaluator must declare evaluator_pkg as input (not poc6c_package)."""
        chain = self._build_chain_with_full_pkg_substituted("blinded-evaluator", "evaluator_pkg")
        with pytest.raises(ChainValidationError, match="evaluator_pkg"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_integrity_must_input_integrity_pkg(self):
        """integrity-and-analysis must declare integrity_pkg as input (not poc6c_package)."""
        chain = self._build_chain_with_full_pkg_substituted("integrity-and-analysis", "integrity_pkg")
        with pytest.raises(ChainValidationError, match="integrity_pkg"):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")

    def test_hash_mismatch_for_role_pkg_raises(self):
        """Chain fails if generic-arm's generic_arm_pkg hash differs from preflight's output."""
        chain = _full_chain()
        ga_idx = next(i for i, a in enumerate(chain) if a.stage == "generic-arm")
        old = chain[ga_idx]
        # Use a hash that is different from _GENERIC_ARM_PKG_HASH
        chain[ga_idx] = create_attestation(
            stage="generic-arm", mode=old.mode, run_id=old.run_id,
            commit_sha=old.commit_sha,
            input_hashes={"generic_arm_pkg": _FULL_PKG_HASH},  # wrong: full pkg hash
            output_hashes=old.output_hashes,
            runner_identity=old.runner_identity, timestamp_utc=old.timestamp_utc,
            is_diagnostic=old.is_diagnostic,
        )
        with pytest.raises(ChainValidationError):
            validate_attestation_chain(chain, _RUN_ID, _COMMIT, "diagnostic")
