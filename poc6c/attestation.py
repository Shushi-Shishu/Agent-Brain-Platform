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
    runner_identity:     str               # e.g. "github-actions/ubuntu-24.04" or "local-synthetic"
    timestamp_utc:       str               # ISO-8601
    provider_model_id:   str | None        # None for non-API stages
    is_diagnostic:       bool

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Attestation":
        return cls(**{k: v for k, v in d.items() if k in {f.name for f in dataclasses.fields(cls)}})

    def sha256(self) -> str:
        """Stable content hash of this attestation (for chaining)."""
        serialised = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialised.encode("utf-8")).hexdigest().upper()


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

    Raises ChainValidationError for:
    - run_id mismatch in any attestation
    - commit_sha mismatch in any attestation
    - mode mismatch in any attestation
    - missing required stage
    - duplicate stage
    - diagnostic attestation in a production chain
    - output hash of stage N not matching input hash of stage N+1 (when declared)
    """
    if not attestations:
        raise ChainValidationError("Attestation list is empty; cannot validate chain.")

    seen_stages: dict[str, Attestation] = {}
    for att in attestations:
        if att.run_id != run_id:
            raise ChainValidationError(
                f"Stage '{att.stage}' run_id '{att.run_id}' != expected '{run_id}'."
            )
        if att.commit_sha != commit_sha:
            raise ChainValidationError(
                f"Stage '{att.stage}' commit_sha '{att.commit_sha}' != expected '{commit_sha}'."
            )
        if att.mode != mode:
            raise ChainValidationError(
                f"Stage '{att.stage}' mode '{att.mode}' != expected '{mode}'."
            )
        if mode == "production" and att.is_diagnostic:
            raise ChainValidationError(
                f"Stage '{att.stage}' carries is_diagnostic=True in a production chain."
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

    # Hash-chain: if stage N records an output and stage N+1 records a
    # matching input key, the hashes must agree.
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
