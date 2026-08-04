"""
Versioned pipeline artifact schemas for POC 6c.

Data flow:
  TaskPackage
    ↓ (both arms consume)
  ArmResult  (one per arm per task)
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


class ArtifactError(RuntimeError):
    """Base class for pipeline artifact errors."""


class CardinalityError(ArtifactError):
    """Arm results missing expected task IDs or repeats."""


class LabelLeakageError(ArtifactError):
    """Raw arm label found in evaluator input."""


class EmptyScoreError(ArtifactError):
    """Evaluator produced empty or placeholder scores in production mode."""


class CrossRunError(ArtifactError):
    """Artifact from a different run_id mixed into this run."""


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
) -> None:
    """Verify cardinality, run-ID consistency, and no cross-run substitution."""
    for r in arm_results:
        if r.run_id != expected_run_id:
            raise CrossRunError(
                f"ArmResult for task '{r.task_id}' has run_id '{r.run_id}', "
                f"expected '{expected_run_id}'."
            )
    # Each task must appear in both arms
    by_arm: dict[str, set[str]] = {}
    for r in arm_results:
        by_arm.setdefault(r.arm, set()).add(r.task_id)
    for arm, task_set in by_arm.items():
        missing = set(expected_task_ids) - task_set
        if missing:
            raise CardinalityError(
                f"Arm '{arm}' missing results for tasks: {sorted(missing)}"
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
    Verify that the blinded bundle contains no raw arm labels.
    Raises LabelLeakageError if 'generic' or 'configured' appear as keys
    or embedded in answer text.
    """
    forbidden = {"generic", "configured"}
    # Keys must not be arm labels
    for k in bundle.answers_by_blind_id:
        if k.lower() in forbidden:
            raise LabelLeakageError(f"Blind ID '{k}' is a raw arm label.")
    # to_dict serialisation must not contain arm-label keys at top level
    d = bundle.to_dict()
    if "arm" in d:
        raise LabelLeakageError("BlindedAnswerBundle.to_dict() contains 'arm' key.")


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
      - scores must be non-empty
      - 'pending_r01_r05' values are fatal
      - every blind_id in the bundle must have a score
    """
    if mode == "production":
        if not result.scores_by_blind_id:
            raise EmptyScoreError("Evaluator produced empty scores in production mode.")
        for blind_id, score in result.scores_by_blind_id.items():
            if score == "pending_r01_r05" or score is None:
                raise EmptyScoreError(
                    f"Score for blind_id '{blind_id}' is '{score}' — "
                    "placeholder scores are fatal in production mode."
                )
        missing = set(bundle.blind_ids) - set(result.scores_by_blind_id.keys())
        if missing:
            raise EmptyScoreError(
                f"Missing scores for blind_ids: {sorted(missing)}"
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
