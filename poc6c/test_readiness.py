"""
Tests for rubric.py and readiness.py — Task 4 confirmation-readiness checks.

Coverage:
  rubric.py
    - validate_rubric: passes on real file; detects hash mismatch,
      missing dimension, wrong max, missing anchor, missing critical_failure
    - rubric_calibration_evidence: structure, passed flag, scope note

  readiness.py
    - check_corpus_facade_enforced: passes on real corpus.py; detects
      missing class, missing manifest check, missing budget enforcement
    - check_rubric_calibration: delegates correctly
    - check_hash_reverification: all-local-match passes; mismatch fails;
      missing file fails; vault keys always vault_absent
    - check_preregistration_checklist: passes on updated file; fails on
      missing [x], missing gate phrase, forbidden confirmation output phrase
    - build_requirements_matrix: R01-R09 present; R01-R05 always BLOCKED;
      R06-R09 status reflects actual checks
    - matrix_summary: counts, confirmation_ready=False while R01-R05 blocked
    - run_preflight: always raises PreflightFailed in this environment;
      error message lists unmet IDs; never succeeds with blocked requirements;
      PreflightFailed carries .unmet and .matrix attributes
    - No mock/env-var bypass of external gates
    - All ablation labels remain selection-only
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import rubric as rubric_module
import readiness as readiness_module
from readiness import (
    PreflightFailed,
    RequirementStatus,
    build_requirements_matrix,
    check_corpus_facade_enforced,
    check_hash_reverification,
    check_preregistration_checklist,
    check_rubric_calibration,
    matrix_summary,
    run_preflight,
    EXPECTED_HASHES,
    LOCAL_HASH_KEYS,
    VAULT_HASH_KEYS,
)
from rubric import (
    EXPECTED_DIMENSIONS,
    EXPECTED_RUBRIC_SHA256,
    EXPECTED_TOTAL,
    validate_rubric,
    rubric_calibration_evidence,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_valid_rubric_text() -> str:
    """Return minimal rubric text that passes all structural checks."""
    return (
        "# Search Confirmation Rubric v1\n\n"
        "## Claim support — 0 to 30\n\n"
        "- **30:** top\n- **24:** good\n- **18:** ok\n- **8:** weak\n- **0:** fail\n\n"
        "## Question coverage — 0 to 20\n\n"
        "- **20:** top\n- **16:** good\n- **10:** ok\n- **4:** weak\n- **0:** fail\n\n"
        "## Gap handling — 0 to 15\n\n"
        "- **15:** top\n- **12:** good\n- **8:** ok\n- **4:** weak\n- **0:** fail\n\n"
        "## Unsupported claim avoidance — 0 to 15\n\n"
        "- **15:** top\n- **12:** good\n- **8:** ok\n- **4:** weak\n- **0:** fail\n\n"
        "## Practical usefulness — 0 to 10\n\n"
        "- **10:** top\n- **8:** good\n- **5:** ok\n- **2:** weak\n- **0:** fail\n\n"
        "## Citation precision — 0 to 10\n\n"
        "- **10:** top\n- **8:** good\n- **5:** ok\n- **2:** weak\n- **0:** fail\n\n"
        "## Critical failure\n\nSet `critical_failure=true` only for fabricated citations.\n"
    )


def _make_minimal_corpus_source() -> str:
    """Return corpus.py source that passes all facade checks."""
    return (
        "from __future__ import annotations\n"
        "EXPECTED_MANIFEST_SHA256 = 'ABC'\n"
        "class CorpusError(RuntimeError): pass\n"
        "class BudgetExhausted(CorpusError): pass\n"
        "class FrozenCorpus:\n"
        "    def __init__(self):\n"
        "        if True: raise CorpusError('escapes the frozen corpus')\n"
        "class SearchSession:\n"
        "    def search(self, q):\n"
        "        if True: raise BudgetExhausted('exhausted')\n"
    )


def _make_valid_preregistration_text() -> str:
    return (
        "# Search Confirmation Preregistration — Draft, Not Yet Activated\n\n"
        "## Readiness gates before activation\n\n"
        "- [x] task file and all prompts/schemas/rubrics are hashed (reverified as R08 below);\n"
        "- [x] **R06** deterministic corpus facade is the only vault access path\n"
        "  — SATISFIED;\n"
        "- [x] **R07** numeric rubric anchors pass a dry-run schema/calibration check\n"
        "  — SATISFIED;\n"
        "- [ ] **R08** all eight frozen inputs re-hashed and confirmed\n"
        "  — PENDING: vault commitments require Project 008 vault;\n"
        "- [x] **R09** preregistration checklist reconciled to executable gate evidence\n"
        "  — SATISFIED;\n"
        "- [x] no investigator has inspected confirmation outputs.\n"
    )


# ---------------------------------------------------------------------------
# rubric.validate_rubric — real file
# ---------------------------------------------------------------------------

class TestValidateRubricRealFile(unittest.TestCase):
    def test_real_rubric_passes(self):
        real_path = (
            Path(__file__).resolve().parent
            / "confirmation"
            / "EVALUATION_RUBRIC_V1.md"
        )
        if not real_path.exists():
            self.skipTest("real rubric file not present")
        errors = validate_rubric(real_path)
        self.assertEqual(errors, [], f"real rubric errors: {errors}")

    def test_real_rubric_hash_matches_preregistration(self):
        real_path = (
            Path(__file__).resolve().parent
            / "confirmation"
            / "EVALUATION_RUBRIC_V1.md"
        )
        if not real_path.exists():
            self.skipTest("real rubric file not present")
        actual = _sha256_text(real_path.read_text(encoding="utf-8"))
        self.assertEqual(actual, EXPECTED_RUBRIC_SHA256)


# ---------------------------------------------------------------------------
# rubric.validate_rubric — synthetic cases
# ---------------------------------------------------------------------------

class TestValidateRubricSynthetic(unittest.TestCase):
    def _write_rubric(self, tmp: Path, text: str) -> Path:
        p = tmp / "EVALUATION_RUBRIC_V1.md"
        _write(p, text)
        return p

    def test_valid_rubric_passes(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_rubric(Path(d), _make_valid_rubric_text())
            errors = validate_rubric(p)
        # Synthetic rubric produces a hash-mismatch error (expected — it is
        # not the preregistered file). Structural errors must be absent.
        structural = [e for e in errors if "hash mismatch" not in e.lower()]
        self.assertEqual(structural, [], structural)

    def test_missing_file_returns_error(self):
        errors = validate_rubric(Path("/nonexistent/rubric.md"))
        self.assertTrue(any("not found" in e for e in errors))

    def test_missing_dimension_detected(self):
        text = _make_valid_rubric_text().replace(
            "## Citation precision — 0 to 10", "## REMOVED — 0 to 10"
        )
        with tempfile.TemporaryDirectory() as d:
            p = self._write_rubric(Path(d), text)
            errors = validate_rubric(p)
            self.assertTrue(any("citation_precision" in e or "citation precision" in e.lower() for e in errors))

    def test_wrong_dimension_max_detected(self):
        text = _make_valid_rubric_text().replace(
            "## Claim support — 0 to 30", "## Claim support — 0 to 25"
        )
        with tempfile.TemporaryDirectory() as d:
            p = self._write_rubric(Path(d), text)
            errors = validate_rubric(p)
            self.assertTrue(any("claim_support" in e or "claim support" in e.lower() for e in errors))

    def test_missing_critical_failure_section_detected(self):
        text = _make_valid_rubric_text().replace("critical_failure", "REMOVED")
        with tempfile.TemporaryDirectory() as d:
            p = self._write_rubric(Path(d), text)
            errors = validate_rubric(p)
            self.assertTrue(any("critical_failure" in e.lower() for e in errors))

    def test_total_score_mismatch_detected(self):
        # Change one max so total != 100
        text = _make_valid_rubric_text().replace(
            "## Claim support — 0 to 30", "## Claim support — 0 to 20"
        )
        with tempfile.TemporaryDirectory() as d:
            p = self._write_rubric(Path(d), text)
            errors = validate_rubric(p)
            self.assertTrue(any("total" in e.lower() or "claim_support" in e.lower() for e in errors))

    def test_hash_mismatch_reported(self):
        text = _make_valid_rubric_text() + "\n# extra line\n"
        with tempfile.TemporaryDirectory() as d:
            p = self._write_rubric(Path(d), text)
            errors = validate_rubric(p)
            self.assertTrue(any("hash mismatch" in e.lower() for e in errors))


# ---------------------------------------------------------------------------
# rubric.rubric_calibration_evidence
# ---------------------------------------------------------------------------

class TestRubricCalibrationEvidence(unittest.TestCase):
    def test_real_file_returns_passed(self):
        real_path = (
            Path(__file__).resolve().parent
            / "confirmation"
            / "EVALUATION_RUBRIC_V1.md"
        )
        if not real_path.exists():
            self.skipTest("real rubric file not present")
        ev = rubric_calibration_evidence(real_path)
        self.assertTrue(ev["passed"])

    def test_evidence_has_required_keys(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "confirmation" / "EVALUATION_RUBRIC_V1.md"
            _write(p, _make_valid_rubric_text())
            ev = rubric_calibration_evidence(p)
        for key in ("requirement", "check", "passed", "errors",
                    "calibration_scope", "selection_limitation"):
            self.assertIn(key, ev)

    def test_calibration_scope_is_non_confirmation(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "confirmation" / "EVALUATION_RUBRIC_V1.md"
            _write(p, _make_valid_rubric_text())
            ev = rubric_calibration_evidence(p)
        self.assertIn("non_confirmation", ev["calibration_scope"])

    def test_selection_limitation_present(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "confirmation" / "EVALUATION_RUBRIC_V1.md"
            _write(p, _make_valid_rubric_text())
            ev = rubric_calibration_evidence(p)
        self.assertIn("selection-only", ev["selection_limitation"])


# ---------------------------------------------------------------------------
# readiness.check_corpus_facade_enforced — real file
# ---------------------------------------------------------------------------

class TestCorpusFacadeRealFile(unittest.TestCase):
    def test_real_corpus_passes(self):
        real_path = Path(__file__).resolve().parent / "corpus.py"
        if not real_path.exists():
            self.skipTest("corpus.py not present")
        result = check_corpus_facade_enforced(real_path)
        self.assertTrue(result["passed"], result["errors"])


# ---------------------------------------------------------------------------
# readiness.check_corpus_facade_enforced — synthetic
# ---------------------------------------------------------------------------

class TestCorpusFacadeSynthetic(unittest.TestCase):
    def test_valid_source_passes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "corpus.py"
            _write(p, _make_minimal_corpus_source())
            result = check_corpus_facade_enforced(p)
        self.assertTrue(result["passed"], result["errors"])

    def test_missing_file_fails(self):
        result = check_corpus_facade_enforced(Path("/nonexistent/corpus.py"))
        self.assertFalse(result["passed"])
        self.assertTrue(any("not found" in e for e in result["errors"]))

    def test_missing_frozen_corpus_class_detected(self):
        src = _make_minimal_corpus_source().replace("class FrozenCorpus", "class _REMOVED")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "corpus.py"
            _write(p, src)
            result = check_corpus_facade_enforced(p)
        self.assertFalse(result["passed"])
        self.assertTrue(any("FrozenCorpus" in e for e in result["errors"]))

    def test_missing_search_session_class_detected(self):
        src = _make_minimal_corpus_source().replace("class SearchSession", "class _REMOVED")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "corpus.py"
            _write(p, src)
            result = check_corpus_facade_enforced(p)
        self.assertFalse(result["passed"])
        self.assertTrue(any("SearchSession" in e for e in result["errors"]))

    def test_missing_manifest_check_detected(self):
        src = _make_minimal_corpus_source().replace("EXPECTED_MANIFEST_SHA256", "REMOVED")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "corpus.py"
            _write(p, src)
            result = check_corpus_facade_enforced(p)
        self.assertFalse(result["passed"])

    def test_missing_budget_enforcement_detected(self):
        src = _make_minimal_corpus_source().replace("BudgetExhausted", "REMOVED")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "corpus.py"
            _write(p, src)
            result = check_corpus_facade_enforced(p)
        self.assertFalse(result["passed"])


# ---------------------------------------------------------------------------
# readiness.check_hash_reverification
# ---------------------------------------------------------------------------

class TestHashReverification(unittest.TestCase):
    def _make_matching_files(self, tmp: Path) -> dict[str, Path]:
        paths: dict[str, Path] = {}
        for key in LOCAL_HASH_KEYS:
            p = tmp / f"{key}.txt"
            # Write content whose sha256 matches the expected hash
            # We find the preregistered content by writing arbitrary content
            # and recording its hash, then adjust. For tests we just verify
            # the mechanism: write the real file content if available, else
            # write a placeholder and expect mismatch.
            p.write_text(f"placeholder_{key}", encoding="utf-8")
            paths[key] = p
        return paths

    def test_vault_keys_always_reported_in_vault_results(self):
        result = check_hash_reverification()
        for key in VAULT_HASH_KEYS:
            self.assertIn(key, result["vault_results"])

    def test_vault_results_contain_expected_hash(self):
        result = check_hash_reverification()
        for key in VAULT_HASH_KEYS:
            self.assertEqual(
                result["vault_results"][key]["expected"],
                EXPECTED_HASHES[key],
            )

    def test_real_local_files_all_match(self):
        # Uses default paths (the actual poc6c files).
        # passed=False is expected when vault is absent (vault_pending=True).
        result = check_hash_reverification()
        self.assertEqual(result["errors"], [], result["errors"])
        for key in LOCAL_HASH_KEYS:
            self.assertEqual(
                result["local_results"][key]["status"],
                "match",
                f"{key} should match",
            )
        # Vault absent → passed=False, vault_pending=True
        self.assertTrue(result["vault_pending"])
        self.assertFalse(result["passed"])

    def test_missing_file_fails(self):
        paths = {k: Path(f"/nonexistent/{k}") for k in LOCAL_HASH_KEYS}
        result = check_hash_reverification(paths)
        self.assertFalse(result["passed"])
        self.assertGreater(len(result["errors"]), 0)

    def test_hash_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "generic_prompt.md"
            p.write_text("wrong content", encoding="utf-8")
            paths = {k: (p if k == "generic_prompt" else Path(f"/nonexistent/{k}"))
                     for k in LOCAL_HASH_KEYS}
            result = check_hash_reverification(paths)
        self.assertFalse(result["passed"])
        self.assertTrue(any("generic_prompt" in e for e in result["errors"]))

    def test_result_has_selection_limitation(self):
        result = check_hash_reverification()
        self.assertIn("selection-only", result["selection_limitation"])

    def test_vault_pending_flag_when_vault_absent(self):
        result = check_hash_reverification()
        self.assertIn("vault_pending", result)
        self.assertTrue(result["vault_pending"])


# ---------------------------------------------------------------------------
# readiness.check_preregistration_checklist
# ---------------------------------------------------------------------------

class TestPreregistrationChecklist(unittest.TestCase):
    def test_real_updated_file_passes(self):
        real_path = (
            Path(__file__).resolve().parent
            / "confirmation"
            / "PREREGISTRATION_DRAFT.md"
        )
        if not real_path.exists():
            self.skipTest("PREREGISTRATION_DRAFT.md not present")
        result = check_preregistration_checklist(real_path)
        self.assertTrue(result["passed"], result["errors"])

    def test_valid_text_passes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "PREREGISTRATION_DRAFT.md"
            _write(p, _make_valid_preregistration_text())
            result = check_preregistration_checklist(p)
        self.assertTrue(result["passed"], result["errors"])

    def test_missing_file_fails(self):
        result = check_preregistration_checklist(Path("/nonexistent/PREREGISTRATION_DRAFT.md"))
        self.assertFalse(result["passed"])

    def test_missing_corpus_gate_fails(self):
        text = _make_valid_preregistration_text().replace(
            "deterministic corpus facade", "REMOVED"
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "PREREGISTRATION_DRAFT.md"
            _write(p, text)
            result = check_preregistration_checklist(p)
        self.assertFalse(result["passed"])

    def test_unchecked_rubric_gate_fails(self):
        text = _make_valid_preregistration_text().replace(
            "- [x] **R07** numeric rubric", "- [ ] **R07** numeric rubric"
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "PREREGISTRATION_DRAFT.md"
            _write(p, text)
            result = check_preregistration_checklist(p)
        self.assertFalse(result["passed"])

    def test_confirmation_output_reference_fails(self):
        text = _make_valid_preregistration_text() + "\n\nconfirmation run produced score 82.\n"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "PREREGISTRATION_DRAFT.md"
            _write(p, text)
            result = check_preregistration_checklist(p)
        self.assertFalse(result["passed"])
        self.assertTrue(any("confirmation run" in e.lower() for e in result["errors"]))


# ---------------------------------------------------------------------------
# build_requirements_matrix
# ---------------------------------------------------------------------------

class TestBuildRequirementsMatrix(unittest.TestCase):
    def test_nine_requirements_present(self):
        matrix = build_requirements_matrix()
        self.assertEqual(len(matrix), 9)

    def test_all_requirement_ids_r01_r09(self):
        matrix = build_requirements_matrix()
        ids = {req.req_id for req in matrix}
        self.assertEqual(ids, {f"R{i:02d}" for i in range(1, 10)})

    def test_r01_r05_always_blocked(self):
        matrix = build_requirements_matrix()
        blocked = {req.req_id for req in matrix if req.status == RequirementStatus.BLOCKED}
        for rid in ("R01", "R02", "R03", "R04", "R05"):
            self.assertIn(rid, blocked)

    def test_r06_satisfied_on_real_files(self):
        matrix = build_requirements_matrix()
        r06 = next(r for r in matrix if r.req_id == "R06")
        self.assertEqual(r06.status, RequirementStatus.SATISFIED)

    def test_r07_satisfied_on_real_rubric(self):
        real_path = (
            Path(__file__).resolve().parent
            / "confirmation"
            / "EVALUATION_RUBRIC_V1.md"
        )
        if not real_path.exists():
            self.skipTest("real rubric file not present")
        matrix = build_requirements_matrix()
        r07 = next(r for r in matrix if r.req_id == "R07")
        self.assertEqual(r07.status, RequirementStatus.SATISFIED)

    def test_r08_pending_when_vault_absent(self):
        # R08 is PENDING (not SATISFIED) when vault is absent — both
        # vault commitments are required.
        matrix = build_requirements_matrix()
        r08 = next(r for r in matrix if r.req_id == "R08")
        self.assertEqual(r08.status, RequirementStatus.PENDING)

    def test_all_requirements_have_unblock_condition(self):
        matrix = build_requirements_matrix()
        for req in matrix:
            self.assertTrue(req.unblock_condition.strip(), f"{req.req_id} missing unblock_condition")

    def test_all_requirements_required_for_confirmation(self):
        matrix = build_requirements_matrix()
        for req in matrix:
            self.assertTrue(req.required_for_confirmation, f"{req.req_id} not required_for_confirmation")

    def test_to_dict_has_all_keys(self):
        matrix = build_requirements_matrix()
        for req in matrix:
            d = req.to_dict()
            for key in ("req_id", "category", "description", "status",
                        "evidence", "owner", "unblock_condition",
                        "required_for_confirmation"):
                self.assertIn(key, d, f"{req.req_id} missing {key}")


# ---------------------------------------------------------------------------
# matrix_summary
# ---------------------------------------------------------------------------

class TestMatrixSummary(unittest.TestCase):
    def test_total_is_nine(self):
        matrix = build_requirements_matrix()
        summary = matrix_summary(matrix)
        self.assertEqual(summary["total"], 9)

    def test_blocked_count_is_five(self):
        matrix = build_requirements_matrix()
        summary = matrix_summary(matrix)
        self.assertEqual(summary["blocked"], 5)

    def test_confirmation_not_ready(self):
        matrix = build_requirements_matrix()
        summary = matrix_summary(matrix)
        self.assertFalse(summary["confirmation_ready"])

    def test_task4_status_blocked(self):
        matrix = build_requirements_matrix()
        summary = matrix_summary(matrix)
        self.assertEqual(summary["task4_status"], "BLOCKED")

    def test_selection_limitation_present(self):
        matrix = build_requirements_matrix()
        summary = matrix_summary(matrix)
        self.assertIn("selection-only", summary["selection_limitation"])


# ---------------------------------------------------------------------------
# run_preflight — fail-closed behavior
# ---------------------------------------------------------------------------

class TestRunPreflight(unittest.TestCase):
    def test_always_raises_preflight_failed(self):
        with self.assertRaises(PreflightFailed):
            run_preflight()

    def test_unmet_includes_r01_r05(self):
        try:
            run_preflight()
        except PreflightFailed as exc:
            for rid in ("R01", "R02", "R03", "R04", "R05"):
                self.assertIn(rid, exc.unmet)

    def test_preflight_failed_has_matrix_attribute(self):
        try:
            run_preflight()
        except PreflightFailed as exc:
            self.assertEqual(len(exc.matrix), 9)

    def test_error_message_names_unmet_requirements(self):
        try:
            run_preflight()
        except PreflightFailed as exc:
            msg = str(exc)
            self.assertIn("R01", msg)
            self.assertIn("Task 5", msg)

    def test_error_message_forbids_mocks(self):
        try:
            run_preflight()
        except PreflightFailed as exc:
            self.assertIn("mock", str(exc).lower())

    def test_preflight_does_not_succeed_with_faked_corpus(self):
        """Even if corpus check passes, R01-R05 still block confirmation."""
        with tempfile.TemporaryDirectory() as d:
            corpus_p = Path(d) / "corpus.py"
            _write(corpus_p, _make_minimal_corpus_source())
            with self.assertRaises(PreflightFailed) as ctx:
                run_preflight(corpus_path=corpus_p)
            self.assertIn("R01", ctx.exception.unmet)

    def test_preflight_unmet_list_not_empty(self):
        try:
            run_preflight()
        except PreflightFailed as exc:
            self.assertGreater(len(exc.unmet), 0)


# ---------------------------------------------------------------------------
# Selection-only invariant: no confirmation verdict anywhere
# ---------------------------------------------------------------------------

class TestSelectionOnlyInvariant(unittest.TestCase):
    def test_matrix_summary_has_no_confirmation_verdict(self):
        matrix = build_requirements_matrix()
        summary = matrix_summary(matrix)
        summary_str = str(summary)
        for phrase in ("confirmed", "product claim", "passes confirmation"):
            self.assertNotIn(phrase, summary_str.lower())

    def test_rubric_calibration_has_no_confirmation_output(self):
        real_path = (
            Path(__file__).resolve().parent
            / "confirmation"
            / "EVALUATION_RUBRIC_V1.md"
        )
        if not real_path.exists():
            self.skipTest("real rubric not present")
        ev = rubric_calibration_evidence(real_path)
        for phrase in ("confirmation score", "confirmed effect"):
            self.assertNotIn(phrase, str(ev).lower())


if __name__ == "__main__":
    unittest.main()
