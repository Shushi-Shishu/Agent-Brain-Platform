"""
Tests for ablation.py — Task 3 selection ablation study.

All tests use stub adapters and stub sessions.
No LLM calls, no corpus access.

Coverage:
- AblationArm enum completeness
- AblationMetrics: support_rate, coverage_rate, to_dict
- PassthroughLedger / PassthroughCritic / PassthroughStopper behavioral contracts
- Block assembly: each arm gets exactly the right blocks
- AblationController.run: output schema, metrics correctness
- Per-arm behavioral guarantees:
    GENERIC: never vetoes, always runs to budget or adapter stop
    LEDGER: records claims but never vetoes
    CRITIC: vetoes on unsupported claims; records veto events
    STOPPER: stops on quality gates without critic
    FULL: same behavior as SearchController (ledger + critic + stopper)
- compare_arms: aggregation, limitation disclaimer
- Budget enforcement: no arm exceeds MAX_SEARCH/READ
- Task isolation: separate ControllerState per run
"""

from __future__ import annotations

import unittest
from typing import Any

from controller import (
    ClaimStatus,
    ControllerState,
    CriticVeto,
    EvidenceCritic,
    EvidenceLedger,
    Facet,
    FacetStatus,
    MAX_READ_CALLS,
    MAX_SEARCH_CALLS,
    QualityProtectedStopper,
    RunStatus,
    StopReason,
)
from ablation import (
    AblationArm,
    AblationController,
    AblationMetrics,
    _PassthroughCritic,
    _PassthroughLedger,
    _PassthroughStopper,
    compare_arms,
)
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Shared stubs
# ---------------------------------------------------------------------------

class _StubSession:
    def __init__(self, *, max_search=MAX_SEARCH_CALLS, max_read=MAX_READ_CALLS):
        self.max_search = max_search
        self.max_read = max_read
        self.search_calls = 0
        self.read_calls = 0

    def search(self, query: str, **_kw) -> list:
        self.search_calls += 1
        return [MagicMock(path="note/A.md")]

    def read_note(self, path: str) -> dict:
        self.read_calls += 1
        return {"path": path, "content": "X is Y.", "content_sha256": "ABCD"}


class _SinglePassAdapter:
    """Searches once, reads once, then stops. Provides one supported claim."""

    def decompose_question(self, q: str) -> list[str]:
        return ["What is X?"]

    def select_next_query(self, state: ControllerState) -> str | None:
        return "X" if state.search_calls_used == 0 else None

    def select_note_to_read(self, state: ControllerState, hits: list) -> str | None:
        if state.read_calls_used == 0 and hits:
            return hits[0]["path"]
        return None

    def extract_claims(self, state: ControllerState, content: str, path: str) -> list[dict]:
        return [{"sentence": "X is Y.", "status": "supported", "excerpt": "X is Y."}]

    def synthesize_answer(self, state: ControllerState) -> dict:
        return {
            "answer": "X is Y.",
            "citations": [{"path": "note/A.md", "supporting_excerpt": "X is Y."}],
            "declared_gaps": [],
            "run_status": "answer",
        }


class _UnsupportedClaimAdapter(_SinglePassAdapter):
    """Provides one unsupported claim — triggers critic veto in CRITIC/FULL arms."""

    def extract_claims(self, state: ControllerState, content: str, path: str) -> list[dict]:
        return [{"sentence": "X is definitely Z.", "status": "unsupported", "excerpt": None}]


class _NoQueryAdapter:
    """Returns no search query — controller stops on low VOI immediately."""

    def decompose_question(self, q: str) -> list[str]:
        return ["F1"]

    def select_next_query(self, state: ControllerState) -> str | None:
        return None

    def select_note_to_read(self, state: ControllerState, hits: list) -> str | None:
        return None

    def extract_claims(self, state: ControllerState, content: str, path: str) -> list[dict]:
        return []

    def synthesize_answer(self, state: ControllerState) -> dict:
        return {"answer": "Nothing.", "citations": [], "declared_gaps": ["F1"], "run_status": "abstain"}


def _make_controller(arm: AblationArm, adapter=None, max_search=4, max_read=6):
    session = _StubSession(max_search=max_search, max_read=max_read)
    ctrl = AblationController(
        arm,
        adapter or _SinglePassAdapter(),
        session,
        max_search_calls=max_search,
        max_read_calls=max_read,
    )
    return ctrl, session


# ---------------------------------------------------------------------------
# AblationArm
# ---------------------------------------------------------------------------

