"""
Distributed attestation schema and chain validation for POC 6c.

Each pipeline stage produces an Attestation recording only the facts it can
observe.  The final integrity job aggregates attestations and verifies the
chain — no single stage can declare the whole run ready.

Stage names (in order):
  preflight | generic-arm | configured-arm | deterministic-blinding |
  blinded-evaluator | integrity-and-analysis
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from typing import Any

SCHEMA_VERSION = "poc6c-attestation-v1"

EXPECTED_STAGES = (
    "preflight",
    "generic-arm",
    "configured-arm",
    "deterministic-blinding",
    "blinded-evaluator",
    "integrity-and-analysis",
)

_ALLOWED_STAGES = set(EXPECTED_STAGES)
_ALLOWED_MODES = {"diagnostic", "production"}

# Provider stages that must have provider_model_id set in production
_PROVIDER_STAGES = {"generic-arm", "configured-arm", "blinded-evaluator"}

# ISO-8601 UTC timestamp pattern (strict: YYYY-MM-DDTHH:MM:SSZ)
_ISO8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

# SHA-256 hex pattern (64 lowercase or uppercase hex chars)
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")

# Mandatory artifact edges: each entry is (output_stage, artifact_key, input_stage)
# The blinding stage must receive both arm outputs.
# The evaluator receives the blinded_answer_bundle only — never the mapping_bundle.
# The integrity stage must receive the evaluation_results digest.
REQUIRED_ARTIFACT_EDGES: tuple[tuple[str, str, str], ...] = (
    ("generic-arm",            "generic_arm_results",    "deterministic-blinding"),
    ("configured-arm",         "configured_arm_results", "deterministic-blinding"),
    ("deterministic-blinding", "blinded_answer_bundle",  "blinded-evaluator"),
    ("blinded-evaluator",      "evaluation_results",     "integrity-and-analysis"),
)


class ChainValidationError(RuntimeError):
    """Raised when the attestation chain is invalid."""


@dataclasses.dataclass
class Attestation:
    """Auditable record of facts observed by a single pipeline stage."""
    schema_version:      str
    stage:               str
    mode:                str               # "diagnostic" | "production"
    run_id:              str
    commit_sha:          str
    input_hashes:        dict[str, str]    # artifact_name → sha256(hex)
    output_hashes:       dict[str, str]    # artifact_name → sha256(hex)
    runner_identity:     str               # e.g. "github-actions/ubuntu-24.04"
    timestamp_utc:       str               # ISO-8601 strict: YYYY-MM-DDTHH:MM:SSZ
    provider_model_id:   str | None        # None for non-API stages
    is_diagnostic:       bool

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Attestation":
        _FIELDS = {f.name for f in dataclasses.fields(cls)}
        missing = _FIELDS - set(d.keys())
        extra = set(d.keys()) - _FIELDS
        if missing:
            raise ChainValidationError(
                f"Attestation dict missing required fields: {sorted(missing)}."
            )
        if extra:
            raise ChainValidationError(
                f"Attestation dict has unknown fields: {sorted(extra)}."
            )
        return cls(**{k: v for k, v in d.items() if k in _FIELDS})

    def sha256(self) -> str:
        """Stable content hash of this attestation (for chaining)."""
        serialised = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialised.encode("utf-8")).hexdigest().upper()


def _validate_single_attestation(att: Attestation, mode: str) -> None:
    """Strict per-attestation field validation."""
    if att.schema_version != SCHEMA_VERSION:
        raise ChainValidationError(
            f"Stage '{att.stage}' schema_version '{att.schema_version}' "
            f"!= expected '{SCHEMA_VERSION}'."
        )
    if att.stage not in _ALLOWED_STAGES:
        raise ChainValidationError(
            f"Unknown stage '{att.stage}'. Allowed: {sorted(_ALLOWED_STAGES)}."
        )
    if att.mode not in _ALLOWED_MODES:
        raise ChainValidationError(
            f"Stage '{att.stage}' mode '{att.mode}' not in {sorted(_ALLOWED_MODES)}."
        )
    if not att.run_id or not att.run_id.strip():
        raise ChainValidationError(
            f"Stage '{att.stage}' has empty run_id."
        )
    if not att.commit_sha or not att.commit_sha.strip():
        raise ChainValidationError(
            f"Stage '{att.stage}' has empty commit_sha."
        )
    if not att.runner_identity or not att.runner_identity.strip():
        raise ChainValidationError(
            f"Stage '{att.stage}' has empty runner_identity."
        )
    if not _ISO8601_RE.match(att.timestamp_utc or ""):
        raise ChainValidationError(
            f"Stage '{att.stage}' timestamp_utc '{att.timestamp_utc}' is not "
            "strict ISO-8601 UTC (YYYY-MM-DDTHH:MM:SSZ)."
        )
    # Validate hash values are proper SHA-256 hex strings (when non-empty)
    for artifact, h in {**att.input_hashes, **att.output_hashes}.items():
        if h and not _SHA256_RE.match(h):
            raise ChainValidationError(
                f"Stage '{att.stage}' artifact '{artifact}' hash '{h[:16]}…' "
                "is not a valid 64-hex SHA-256 value."
            )
    # Production chains must not contain diagnostic attestations
    if mode == "production" and att.is_diagnostic:
        raise ChainValidationError(
            f"Stage '{att.stage}' carries is_diagnostic=True in a production chain."
        )
    # Production provider stages must declare provider_model_id
    if mode == "production" and att.stage in _PROVIDER_STAGES:
        if not att.provider_model_id or not att.provider_model_id.strip():
            raise ChainValidationError(
                f"Stage '{att.stage}' in production mode must declare "
                "provider_model_id (non-empty)."
            )


def create_attestation(
    stage: str,
    mode: str,
    run_id: str,
    commit_sha: str,
    input_hashes: dict[str, str],
    output_hashes: dict[str, str],
    runner_identity: str,
    timestamp_utc: str,
    provider_model_id: str | None = None,
    is_diagnostic: bool = False,
) -> Attestation:
    return Attestation(
        schema_version   = SCHEMA_VERSION,
        stage            = stage,
        mode             = mode,
        run_id           = run_id,
        commit_sha       = commit_sha,
        input_hashes     = input_hashes,
        output_hashes    = output_hashes,
        runner_identity  = runner_identity,
        timestamp_utc    = timestamp_utc,
        provider_model_id = provider_model_id,
        is_diagnostic    = is_diagnostic,
    )


def validate_attestation_chain(
    attestations: list[Attestation],
    run_id: str,
    commit_sha: str,
    mode: str,
    expected_stages: tuple[str, ...] = EXPECTED_STAGES,
) -> None:
    """
    Verify the chain of attestations for a complete pipeline run.

    Validates the SUBMITTED order — does not rebuild a valid order internally.
    Raises ChainValidationError for any of:
    - Empty list.
    - Schema version mismatch in any attestation.
    - Unknown stage name.
    - run_id mismatch in any attestation.
    - commit_sha mismatch in any attestation.
    - mode mismatch in any attestation.
    - Empty runner_identity in any attestation.
    - Malformed ISO-8601 timestamp.
    - Non-hex or wrong-length artifact hash values.
    - Duplicate stage.
    - Missing required stage.
    - Diagnostic attestation in a production chain.
    - Missing provider_model_id for production provider stages.
    - Output hash of stage N not matching input hash of stage N+1 (hash substitution).
    - Missing required artifact edges (mandatory graph).
    - Stages presented in the wrong order relative to expected_stages.
    """
    if not attestations:
        raise ChainValidationError("Attestation list is empty; cannot validate chain.")

    # Per-attestation strict field validation
    for att in attestations:
        _validate_single_attestation(att, mode)

    seen_stages: dict[str, Attestation] = {}
    for att in attestations:
        if att.run_id != run_id:
            raise ChainValidationError(
                f"Stage '{att.stage}' run_id '{att.run_id}' != expected '{run_id}'."
            )
        if att.commit_sha != commit_sha:
            raise ChainValidationError(
                f"Stage '{att.stage}' commit_sha '{att.commit_sha}' "
                f"!= expected '{commit_sha}'."
            )
        if att.mode != mode:
            raise ChainValidationError(
                f"Stage '{att.stage}' mode '{att.mode}' != expected '{mode}'."
            )
        if att.stage in seen_stages:
            raise ChainValidationError(
                f"Duplicate attestation for stage '{att.stage}'."
            )
        seen_stages[att.stage] = att

    missing = [s for s in expected_stages if s not in seen_stages]
    if missing:
        raise ChainValidationError(
            f"Missing attestations for stage(s): {missing}."
        )

    # Validate submitted ORDER matches expected order (not just set membership)
    submitted_order = [a.stage for a in attestations if a.stage in set(expected_stages)]
    expected_present = [s for s in expected_stages if s in seen_stages]
    if submitted_order != expected_present:
        raise ChainValidationError(
            f"Attestations submitted in wrong order. "
            f"Expected: {expected_present}, got: {submitted_order}."
        )

    # Hash-chain: if stage N records an output and stage N+1 records a
    # matching input key, the hashes must agree (hash substitution detection).
    ordered = [seen_stages[s] for s in expected_stages if s in seen_stages]
    for i in range(len(ordered) - 1):
        prev, nxt = ordered[i], ordered[i + 1]
        for key, prev_hash in prev.output_hashes.items():
            if key in nxt.input_hashes:
                if nxt.input_hashes[key] != prev_hash:
                    raise ChainValidationError(
                        f"Hash mismatch for '{key}' between stage "
                        f"'{prev.stage}' (output) and '{nxt.stage}' (input): "
                        f"{prev_hash[:16]}… vs {nxt.input_hashes[key][:16]}…"
                    )

    # Mandatory artifact edge validation
    for out_stage, artifact_key, in_stage in REQUIRED_ARTIFACT_EDGES:
        if out_stage not in seen_stages or in_stage not in seen_stages:
            continue  # only validate edges when both stages are present
        out_att = seen_stages[out_stage]
        in_att  = seen_stages[in_stage]
        if artifact_key not in out_att.output_hashes:
            raise ChainValidationError(
                f"Required artifact '{artifact_key}' missing from "
                f"stage '{out_stage}' output_hashes."
            )
        if artifact_key not in in_att.input_hashes:
            raise ChainValidationError(
                f"Required artifact '{artifact_key}' missing from "
                f"stage '{in_stage}' input_hashes."
            )
        if out_att.output_hashes[artifact_key] != in_att.input_hashes[artifact_key]:
            raise ChainValidationError(
                f"Mandatory artifact edge hash mismatch for '{artifact_key}' "
                f"between '{out_stage}' output and '{in_stage}' input."
            )


def aggregate_attestations(
    attestations: list[Attestation],
    run_id: str,
    commit_sha: str,
    mode: str,
    expected_stages: tuple[str, ...] = EXPECTED_STAGES,
) -> dict[str, Any]:
    """
    Aggregate and verify the attestation chain.  Returns a summary dict.
    Raises ChainValidationError on any inconsistency.
    """
    validate_attestation_chain(attestations, run_id, commit_sha, mode, expected_stages)
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "commit_sha": commit_sha,
        "mode": mode,
        "stages_verified": [a.stage for a in attestations],
        "chain_valid": True,
        "is_diagnostic": any(a.is_diagnostic for a in attestations),
        "confirmation_ready": False,  # never True from attestation chain alone
    }
