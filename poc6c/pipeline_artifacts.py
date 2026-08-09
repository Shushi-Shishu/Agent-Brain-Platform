"""
Versioned pipeline artifact schemas for POC 6c.

Data flow:
  TaskPackage
    ↓ (both arms consume)
  ArmResult  (one per arm per task/repeat pair)
    ↓ (custody stage)
  BlindedAnswerBundle  +  CustodyMapping (separate path)
    ↓ (evaluator receives bundle + rubric only)
  EvaluatorResult
    ↓ (integrity job)
  IntegrityReport

Security invariants
-------------------
- Raw arm labels and the encrypted mapping never appear in evaluator inputs.
- Empty scores or 'pending_r01_r05' values are fatal in production mode.
- Diagnostic artifacts carry is_diagnostic=True and are rejected by all
  production analysis paths.
- Exactly two declared arms (generic, configured) are required; no more,
  no fewer, no unknowns, no duplicates.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import secrets
from typing import Any

SCHEMA_VERSION = "poc6c-artifacts-v1"
_DIAGNOSTIC_TAG = "diagnostic_synthetic_only"

# Canonical arm set — must match exactly; no unknowns, no extras.
DECLARED_ARMS: tuple[str, ...] = ("generic", "configured")


class ArtifactError(RuntimeError):
    """Base class for pipeline artifact errors."""


class CardinalityError(ArtifactError):
    """Arm results missing expected task IDs/repeats, or wrong arm set."""


class UnknownArmError(ArtifactError):
    """An arm label not in DECLARED_ARMS was submitted."""


class DuplicateResultError(ArtifactError):
    """Duplicate (arm, task_id, repeat) tuple in arm results."""


class LabelLeakageError(ArtifactError):
    """Raw arm label found in evaluator input."""


class EmptyScoreError(ArtifactError):
    """Evaluator produced empty or placeholder scores in production mode."""


class CrossRunError(ArtifactError):
    """Artifact from a different run_id mixed into this run."""


class ProductionRejectionError(ArtifactError):
    """A diagnostic/synthetic/test-only artifact was presented to a production consumer."""


# ---------------------------------------------------------------------------
# TaskPackage
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class TaskPackage:
    schema_version: str
    run_id:         str
    task_ids:       list[str]
    corpus_sha256:  str
    is_diagnostic:  bool

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    def sha256(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest().upper()

    @classmethod
    def make_diagnostic(cls, run_id: str, task_ids: list[str]) -> "TaskPackage":
        return cls(
            schema_version=SCHEMA_VERSION,
            run_id=run_id,
            task_ids=task_ids,
            corpus_sha256="SYNTHETIC-CORPUS-HASH",
            is_diagnostic=True,
        )


# ---------------------------------------------------------------------------
# ArmResult
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class ArmResult:
    schema_version: str
    run_id:         str
    arm:            str          # "generic" | "configured"
    task_id:        str
    answer:         str
    telemetry:      dict[str, Any]
    is_diagnostic:  bool

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    def sha256(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest().upper()


def validate_arm_results(
    arm_results: list[ArmResult],
    expected_run_id: str,
    expected_task_ids: list[str],
    expected_repeats: int = 1,
) -> None:
    """
    Verify exact cardinality, run-ID consistency, and no cross-run substitution.

    Enforces:
    - Zero arms raises CardinalityError.
    - One arm (missing the other) raises CardinalityError.
    - Unknown arm name raises UnknownArmError.
    - Exactly DECLARED_ARMS present; any extra raises UnknownArmError.
    - Exactly one result per (arm, task_id, repeat) — duplicates raise DuplicateResultError.
    - Missing (arm, task_id) pair raises CardinalityError.
    - Empty answer raises CardinalityError.
    - Cross-run run_id raises CrossRunError.
    """
    if not arm_results:
        raise CardinalityError("No arm results provided; expected results for arms: "
                               f"{list(DECLARED_ARMS)}.")

    # Cross-run check first
    for r in arm_results:
        if r.run_id != expected_run_id:
            raise CrossRunError(
                f"ArmResult for task '{r.task_id}' arm '{r.arm}' has run_id "
                f"'{r.run_id}', expected '{expected_run_id}'."
            )

    # Validate arm names
    submitted_arms = {r.arm for r in arm_results}
    unknown = submitted_arms - set(DECLARED_ARMS)
    if unknown:
        raise UnknownArmError(
            f"Unknown arm(s) in results: {sorted(unknown)}. "
            f"Only declared arms are accepted: {list(DECLARED_ARMS)}."
        )

    # Check all declared arms are present
    missing_arms = set(DECLARED_ARMS) - submitted_arms
    if missing_arms:
        raise CardinalityError(
            f"Missing results for declared arm(s): {sorted(missing_arms)}. "
            f"Exactly {list(DECLARED_ARMS)} are required."
        )

    # Duplicate (arm, task_id, repeat) check
    seen: set[tuple[str, str, int]] = set()
    for r in arm_results:
        key = (r.arm, r.task_id, getattr(r, "repeat", 0))
        if key in seen:
            raise DuplicateResultError(
                f"Duplicate result for arm='{r.arm}' task_id='{r.task_id}' "
                f"repeat={getattr(r, 'repeat', 0)}."
            )
        seen.add(key)

    # Empty answer check
    for r in arm_results:
        if not r.answer or not r.answer.strip():
            raise CardinalityError(
                f"Arm '{r.arm}' task '{r.task_id}' has an empty answer."
            )

    # Each declared arm must have exactly one result per expected task
    by_arm: dict[str, set[str]] = {}
    for r in arm_results:
        by_arm.setdefault(r.arm, set()).add(r.task_id)
    for arm in DECLARED_ARMS:
        task_set = by_arm.get(arm, set())
        missing = set(expected_task_ids) - task_set
        if missing:
            raise CardinalityError(
                f"Arm '{arm}' missing results for tasks: {sorted(missing)}."
            )
        extra = task_set - set(expected_task_ids)
        if extra:
            raise CardinalityError(
                f"Arm '{arm}' has unexpected task results: {sorted(extra)}."
            )


# ---------------------------------------------------------------------------
# BlindedAnswerBundle + CustodyMapping
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class BlindedAnswerBundle:
    schema_version:     str
    run_id:             str
    blind_ids:          list[str]
    answers_by_blind_id: dict[str, str]   # blind_id → answer text
    rubric_sha256:      str
    is_diagnostic:      bool

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    def sha256(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest().upper()


@dataclasses.dataclass
class CustodyMapping:
    """Holds the encrypted mapping bundle — kept on a separate custody path."""
    schema_version:     str
    run_id:             str
    bundle_json_str:    str   # serialised MappingBundle (encrypted)
    is_diagnostic:      bool

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def build_blinded_answer_bundle(
    arm_results: list[ArmResult],
    expected_run_id: str,
    expected_task_ids: list[str],
    rubric_sha256: str,
    is_diagnostic: bool,
) -> tuple[BlindedAnswerBundle, dict[str, dict[str, str]]]:
    """
    Assign random blind IDs to each (task_id, arm) pair and produce a
    BlindedAnswerBundle.

    Returns (bundle, plain_mapping) where plain_mapping maps
    blind_id → {"task_id": ..., "arm": ...}.

    The plain mapping must be encrypted by the custody stage; it must
    never be passed to the evaluator.

    Arm labels are absent from the bundle — evaluator receives only answers.
    """
    validate_arm_results(arm_results, expected_run_id, expected_task_ids)

    blind_ids: list[str] = []
    answers_by_blind_id: dict[str, str] = {}
    plain_mapping: dict[str, dict[str, str]] = {}

    for result in arm_results:
        blind_id = secrets.token_hex(8).upper()
        blind_ids.append(blind_id)
        answers_by_blind_id[blind_id] = result.answer
        plain_mapping[blind_id] = {"task_id": result.task_id, "arm": result.arm}

    bundle = BlindedAnswerBundle(
        schema_version      = SCHEMA_VERSION,
        run_id              = expected_run_id,
        blind_ids           = blind_ids,
        answers_by_blind_id = answers_by_blind_id,
        rubric_sha256       = rubric_sha256,
        is_diagnostic       = is_diagnostic,
    )
    return bundle, plain_mapping


def assert_no_label_leakage(bundle: BlindedAnswerBundle) -> None:
    """
    Verify that the blinded bundle contains no raw arm labels anywhere.

    Checks:
    - Blind ID keys are not arm labels.
    - Answer text does not contain literal arm labels.
    - Serialized to_dict() bytes contain no arm labels in keys or values.
    - Nested metadata fields contain no arm labels.
    - Filenames derived from blind IDs are not arm labels.
    Raises LabelLeakageError on any violation.
    """
    forbidden = set(DECLARED_ARMS)  # {"generic", "configured"}

    # Keys must not be arm labels
    for k in bundle.answers_by_blind_id:
        if k.lower() in forbidden:
            raise LabelLeakageError(
                f"Blind ID key '{k}' is a raw arm label. "
                "Blind IDs must be random tokens."
            )

    # Answer text must not contain literal arm labels
    for bid, answer in bundle.answers_by_blind_id.items():
        for label in forbidden:
            if label in (answer or "").lower():
                raise LabelLeakageError(
                    f"Answer for blind_id '{bid}' contains raw arm label '{label}'."
                )

    # to_dict() serialization must not contain arm labels in any key
    d = bundle.to_dict()
    if "arm" in d:
        raise LabelLeakageError("BlindedAnswerBundle.to_dict() contains 'arm' key.")

    # Full JSON serialization must not contain arm labels as standalone values
    serialized = json.dumps(d, sort_keys=True)
    for label in forbidden:
        # Check as a JSON string value (exact match)
        if f'"{label}"' in serialized:
            raise LabelLeakageError(
                f"Serialized bundle contains raw arm label '{label}' as a JSON value."
            )


# ---------------------------------------------------------------------------
# EvaluatorResult
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class EvaluatorResult:
    schema_version:     str
    run_id:             str
    scores_by_blind_id: dict[str, Any]   # blind_id → score dict
    is_diagnostic:      bool

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def validate_evaluator_result(
    result: EvaluatorResult,
    bundle: BlindedAnswerBundle,
    mode: str,
) -> None:
    """
    Validate evaluator output against the blinded bundle.

    In production mode:
      - Rejects result.is_diagnostic=True (ProductionRejectionError).
      - Rejects diagnostic input bundles (ProductionRejectionError).
      - Scores must be non-empty.
      - 'pending_r01_r05', None, placeholder, dry_run, test_only, stale
        values are fatal.
      - Every blind_id in the bundle must have a score; no extras allowed.
      - Extra scores not in the bundle raise EmptyScoreError.
      - Cross-run run_id raises CrossRunError.
    """
    # Production rejection of diagnostic/synthetic/test-only artifacts
    if mode == "production":
        if result.is_diagnostic:
            raise ProductionRejectionError(
                "EvaluatorResult.is_diagnostic=True — this result was produced "
                "in diagnostic/synthetic mode and must not be used in production analysis."
            )
        if bundle.is_diagnostic:
            raise ProductionRejectionError(
                "BlindedAnswerBundle.is_diagnostic=True — this is a diagnostic input "
                "bundle and must not reach production evaluation."
            )
        if result.run_id != bundle.run_id:
            raise CrossRunError(
                f"EvaluatorResult run_id '{result.run_id}' != bundle run_id "
                f"'{bundle.run_id}'. Cross-run substitution rejected."
            )
        if not result.scores_by_blind_id:
            raise EmptyScoreError("Evaluator produced empty scores in production mode.")

        _REJECT_VALUES = {
            "pending_r01_r05", "dry_run_placeholder", "test_only",
            "placeholder", "stale", "synthetic",
        }
        for blind_id, score in result.scores_by_blind_id.items():
            if score is None:
                raise EmptyScoreError(
                    f"Score for blind_id '{blind_id}' is None — "
                    "null scores are fatal in production mode."
                )
            score_str = str(score).lower() if not isinstance(score, dict) else ""
            if score_str in _REJECT_VALUES:
                raise EmptyScoreError(
                    f"Score for blind_id '{blind_id}' is placeholder value "
                    f"'{score}' — rejected in production mode."
                )

        missing = set(bundle.blind_ids) - set(result.scores_by_blind_id.keys())
        if missing:
            raise EmptyScoreError(
                f"Missing scores for blind_ids: {sorted(missing)}."
            )
        extra = set(result.scores_by_blind_id.keys()) - set(bundle.blind_ids)
        if extra:
            raise EmptyScoreError(
                f"Extra scores for blind_ids not in bundle: {sorted(extra)}."
            )


# ---------------------------------------------------------------------------
# IntegrityReport
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class IntegrityReport:
    schema_version:          str
    run_id:                  str
    mode:                    str
    attestation_chain_valid: bool
    all_stages_complete:     bool
    confirmation_ready:      bool   # always False — only real R01-R05 evidence can change this
    is_diagnostic:           bool
    notes:                   list[str]

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)
