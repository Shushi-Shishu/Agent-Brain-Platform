"""Tests for pipeline_artifacts.py and synthetic_runner.py (T4B-03/T4B-08)."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from pipeline_artifacts import (
    ArmResult,
    BlindedAnswerBundle,
    CardinalityError,
    CrossRunError,
    EmptyScoreError,
    EvaluatorResult,
    LabelLeakageError,
    SCHEMA_VERSION,
    assert_no_label_leakage,
    build_blinded_answer_bundle,
    validate_arm_results,
    validate_evaluator_result,
)

_RUN_ID   = "test-run-abc"
_TASKS    = ["T001", "T002", "T003"]
_RUBRIC   = "RUBRICHASH"


def _make_arm_results(run_id: str = _RUN_ID, tasks: list = _TASKS) -> list[ArmResult]:
    results = []
    for arm in ("generic", "configured"):
        for task_id in tasks:
            results.append(ArmResult(
                schema_version = SCHEMA_VERSION,
                run_id         = run_id,
                arm            = arm,
                task_id        = task_id,
                answer         = f"Answer from {arm} for {task_id}",
                telemetry      = {},
                is_diagnostic  = True,
            ))
    return results


class TestValidateArmResults:
    def test_valid_passes(self):
        validate_arm_results(_make_arm_results(), _RUN_ID, _TASKS)

    def test_cross_run_id_raises(self):
        results = _make_arm_results()
        results[0] = ArmResult(SCHEMA_VERSION, "wrong-run", "generic", _TASKS[0],
                                "x", {}, True)
        with pytest.raises(CrossRunError):
            validate_arm_results(results, _RUN_ID, _TASKS)

    def test_missing_task_raises(self):
        results = [r for r in _make_arm_results() if r.task_id != _TASKS[1] or r.arm != "generic"]
        with pytest.raises(CardinalityError):
            validate_arm_results(results, _RUN_ID, _TASKS)


class TestBuildBlindedAnswerBundle:
    def _build(self):
        return build_blinded_answer_bundle(
            _make_arm_results(), _RUN_ID, _TASKS, _RUBRIC, is_diagnostic=True
        )

    def test_golden_path(self):
        bundle, plain_mapping = self._build()
        assert bundle.run_id == _RUN_ID
        assert bundle.is_diagnostic is True
        assert len(bundle.blind_ids) == len(_TASKS) * 2
        assert set(bundle.blind_ids) == set(bundle.answers_by_blind_id.keys())
        assert set(plain_mapping.keys()) == set(bundle.blind_ids)

    def test_no_arm_labels_in_bundle(self):
        bundle, _ = self._build()
        assert_no_label_leakage(bundle)
        # Keys must not be 'generic' or 'configured'
        for bid in bundle.blind_ids:
            assert bid.lower() not in ("generic", "configured")

    def test_bundle_sha256_stable(self):
        bundle, _ = self._build()
        h1, h2 = bundle.sha256(), bundle.sha256()
        assert h1 == h2

    def test_plain_mapping_contains_arm_labels(self):
        _, plain_mapping = self._build()
        arms_seen = {v["arm"] for v in plain_mapping.values()}
        assert arms_seen == {"generic", "configured"}


class TestAssertNoLabelLeakage:
    def test_valid_bundle_passes(self):
        bundle, _ = build_blinded_answer_bundle(
            _make_arm_results(), _RUN_ID, _TASKS, _RUBRIC, is_diagnostic=True
        )
        assert_no_label_leakage(bundle)

    def test_arm_label_key_raises(self):
        bundle = BlindedAnswerBundle(
            schema_version      = SCHEMA_VERSION,
            run_id              = _RUN_ID,
            blind_ids           = ["generic"],
            answers_by_blind_id = {"generic": "some answer"},
            rubric_sha256       = _RUBRIC,
            is_diagnostic       = True,
        )
        with pytest.raises(LabelLeakageError):
            assert_no_label_leakage(bundle)


class TestValidateEvaluatorResult:
    def _bundle(self):
        bundle, _ = build_blinded_answer_bundle(
            _make_arm_results(), _RUN_ID, _TASKS, _RUBRIC, is_diagnostic=True
        )
        return bundle

    def test_production_empty_scores_raises(self):
        bundle = self._bundle()
        result = EvaluatorResult(SCHEMA_VERSION, _RUN_ID, {}, True)
        with pytest.raises(EmptyScoreError):
            validate_evaluator_result(result, bundle, mode="production")

    def test_production_pending_score_raises(self):
        bundle = self._bundle()
        scores = {bid: "pending_r01_r05" for bid in bundle.blind_ids}
        result = EvaluatorResult(SCHEMA_VERSION, _RUN_ID, scores, False)
        with pytest.raises(EmptyScoreError):
            validate_evaluator_result(result, bundle, mode="production")

    def test_production_none_score_raises(self):
        bundle = self._bundle()
        scores = {bid: None for bid in bundle.blind_ids}
        result = EvaluatorResult(SCHEMA_VERSION, _RUN_ID, scores, False)
        with pytest.raises(EmptyScoreError):
            validate_evaluator_result(result, bundle, mode="production")

    def test_production_missing_blind_id_raises(self):
        bundle = self._bundle()
        # Only score half the blind_ids
        half = bundle.blind_ids[:1]
        scores = {bid: {"total": 80} for bid in half}
        result = EvaluatorResult(SCHEMA_VERSION, _RUN_ID, scores, False)
        with pytest.raises(EmptyScoreError):
            validate_evaluator_result(result, bundle, mode="production")

    def test_diagnostic_empty_scores_ok(self):
        bundle = self._bundle()
        result = EvaluatorResult(SCHEMA_VERSION, _RUN_ID, {}, True)
        validate_evaluator_result(result, bundle, mode="diagnostic")  # no raise

    def test_production_valid_scores_pass(self):
        bundle = self._bundle()
        scores = {bid: {"total": 75} for bid in bundle.blind_ids}
        result = EvaluatorResult(SCHEMA_VERSION, _RUN_ID, scores, False)
        validate_evaluator_result(result, bundle, mode="production")  # no raise


class TestSyntheticRunner:
    def test_diagnostic_pipeline_completes(self):
        from synthetic_runner import run_diagnostic_pipeline
        report = run_diagnostic_pipeline()
        assert report is not None

    def test_confirmation_ready_always_false(self):
        from synthetic_runner import run_diagnostic_pipeline
        report = run_diagnostic_pipeline()
        assert report.confirmation_ready is False

    def test_is_diagnostic_true(self):
        from synthetic_runner import run_diagnostic_pipeline
        report = run_diagnostic_pipeline()
        assert report.is_diagnostic is True

    def test_all_stages_complete(self):
        from synthetic_runner import run_diagnostic_pipeline
        report = run_diagnostic_pipeline()
        assert report.all_stages_complete is True
        assert report.attestation_chain_valid is True

    def test_mode_is_diagnostic(self):
        from synthetic_runner import run_diagnostic_pipeline
        report = run_diagnostic_pipeline()
        assert report.mode == "diagnostic"

    def test_custom_task_ids(self):
        from synthetic_runner import run_diagnostic_pipeline
        report = run_diagnostic_pipeline(task_ids=["X001", "X002"])
        assert report.confirmation_ready is False
