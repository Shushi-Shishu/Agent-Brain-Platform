"""
Local synthetic runner for POC 6c.

Exercises the same six-stage entrypoints and artifact contracts as the
GitHub Actions workflow using synthetic tasks, providers, answers, and
scores.  No live API calls, no real secrets, no confirmation material.

All outputs are tagged diagnostic_synthetic_only.
confirmation_ready is always False.

Usage:
    from synthetic_runner import run_diagnostic_pipeline
    report = run_diagnostic_pipeline()
    assert report.confirmation_ready is False
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import timezone
from datetime import datetime as _dt
from pathlib import Path
from typing import Any

from attestation import (
    Attestation,
    ChainValidationError,
    EXPECTED_STAGES,
    aggregate_attestations,
    create_attestation,
)
from blinding import (
    DryRunBundle,
    assert_mapping_not_in_environment,
    assert_seed_not_in_environment,
    assign_arms,
    check_not_dry_run_bundle,
    encrypt_mapping,
    generate_seed,
)
from pipeline_artifacts import (
    ArmResult,
    BlindedAnswerBundle,
    CustodyMapping,
    EvaluatorResult,
    IntegrityReport,
    SCHEMA_VERSION,
    _DIAGNOSTIC_TAG,
    assert_no_label_leakage,
    build_blinded_answer_bundle,
    validate_evaluator_result,
)
from pipeline_mode import PipelineMode

HERE = Path(__file__).resolve().parent
_RUBRIC_PATH = HERE / "confirmation" / "EVALUATION_RUBRIC_V1.md"

_RUN_ID_PREFIX = "synthetic-diag-"
_RUNNER_IDENTITY = "local-synthetic"
_COMMIT_SHA = "0000000000000000000000000000000000000000"  # sentinel for diagnostic

_SYNTHETIC_TASK_IDS = [f"SYN-{i:03d}" for i in range(1, 6)]
_ARMS = ("generic", "configured")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_utc() -> str:
    return _dt.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_str(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def _rubric_sha256() -> str:
    if _RUBRIC_PATH.exists():
        return hashlib.sha256(_RUBRIC_PATH.read_bytes()).hexdigest().upper()
    return "RUBRIC-NOT-FOUND"


# ---------------------------------------------------------------------------
# Stage 1: Preflight (diagnostic)
# ---------------------------------------------------------------------------

def _stage_preflight(run_id: str) -> Attestation:
    from readiness import run_diagnostic_preflight
    run_diagnostic_preflight(skip_r08_vault=True)
    corpus_hash = _sha256_str("synthetic-corpus-package")
    return create_attestation(
        stage            = "preflight",
        mode             = PipelineMode.DIAGNOSTIC.value,
        run_id           = run_id,
        commit_sha       = _COMMIT_SHA,
        input_hashes     = {},
        output_hashes    = {"preflight_report": _sha256_str(f"{run_id}-preflight-ok")},
        runner_identity  = _RUNNER_IDENTITY,
        timestamp_utc    = _now_utc(),
        provider_model_id = None,
        is_diagnostic    = True,
    )


# ---------------------------------------------------------------------------
# Stage 2 & 3: Arm execution (synthetic)
# ---------------------------------------------------------------------------

def _run_arm(arm: str, run_id: str, task_ids: list[str]) -> tuple[list[ArmResult], Attestation]:
    assert_seed_not_in_environment()
    assert_mapping_not_in_environment()

    results: list[ArmResult] = []
    for task_id in task_ids:
        # Answers must not contain raw arm labels (J3-03)
        answer = f"Synthetic answer for task {task_id}. [{_DIAGNOSTIC_TAG}]"
        results.append(ArmResult(
            schema_version = SCHEMA_VERSION,
            run_id         = run_id,
            arm            = arm,
            task_id        = task_id,
            answer         = answer,
            telemetry      = {"model_id": "synthetic", "tokens": 0, "is_diagnostic": True},
            is_diagnostic  = True,
        ))

    combined_hash = _sha256_str(json.dumps(
        [r.to_dict() for r in results], sort_keys=True
    ))
    att = create_attestation(
        stage            = f"{arm}-arm",
        mode             = PipelineMode.DIAGNOSTIC.value,
        run_id           = run_id,
        commit_sha       = _COMMIT_SHA,
        input_hashes     = {"task_package": _sha256_str(str(task_ids))},
        output_hashes    = {f"{arm}_arm_results": combined_hash},
        runner_identity  = _RUNNER_IDENTITY,
        timestamp_utc    = _now_utc(),
        provider_model_id = "synthetic",
        is_diagnostic    = True,
    )
    return results, att


# ---------------------------------------------------------------------------
# Stage 4: Deterministic blinding
# ---------------------------------------------------------------------------

def _stage_blinding(
    all_arm_results: list[ArmResult],
    run_id: str,
    task_ids: list[str],
) -> tuple[BlindedAnswerBundle, CustodyMapping, Attestation, str, str]:
    """Returns (bundle, custody, att, bundle_hash, mapping_bundle_hash).

    bundle_hash       → evaluator input (blinded_answer_bundle)
    mapping_bundle_hash → custody output only (never reaches evaluator)
    """
    # Synthetic seed — never persisted
    seed = generate_seed()
    rubric_sha = _rubric_sha256()

    bundle, plain_mapping = build_blinded_answer_bundle(
        arm_results        = all_arm_results,
        expected_run_id    = run_id,
        expected_task_ids  = task_ids,
        rubric_sha256      = rubric_sha,
        is_diagnostic      = True,
    )
    assert_no_label_leakage(bundle)

    # Encrypt mapping with dry_run=True (test-only key, tagged synthetic)
    mapping_bundle = encrypt_mapping(
        {bid: f"{v['task_id']}/{v['arm']}" for bid, v in plain_mapping.items()},
        dry_run=True,
    )
    custody = CustodyMapping(
        schema_version  = SCHEMA_VERSION,
        run_id          = run_id,
        bundle_json_str = json.dumps(mapping_bundle.to_dict(), sort_keys=True),
        is_diagnostic   = True,
    )

    bundle_hash = bundle.sha256()
    mapping_bundle_hash = _sha256_str(json.dumps(mapping_bundle.to_dict(), sort_keys=True))

    # Blinding attestation:
    #   inputs:  both arm results (for chain validation)
    #   outputs: blinded_answer_bundle (→ evaluator) + mapping_bundle (→ custody only)
    att = create_attestation(
        stage            = "deterministic-blinding",
        mode             = PipelineMode.DIAGNOSTIC.value,
        run_id           = run_id,
        commit_sha       = _COMMIT_SHA,
        input_hashes     = {
            "generic_arm_results":    _sha256_str(json.dumps(
                [r.to_dict() for r in all_arm_results if r.arm == "generic"], sort_keys=True)),
            "configured_arm_results": _sha256_str(json.dumps(
                [r.to_dict() for r in all_arm_results if r.arm == "configured"], sort_keys=True)),
        },
        output_hashes    = {
            "blinded_answer_bundle": bundle_hash,
            "mapping_bundle":        mapping_bundle_hash,
        },
        runner_identity  = _RUNNER_IDENTITY,
        timestamp_utc    = _now_utc(),
        provider_model_id = None,
        is_diagnostic    = True,
    )
    return bundle, custody, att, bundle_hash, mapping_bundle_hash


# ---------------------------------------------------------------------------
# Stage 5: Blinded evaluator (synthetic)
# ---------------------------------------------------------------------------

def _stage_evaluator(
    bundle: BlindedAnswerBundle,
    bundle_hash: str,
    run_id: str,
) -> tuple[EvaluatorResult, Attestation]:
    # Evaluator receives ONLY: blinded bundle + rubric. Verify no labels present.
    assert_no_label_leakage(bundle)
    assert_seed_not_in_environment()
    assert_mapping_not_in_environment()

    # Verify bundle is tagged diagnostic; production analysis would reject it
    bundle_dict = bundle.to_dict()
    if not bundle.is_diagnostic:
        raise RuntimeError("Synthetic runner received non-diagnostic bundle — abort.")

    # Produce synthetic scores (one per blind_id)
    scores: dict[str, Any] = {
        bid: {"total": 75, "is_diagnostic": True}
        for bid in bundle.blind_ids
    }

    result = EvaluatorResult(
        schema_version      = SCHEMA_VERSION,
        run_id              = run_id,
        scores_by_blind_id  = scores,
        is_diagnostic       = True,
    )
    # Validate result (diagnostic mode — empty scores OK, but test it passes)
    validate_evaluator_result(result, bundle, mode="diagnostic")

    result_hash = _sha256_str(json.dumps(result.to_dict(), sort_keys=True))
    att = create_attestation(
        stage            = "blinded-evaluator",
        mode             = PipelineMode.DIAGNOSTIC.value,
        run_id           = run_id,
        commit_sha       = _COMMIT_SHA,
        # Evaluator sees the blinded bundle only — NOT the mapping_bundle or custody material
        input_hashes     = {
            "blinded_answer_bundle": bundle_hash,
        },
        output_hashes    = {"evaluation_results": result_hash},
        runner_identity  = _RUNNER_IDENTITY,
        timestamp_utc    = _now_utc(),
        provider_model_id = "synthetic",
        is_diagnostic    = True,
    )
    return result, att


# ---------------------------------------------------------------------------
# Stage 6: Integrity and analysis
# ---------------------------------------------------------------------------

def _stage_integrity(
    attestations: list[Attestation],
    eval_result: EvaluatorResult,
    run_id: str,
) -> tuple[IntegrityReport, Attestation]:
    notes: list[str] = [
        "Diagnostic synthetic run — no confirmation answers generated.",
        "All outputs tagged diagnostic_synthetic_only.",
        "R01-R05 remain BLOCKED; Task 5 must not start.",
        "confirmation_ready=False is the only valid outcome of this run.",
    ]

    # Validate the chain of the 5 upstream stages (integrity stage not yet added)
    upstream_stages = tuple(s for s in EXPECTED_STAGES if s != "integrity-and-analysis")
    chain_valid = False
    try:
        aggregate_attestations(
            attestations,
            run_id      = run_id,
            commit_sha  = _COMMIT_SHA,
            mode        = PipelineMode.DIAGNOSTIC.value,
            expected_stages = upstream_stages,
        )
        chain_valid = True
    except ChainValidationError as e:
        notes.append(f"Upstream chain validation error: {e}")

    report = IntegrityReport(
        schema_version          = SCHEMA_VERSION,
        run_id                  = run_id,
        mode                    = PipelineMode.DIAGNOSTIC.value,
        attestation_chain_valid = chain_valid,
        all_stages_complete     = chain_valid,
        confirmation_ready      = False,
        is_diagnostic           = True,
        notes                   = notes,
    )

    # Integrity attestation must record the actual evaluation-result digest as input
    eval_result_hash = _sha256_str(json.dumps(eval_result.to_dict(), sort_keys=True))
    report_hash = _sha256_str(json.dumps(report.to_dict(), sort_keys=True))

    att = create_attestation(
        stage            = "integrity-and-analysis",
        mode             = PipelineMode.DIAGNOSTIC.value,
        run_id           = run_id,
        commit_sha       = _COMMIT_SHA,
        input_hashes     = {"evaluation_results": eval_result_hash},
        output_hashes    = {"integrity_report": report_hash},
        runner_identity  = _RUNNER_IDENTITY,
        timestamp_utc    = _now_utc(),
        provider_model_id = None,
        is_diagnostic    = True,
    )
    return report, att


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_diagnostic_pipeline(
    task_ids: list[str] | None = None,
) -> IntegrityReport:
    """
    Run a full 6-stage diagnostic pipeline with synthetic fixtures.

    Verifies:
    - All six stage entrypoints execute without errors
    - Blinded bundle contains no raw arm labels
    - Evaluator receives no mapping, seed, or private-key material
    - Attestation chain is consistent across all stages
    - IntegrityReport.confirmation_ready is always False

    Returns the IntegrityReport.
    """
    run_id   = _RUN_ID_PREFIX + _sha256_str(os.urandom(8).hex())[:12]
    task_ids = task_ids or _SYNTHETIC_TASK_IDS

    attestations: list[Attestation] = []

    # Stage 1
    att_preflight = _stage_preflight(run_id)
    attestations.append(att_preflight)

    # Stages 2 & 3
    generic_results, att_generic = _run_arm("generic", run_id, task_ids)
    configured_results, att_configured = _run_arm("configured", run_id, task_ids)
    attestations.append(att_generic)
    attestations.append(att_configured)

    all_arm_results = generic_results + configured_results

    # Stage 4
    bundle, custody, att_blinding, bundle_hash, mapping_bundle_hash = _stage_blinding(all_arm_results, run_id, task_ids)
    attestations.append(att_blinding)

    # Stage 5 — evaluator receives blinded bundle only, not the mapping bundle
    eval_result, att_evaluator = _stage_evaluator(bundle, bundle_hash, run_id)
    attestations.append(att_evaluator)

    # Stage 6
    report, att_integrity = _stage_integrity(attestations, eval_result, run_id)
    attestations.append(att_integrity)

    # Final chain validation with all six attestations
    try:
        aggregate_attestations(
            attestations,
            run_id     = run_id,
            commit_sha = _COMMIT_SHA,
            mode       = PipelineMode.DIAGNOSTIC.value,
        )
    except ChainValidationError as e:
        report.attestation_chain_valid = False
        report.all_stages_complete     = False
        report.notes.append(f"Final chain validation error: {e}")

    return report
