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
    DuplicateResultError,
    EmptyScoreError,
    EvaluatorResult,
    LabelLeakageError,
    ProductionRejectionError,
    UnknownArmError,
    DECLARED_ARMS,
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
    """Create valid arm results with NO arm labels in answer text."""
    results = []
    for arm in DECLARED_ARMS:
        for task_id in tasks:
            results.append(ArmResult(
                schema_version = SCHEMA_VERSION,
                run_id         = run_id,
                arm            = arm,
                task_id        = task_id,
                answer         = f"Synthetic answer for task {task_id}.",
                telemetry      = {},
                is_diagnostic  = True,
            ))
    return results


def _make_production_bundle():
    """Create a non-diagnostic bundle suitable for production validation tests."""
    results = []
    for arm in DECLARED_ARMS:
        for task_id in _TASKS:
            results.append(ArmResult(
                schema_version = SCHEMA_VERSION,
                run_id         = _RUN_ID,
                arm            = arm,
                task_id        = task_id,
                answer         = f"Production answer for task {task_id}.",
                telemetry      = {},
                is_diagnostic  = False,
            ))
    bundle, _ = build_blinded_answer_bundle(
        results, _RUN_ID, _TASKS, _RUBRIC, is_diagnostic=False
    )
    return bundle


class TestValidateArmResults:
    def test_valid_passes(self):
        validate_arm_results(_make_arm_results(), _RUN_ID, _TASKS)

    def test_cross_run_id_raises(self):
        results = _make_arm_results()
        results[0] = ArmResult(SCHEMA_VERSION, "wrong-run", "generic", _TASKS[0],
                                "answer text", {}, True)
        with pytest.raises(CrossRunError):
            validate_arm_results(results, _RUN_ID, _TASKS)

    def test_missing_task_raises(self):
        results = [r for r in _make_arm_results() if r.task_id != _TASKS[1] or r.arm != "generic"]
        with pytest.raises(CardinalityError):
            validate_arm_results(results, _RUN_ID, _TASKS)

    def test_no_arms_raises(self):
        with pytest.raises(CardinalityError, match="No arm results"):
            validate_arm_results([], _RUN_ID, _TASKS)

    def test_one_arm_missing_raises(self):
        results = [r for r in _make_arm_results() if r.arm == "generic"]
        with pytest.raises(CardinalityError, match="Missing results"):
            validate_arm_results(results, _RUN_ID, _TASKS)

    def test_unknown_arm_raises(self):
        results = _make_arm_results()
        results[0] = ArmResult(SCHEMA_VERSION, _RUN_ID, "unknown_arm", _TASKS[0],
                                "answer text", {}, True)
        with pytest.raises(UnknownArmError):
            validate_arm_results(results, _RUN_ID, _TASKS)

    def test_duplicate_arm_task_raises(self):
        results = _make_arm_results()
        # Add duplicate
        results.append(ArmResult(SCHEMA_VERSION, _RUN_ID, "generic", _TASKS[0],
                                  "answer text", {}, True))
        with pytest.raises(DuplicateResultError):
            validate_arm_results(results, _RUN_ID, _TASKS)

    def test_empty_answer_raises(self):
        results = _make_arm_results()
        results[0] = ArmResult(SCHEMA_VERSION, _RUN_ID, "generic", _TASKS[0],
                                "", {}, True)
        with pytest.raises(CardinalityError, match="empty answer"):
            validate_arm_results(results, _RUN_ID, _TASKS)

    def test_extra_task_raises(self):
        results = _make_arm_results()
        for arm in DECLARED_ARMS:
            results.append(ArmResult(SCHEMA_VERSION, _RUN_ID, arm, "EXTRA-TASK",
                                      "answer text", {}, True))
        with pytest.raises(CardinalityError, match="unexpected"):
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
        for bid in bundle.blind_ids:
            assert bid.lower() not in DECLARED_ARMS

    def test_bundle_sha256_stable(self):
        bundle, _ = self._build()
        h1, h2 = bundle.sha256(), bundle.sha256()
        assert h1 == h2

    def test_plain_mapping_contains_arm_labels(self):
        _, plain_mapping = self._build()
        arms_seen = {v["arm"] for v in plain_mapping.values()}
        assert arms_seen == set(DECLARED_ARMS)


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

    def test_arm_label_in_answer_text_raises(self):
        bundle = BlindedAnswerBundle(
            schema_version      = SCHEMA_VERSION,
            run_id              = _RUN_ID,
            blind_ids           = ["BLINDID01"],
            answers_by_blind_id = {"BLINDID01": "This is the generic arm answer."},
            rubric_sha256       = _RUBRIC,
            is_diagnostic       = True,
        )
        with pytest.raises(LabelLeakageError, match="(?i)answer.*generic"):
            assert_no_label_leakage(bundle)

    def test_arm_label_in_serialized_value_raises(self):
        bundle = BlindedAnswerBundle(
            schema_version      = SCHEMA_VERSION,
            run_id              = _RUN_ID,
            blind_ids           = ["BLINDID01"],
            answers_by_blind_id = {"BLINDID01": "generic"},
            rubric_sha256       = _RUBRIC,
            is_diagnostic       = True,
        )
        with pytest.raises(LabelLeakageError):
            assert_no_label_leakage(bundle)