class TestAblationArm(unittest.TestCase):
    def test_five_arms_defined(self):
        self.assertEqual(len(AblationArm), 5)

    def test_arm_values(self):
        expected = {"generic", "ledger_only", "ledger_plus_critic", "stopper_only", "full_candidate2"}
        self.assertEqual({a.value for a in AblationArm}, expected)


# ---------------------------------------------------------------------------
# AblationMetrics
# ---------------------------------------------------------------------------

class TestAblationMetrics(unittest.TestCase):
    def _make(self, supported=3, unsupported=1, facets_resolved=2, facets_total=3):
        return AblationMetrics(
            arm=AblationArm.FULL,
            task_id="T1",
            supported_claim_count=supported,
            unsupported_claim_count=unsupported,
            facets_resolved=facets_resolved,
            facets_total=facets_total,
        )

    def test_support_rate(self):
        m = self._make(supported=3, unsupported=1)
        self.assertAlmostEqual(m.support_rate(), 0.75)

    def test_support_rate_zero_claims(self):
        m = self._make(supported=0, unsupported=0)
        self.assertEqual(m.support_rate(), 0.0)

    def test_coverage_rate(self):
        m = self._make(facets_resolved=2, facets_total=4)
        self.assertAlmostEqual(m.coverage_rate(), 0.5)

    def test_coverage_rate_zero_facets(self):
        m = self._make(facets_resolved=0, facets_total=0)
        self.assertEqual(m.coverage_rate(), 0.0)

    def test_to_dict_has_required_keys(self):
        m = self._make()
        d = m.to_dict()
        for key in ("arm", "task_id", "supported_claims", "unsupported_claims",
                    "coverage_rate", "support_rate", "stop_reason",
                    "hard_budget_stop", "answer_ready"):
            self.assertIn(key, d)

    def test_to_dict_arm_value(self):
        m = self._make()
        self.assertEqual(m.to_dict()["arm"], AblationArm.FULL.value)


# ---------------------------------------------------------------------------
# Passthrough stubs
# ---------------------------------------------------------------------------

class TestPassthroughLedger(unittest.TestCase):
    def _make(self):
        state = ControllerState(question="Q")
        return _PassthroughLedger(state), state

    def test_record_claim_noop(self):
        ledger, state = self._make()
        ledger.record_claim("X.", ClaimStatus.UNSUPPORTED)
        self.assertEqual(state.claims, [])

    def test_unsupported_claims_empty(self):
        ledger, _ = self._make()
        self.assertEqual(ledger.unsupported_claims(), [])

    def test_all_claims_resolved_always_true(self):
        ledger, _ = self._make()
        self.assertTrue(ledger.all_claims_resolved())


class TestPassthroughCritic(unittest.TestCase):
    def test_never_raises(self):
        state = ControllerState(question="Q")
        critic = _PassthroughCritic(state)
        critic.check()  # must not raise

    def test_records_passed_event(self):
        state = ControllerState(question="Q")
        critic = _PassthroughCritic(state)
        critic.check()
        self.assertTrue(state.decision_events[-1]["passed"])


class TestPassthroughStopper(unittest.TestCase):
    def test_should_stop_always_false(self):
        state = ControllerState(question="Q")
        stopper = _PassthroughStopper(state)
        stop, _ = stopper.should_stop(critic_passed=True)
        self.assertFalse(stop)
        stop, _ = stopper.should_stop(critic_passed=False)
        self.assertFalse(stop)

    def test_record_stop_sets_state(self):
        state = ControllerState(question="Q")
        stopper = _PassthroughStopper(state)
        stopper.record_stop(StopReason.LOW_VOI)
        self.assertEqual(state.stop_reason, StopReason.LOW_VOI)


# ---------------------------------------------------------------------------
# Block assembly — each arm gets the right components
# ---------------------------------------------------------------------------

class TestBlockAssembly(unittest.TestCase):
    def _blocks(self, arm: AblationArm):
        state = ControllerState(question="Q")
        ctrl, _ = _make_controller(arm)
        ledger = ctrl._make_ledger(state)
        critic = ctrl._make_critic(state, ledger)
        stopper = ctrl._make_stopper(state)
        return ledger, critic, stopper

    def test_generic_all_passthroughs(self):
        ledger, critic, stopper = self._blocks(AblationArm.GENERIC)
        self.assertIsInstance(ledger, _PassthroughLedger)
        self.assertIsInstance(critic, _PassthroughCritic)
        self.assertIsInstance(stopper, _PassthroughStopper)

    def test_ledger_only(self):
        ledger, critic, stopper = self._blocks(AblationArm.LEDGER)
        self.assertIsInstance(ledger, EvidenceLedger)
        self.assertIsInstance(critic, _PassthroughCritic)
        self.assertIsInstance(stopper, _PassthroughStopper)

    def test_critic_arm(self):
        ledger, critic, stopper = self._blocks(AblationArm.CRITIC)
        self.assertIsInstance(ledger, EvidenceLedger)
        self.assertIsInstance(critic, EvidenceCritic)
        self.assertIsInstance(stopper, _PassthroughStopper)

    def test_stopper_only(self):
        ledger, critic, stopper = self._blocks(AblationArm.STOPPER)
        self.assertIsInstance(ledger, _PassthroughLedger)
        self.assertIsInstance(critic, _PassthroughCritic)
        self.assertIsInstance(stopper, QualityProtectedStopper)

    def test_full_all_real(self):
        ledger, critic, stopper = self._blocks(AblationArm.FULL)
        self.assertIsInstance(ledger, EvidenceLedger)
        self.assertIsInstance(critic, EvidenceCritic)
        self.assertIsInstance(stopper, QualityProtectedStopper)


# ---------------------------------------------------------------------------
# AblationController.run — output schema
# ---------------------------------------------------------------------------

class TestAblationControllerOutputSchema(unittest.TestCase):
    def _run_arm(self, arm: AblationArm, adapter=None):
        ctrl, session = _make_controller(arm, adapter)
        return ctrl.run("T1", "What is X?")

    def test_output_has_required_keys(self):
        output, _ = self._run_arm(AblationArm.FULL)
        for key in ("schema_version", "arm", "task_id", "behavior",
                    "answer", "citations", "declared_gaps", "operational_trace"):
            self.assertIn(key, output)

    def test_arm_value_in_output(self):
        for arm in AblationArm:
            output, _ = self._run_arm(arm)
            self.assertEqual(output["arm"], arm.value)

    def test_task_id_in_output(self):
        output, _ = self._run_arm(AblationArm.GENERIC)
        self.assertEqual(output["task_id"], "T1")

    def test_decision_events_recorded(self):
        output, _ = self._run_arm(AblationArm.FULL)
        self.assertGreater(len(output["operational_trace"]["decision_events"]), 0)


# ---------------------------------------------------------------------------
# Per-arm behavioral guarantees
# ---------------------------------------------------------------------------

class TestGenericArmBehavior(unittest.TestCase):
    def test_never_vetoes(self):
        ctrl, _ = _make_controller(AblationArm.GENERIC, _UnsupportedClaimAdapter())
        output, metrics = ctrl.run("T1", "What is X?")
        self.assertEqual(metrics.critic_veto_count, 0)

    def test_runs_to_adapter_stop(self):
        ctrl, session = _make_controller(AblationArm.GENERIC)
        output, metrics = ctrl.run("T1", "What is X?")
        self.assertIn(metrics.stop_reason, [r.value for r in StopReason])


class TestLedgerArmBehavior(unittest.TestCase):
    def test_records_claims_in_state(self):
        ctrl, _ = _make_controller(AblationArm.LEDGER)
        output, metrics = ctrl.run("T1", "What is X?")
        self.assertGreater(metrics.supported_claim_count + metrics.unsupported_claim_count, 0)

    def test_never_vetoes(self):
        ctrl, _ = _make_controller(AblationArm.LEDGER, _UnsupportedClaimAdapter())
        output, metrics = ctrl.run("T1", "What is X?")
        self.assertEqual(metrics.critic_veto_count, 0)


class TestCriticArmBehavior(unittest.TestCase):
    def test_veto_recorded_on_unsupported_claim(self):
        ctrl, _ = _make_controller(AblationArm.CRITIC, _UnsupportedClaimAdapter())
        output, metrics = ctrl.run("T1", "What is X?")
        self.assertGreater(metrics.critic_veto_count, 0)

    def test_no_veto_on_supported_claim(self):
        ctrl, _ = _make_controller(AblationArm.CRITIC, _SinglePassAdapter())
        output, metrics = ctrl.run("T1", "What is X?")
        self.assertEqual(metrics.critic_veto_count, 0)


class TestStopperArmBehavior(unittest.TestCase):
    def test_stopper_records_stop_reason(self):
        ctrl, _ = _make_controller(AblationArm.STOPPER)
        output, metrics = ctrl.run("T1", "What is X?")
        self.assertNotEqual(metrics.stop_reason, "")

    def test_no_veto_even_with_unsupported_claims(self):
        ctrl, _ = _make_controller(AblationArm.STOPPER, _UnsupportedClaimAdapter())
        output, metrics = ctrl.run("T1", "What is X?")
        self.assertEqual(metrics.critic_veto_count, 0)