class TestValidateEvaluatorResult:
    def test_production_rejects_diagnostic_result(self):
        """J3-04: diagnostic result must be rejected by production consumer."""
        bundle = _make_production_bundle()
        result = EvaluatorResult(SCHEMA_VERSION, _RUN_ID, {}, is_diagnostic=True)
        with pytest.raises(ProductionRejectionError, match="is_diagnostic"):
            validate_evaluator_result(result, bundle, mode="production")

    def test_production_rejects_diagnostic_bundle(self):
        """J3-04: diagnostic bundle must be rejected by production consumer."""
        diag_bundle, _ = build_blinded_answer_bundle(
            _make_arm_results(), _RUN_ID, _TASKS, _RUBRIC, is_diagnostic=True
        )
        result = EvaluatorResult(SCHEMA_VERSION, _RUN_ID, {}, is_diagnostic=False)
        with pytest.raises(ProductionRejectionError, match="is_diagnostic"):
            validate_evaluator_result(result, diag_bundle, mode="production")

    def test_production_empty_scores_raises(self):
        bundle = _make_production_bundle()
        result = EvaluatorResult(SCHEMA_VERSION, _RUN_ID, {}, is_diagnostic=False)
        with pytest.raises(EmptyScoreError):
            validate_evaluator_result(result, bundle, mode="production")

    def test_production_pending_score_raises(self):
        bundle = _make_production_bundle()
        scores = {bid: "pending_r01_r05" for bid in bundle.blind_ids}
        result = EvaluatorResult(SCHEMA_VERSION, _RUN_ID, scores, is_diagnostic=False)
        with pytest.raises(EmptyScoreError):
            validate_evaluator_result(result, bundle, mode="production")

    def test_production_none_score_raises(self):
        bundle = _make_production_bundle()
        scores = {bid: None for bid in bundle.blind_ids}
        result = EvaluatorResult(SCHEMA_VERSION, _RUN_ID, scores, is_diagnostic=False)
        with pytest.raises(EmptyScoreError):
            validate_evaluator_result(result, bundle, mode="production")

    def test_production_missing_blind_id_raises(self):
        bundle = _make_production_bundle()
        half = bundle.blind_ids[:1]
        scores = {bid: {"total": 80} for bid in half}
        result = EvaluatorResult(SCHEMA_VERSION, _RUN_ID, scores, is_diagnostic=False)
        with pytest.raises(EmptyScoreError):
            validate_evaluator_result(result, bundle, mode="production")

    def test_production_extra_blind_id_raises(self):
        bundle = _make_production_bundle()
        scores = {bid: {"total": 80} for bid in bundle.blind_ids}
        scores["EXTRA_BLIND_ID"] = {"total": 80}
        result = EvaluatorResult(SCHEMA_VERSION, _RUN_ID, scores, is_diagnostic=False)
        with pytest.raises(EmptyScoreError, match="Extra"):
            validate_evaluator_result(result, bundle, mode="production")

    def test_production_cross_run_raises(self):
        bundle = _make_production_bundle()
        scores = {bid: {"total": 80} for bid in bundle.blind_ids}
        result = EvaluatorResult(SCHEMA_VERSION, "different-run-id", scores, is_diagnostic=False)
        with pytest.raises(CrossRunError):
            validate_evaluator_result(result, bundle, mode="production")

    def test_diagnostic_empty_scores_ok(self):
        diag_bundle, _ = build_blinded_answer_bundle(
            _make_arm_results(), _RUN_ID, _TASKS, _RUBRIC, is_diagnostic=True
        )
        result = EvaluatorResult(SCHEMA_VERSION, _RUN_ID, {}, is_diagnostic=True)
        validate_evaluator_result(result, diag_bundle, mode="diagnostic")  # no raise

    def test_production_valid_scores_pass(self):
        bundle = _make_production_bundle()
        scores = {bid: {"total": 75} for bid in bundle.blind_ids}
        result = EvaluatorResult(SCHEMA_VERSION, _RUN_ID, scores, is_diagnostic=False)
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