class TestFullArmBehavior(unittest.TestCase):
    def test_full_produces_answer(self):
        ctrl, _ = _make_controller(AblationArm.FULL)
        output, metrics = ctrl.run("T1", "What is X?")
        self.assertEqual(output["behavior"], RunStatus.ANSWER.value)

    def test_full_records_veto_on_unsupported(self):
        ctrl, _ = _make_controller(AblationArm.FULL, _UnsupportedClaimAdapter())
        output, metrics = ctrl.run("T1", "What is X?")
        self.assertGreater(metrics.critic_veto_count, 0)

    def test_full_stop_reason_set(self):
        ctrl, _ = _make_controller(AblationArm.FULL)
        output, metrics = ctrl.run("T1", "What is X?")
        self.assertNotEqual(metrics.stop_reason, "")


# ---------------------------------------------------------------------------
# Budget enforcement — no arm exceeds allocated calls
# ---------------------------------------------------------------------------

class TestBudgetEnforcement(unittest.TestCase):
    def test_no_arm_exceeds_search_budget(self):
        for arm in AblationArm:
            ctrl, session = _make_controller(arm, max_search=2, max_read=2)
            ctrl.run("T1", "What is X?")
            self.assertLessEqual(session.search_calls, 2, f"arm={arm}")

    def test_no_arm_exceeds_read_budget(self):
        for arm in AblationArm:
            ctrl, session = _make_controller(arm, max_search=2, max_read=2)
            ctrl.run("T1", "What is X?")
            self.assertLessEqual(session.read_calls, 2, f"arm={arm}")


# ---------------------------------------------------------------------------
# Task isolation — separate state per run
# ---------------------------------------------------------------------------

class TestTaskIsolation(unittest.TestCase):
    def test_two_runs_have_independent_state(self):
        ctrl, _ = _make_controller(AblationArm.FULL)
        out1, m1 = ctrl.run("T1", "What is A?")
        ctrl2, _ = _make_controller(AblationArm.FULL)
        out2, m2 = ctrl2.run("T2", "What is B?")
        self.assertEqual(m1.task_id, "T1")
        self.assertEqual(m2.task_id, "T2")

    def test_outputs_do_not_share_decision_events(self):
        ctrl1, _ = _make_controller(AblationArm.FULL)
        ctrl2, _ = _make_controller(AblationArm.FULL)
        out1, _ = ctrl1.run("T1", "A?")
        out2, _ = ctrl2.run("T2", "B?")
        events1 = out1["operational_trace"]["decision_events"]
        events2 = out2["operational_trace"]["decision_events"]
        self.assertIsNot(events1, events2)


# ---------------------------------------------------------------------------
# compare_arms
# ---------------------------------------------------------------------------

class TestCompareArms(unittest.TestCase):
    def _make_metrics(self, arm: AblationArm, supported=2, unsupported=0,
                      resolved=1, total=1, answer_ready=True) -> AblationMetrics:
        return AblationMetrics(
            arm=arm,
            task_id="T1",
            supported_claim_count=supported,
            unsupported_claim_count=unsupported,
            facets_resolved=resolved,
            facets_total=total,
            answer_ready=answer_ready,
            stop_reason=StopReason.ALL_FACETS_RESOLVED.value,
        )

    def test_report_contains_each_arm(self):
        results = [
            (arm, [self._make_metrics(arm)]) for arm in AblationArm
        ]
        report = compare_arms(results)
        for arm in AblationArm:
            self.assertIn(arm.value, report["arms"])

    def test_report_has_disclaimer(self):
        report = compare_arms([])
        self.assertIn("limitations", report)
        self.assertTrue(any("confirmation" in s for s in report["limitations"]))

    def test_status_is_selection_only(self):
        report = compare_arms([])
        self.assertIn("selection_only", report["status"])

    def test_mean_support_rate_correct(self):
        m1 = self._make_metrics(AblationArm.FULL, supported=4, unsupported=0)
        m2 = self._make_metrics(AblationArm.FULL, supported=2, unsupported=2)
        report = compare_arms([(AblationArm.FULL, [m1, m2])])
        self.assertAlmostEqual(
            report["arms"][AblationArm.FULL.value]["mean_support_rate"],
            0.75,  # (1.0 + 0.5) / 2
        )

    def test_empty_arm_skipped(self):
        report = compare_arms([(AblationArm.GENERIC, [])])
        self.assertNotIn(AblationArm.GENERIC.value, report["arms"])


if __name__ == "__main__":
    unittest.main()
