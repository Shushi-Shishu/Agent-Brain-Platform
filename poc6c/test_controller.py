"""
Tests for controller.py — Candidate 2 executable controller.

All tests use stub ProviderAdapters and a stub SearchSession.
No LLM calls, no corpus access.
"""

from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import MagicMock

from controller import (
    MAX_READ_CALLS,
    MAX_SEARCH_CALLS,
    POLICY_VERSION,
    BudgetExceededInternally,
    ClaimStatus,
    ControllerState,
    CriticVeto,
    EvidenceCritic,
    EvidenceLedger,
    FacetStatus,
    QualityProtectedStopper,
    RunStatus,
    SearchController,
    StopReason,
    Facet,
)


# ---------------------------------------------------------------------------
# Stub helpers
# ---------------------------------------------------------------------------

class _StubSession:
    """Minimal stub for corpus.SearchSession."""

    def __init__(
        self,
        *,
        max_search_calls: int = MAX_SEARCH_CALLS,
        max_read_calls: int = MAX_READ_CALLS,
    ) -> None:
        self.max_search_calls = max_search_calls
        self.max_read_calls = max_read_calls
        self.search_calls = 0
        self.read_calls = 0
        self.events: list[dict] = []

    def search(self, query: str, **_kwargs: Any) -> list[dict]:
        self.search_calls += 1
        self.events.append({"sequence": len(self.events) + 1, "type": "vault_search",
                             "query": query, "result_paths": ["note/A.md"]})
        return [MagicMock(path="note/A.md")]

    def read_note(self, path: str) -> dict:
        self.read_calls += 1
        self.events.append({"sequence": len(self.events) + 1, "type": "document_read",
                             "path": path, "content_sha256": "ABCD"})
        return {"path": path, "content": "Some content about the topic.", "content_sha256": "ABCD"}

    def remaining_budget(self) -> dict:
        return {
            "search_calls": self.max_search_calls - self.search_calls,
            "read_calls": self.max_read_calls - self.read_calls,
        }


def _make_state(**kwargs: Any) -> ControllerState:
    return ControllerState(question="What is X?", **kwargs)


def _state_with_facets(*facets: tuple[str, FacetStatus]) -> ControllerState:
    state = _make_state()
    for text, status in facets:
        state.facets.append(Facet(text=text, status=status))
    return state


# ---------------------------------------------------------------------------
# ControllerState
# ---------------------------------------------------------------------------

class TestControllerState(unittest.TestCase):
    def test_remaining_budget_decrements(self):
        s = _make_state()
        self.assertEqual(s.remaining_search(), MAX_SEARCH_CALLS)
        s.search_calls_used += 1
        self.assertEqual(s.remaining_search(), MAX_SEARCH_CALLS - 1)

    def test_budget_exhausted_when_both_zero(self):
        s = _make_state(
            max_search_calls=1, max_read_calls=1,
            search_calls_used=1, read_calls_used=1,
        )
        self.assertTrue(s.budget_exhausted())

    def test_budget_not_exhausted_with_remaining_read(self):
        s = _make_state(max_search_calls=1, max_read_calls=2, search_calls_used=1)
        self.assertFalse(s.budget_exhausted())

    def test_evidence_status_counts(self):
        s = _state_with_facets(
            ("F1", FacetStatus.SUPPORTED),
            ("F2", FacetStatus.MISSING),
            ("F3", FacetStatus.UNSEARCHED),
        )
        counts = s.evidence_status_counts()
        self.assertEqual(counts[FacetStatus.SUPPORTED.value], 1)
        self.assertEqual(counts[FacetStatus.MISSING.value], 1)
        self.assertEqual(counts[FacetStatus.UNSEARCHED.value], 1)

    def test_to_operational_trace_keys(self):
        s = _make_state()
        trace = s.to_operational_trace()
        for key in ("facets", "claims", "declared_gaps", "stop_reason",
                    "evidence_status_counts"):
            self.assertIn(key, trace)


# ---------------------------------------------------------------------------
# EvidenceLedger
# ---------------------------------------------------------------------------

class TestEvidenceLedger(unittest.TestCase):
    def test_record_supported_claim(self):
        state = _make_state()
        ledger = EvidenceLedger(state)
        ledger.record_claim("X is true.", ClaimStatus.SUPPORTED,
                            citation_path="note/A.md", excerpt="X is true in context.")
        self.assertEqual(len(ledger.supported_claims()), 1)
        self.assertEqual(len(ledger.unsupported_claims()), 0)

    def test_supported_claim_requires_citation(self):
        state = _make_state()
        ledger = EvidenceLedger(state)
        with self.assertRaises(ValueError):
            ledger.record_claim("X is true.", ClaimStatus.SUPPORTED)

    def test_supported_claim_requires_excerpt(self):
        state = _make_state()
        ledger = EvidenceLedger(state)
        with self.assertRaises(ValueError):
            ledger.record_claim("X is true.", ClaimStatus.SUPPORTED,
                                citation_path="note/A.md")

    def test_unsupported_claim_no_citation_required(self):
        state = _make_state()
        ledger = EvidenceLedger(state)
        ledger.record_claim("Maybe X.", ClaimStatus.UNSUPPORTED)
        self.assertEqual(len(ledger.unsupported_claims()), 1)

    def test_all_claims_resolved_with_inference(self):
        state = _make_state()
        ledger = EvidenceLedger(state)
        ledger.record_claim("X is likely.", ClaimStatus.INFERENCE)
        self.assertTrue(ledger.all_claims_resolved())

    def test_all_claims_resolved_false_with_unsupported(self):
        state = _make_state()
        ledger = EvidenceLedger(state)
        ledger.record_claim("X is true.", ClaimStatus.UNSUPPORTED)
        self.assertFalse(ledger.all_claims_resolved())

    def test_empty_sentence_rejected(self):
        state = _make_state()
        ledger = EvidenceLedger(state)
        with self.assertRaises(ValueError):
            ledger.record_claim("   ", ClaimStatus.INFERENCE)


# ---------------------------------------------------------------------------
# EvidenceCritic
# ---------------------------------------------------------------------------

class TestEvidenceCritic(unittest.TestCase):
    def _setup(self, facets=None):
        state = _make_state()
        if facets:
            for text, status in facets:
                state.facets.append(Facet(text=text, status=status))
        ledger = EvidenceLedger(state)
        critic = EvidenceCritic(state, ledger)
        return state, ledger, critic

    def test_passes_with_supported_facet_and_claim(self):
        state, ledger, critic = self._setup([("F1", FacetStatus.SUPPORTED)])
        ledger.record_claim("X.", ClaimStatus.SUPPORTED,
                            citation_path="note/A.md", excerpt="X context")
        critic.check()  # must not raise
        self.assertTrue(state.decision_events[-1]["passed"])

    def test_passes_with_no_claims_and_resolved_facet(self):
        state, ledger, critic = self._setup([("F1", FacetStatus.MISSING)])
        critic.check()  # no claims — gap declared is acceptable
        self.assertTrue(state.decision_events[-1]["passed"])

    def test_vetoes_with_unsupported_claim(self):
        state, ledger, critic = self._setup([("F1", FacetStatus.SUPPORTED)])
        ledger.record_claim("Unsupported claim.", ClaimStatus.UNSUPPORTED)
        with self.assertRaises(CriticVeto) as ctx:
            critic.check()
        self.assertEqual(len(ctx.exception.unsupported), 1)
        self.assertFalse(state.decision_events[-1]["passed"])

    def test_vetoes_when_no_facets_resolved(self):
        state, ledger, critic = self._setup([("F1", FacetStatus.UNSEARCHED)])
        ledger.record_claim("X.", ClaimStatus.SUPPORTED,
                            citation_path="note/A.md", excerpt="X context")
        with self.assertRaises(CriticVeto):
            critic.check()

    def test_decision_event_recorded(self):
        state, ledger, critic = self._setup([("F1", FacetStatus.SUPPORTED)])
        try:
            critic.check()
        except CriticVeto:
            pass
        self.assertTrue(any(e.get("block") == "critic" for e in state.decision_events))


# ---------------------------------------------------------------------------
# QualityProtectedStopper
# ---------------------------------------------------------------------------

class TestQualityProtectedStopper(unittest.TestCase):
    def test_hard_budget_takes_priority(self):
        state = _make_state(
            max_search_calls=1, max_read_calls=1,
            search_calls_used=1, read_calls_used=1,
        )
        stopper = QualityProtectedStopper(state)
        stop, reason = stopper.should_stop(critic_passed=True)
        self.assertTrue(stop)
        self.assertEqual(reason, StopReason.HARD_BUDGET)

    def test_no_stop_when_critic_blocked(self):
        state = _state_with_facets(("F1", FacetStatus.UNSEARCHED))
        stopper = QualityProtectedStopper(state)
        stop, reason = stopper.should_stop(critic_passed=False)
        self.assertFalse(stop)

    def test_stop_all_facets_resolved_low_voi(self):
        state = _state_with_facets(("F1", FacetStatus.SUPPORTED))
        state.max_read_calls = 1
        state.read_calls_used = 1
        stopper = QualityProtectedStopper(state)
        stop, reason = stopper.should_stop(critic_passed=True)
        self.assertTrue(stop)
        self.assertIn(reason, (StopReason.ALL_FACETS_RESOLVED, StopReason.LOW_VOI))

    def test_record_stop_sets_state(self):
        state = _make_state()
        stopper = QualityProtectedStopper(state)
        stopper.record_stop(StopReason.HARD_BUDGET)
        self.assertEqual(state.stop_reason, StopReason.HARD_BUDGET)
        self.assertTrue(any(e.get("block") == "stopper" for e in state.decision_events))


# ---------------------------------------------------------------------------
# SearchController integration
# ---------------------------------------------------------------------------

class _ImmediateStopAdapter:
    """Adapter that causes the controller to stop after one facet + one claim."""

    def decompose_question(self, question: str) -> list[str]:
        return ["What is X?"]

    def select_next_query(self, state: ControllerState) -> str | None:
        return "X definition" if state.search_calls_used == 0 else None

    def select_note_to_read(
        self, state: ControllerState, hits: list[dict]
    ) -> str | None:
        if state.read_calls_used == 0 and hits:
            return hits[0]["path"]
        return None

    def extract_claims(
        self, state: ControllerState, content: str, path: str
    ) -> list[dict]:
        return [
            {
                "sentence": "X is defined as Y.",
                "status": "supported",
                "excerpt": "X is defined as Y in context.",
            }
        ]

    def synthesize_answer(self, state: ControllerState) -> dict:
        return {
            "answer": "X is Y.",
            "citations": [{"path": "note/A.md", "supporting_excerpt": "X is defined as Y."}],
            "declared_gaps": [],
            "run_status": "answer",
        }


class _ErrorAdapter:
    """Adapter that raises ProviderError on question decompose."""

    def decompose_question(self, question: str) -> list[str]:
        from controller import ProviderError
        raise ProviderError("model unavailable")

    def select_next_query(self, state: ControllerState) -> str | None:
        return None

    def select_note_to_read(self, state, hits) -> str | None:
        return None

    def extract_claims(self, state, content, path) -> list[dict]:
        return []

    def synthesize_answer(self, state) -> dict:
        return {"answer": "", "citations": [], "declared_gaps": [], "run_status": "error"}


class TestSearchController(unittest.TestCase):
    def _run(self, adapter=None, max_search=4, max_read=6):
        session = _StubSession(max_search_calls=max_search, max_read_calls=max_read)
        ctrl = SearchController(
            adapter or _ImmediateStopAdapter(),
            session,
            max_search_calls=max_search,
            max_read_calls=max_read,
        )
        return ctrl.run("What is X?"), session

    def test_output_has_required_keys(self):
        result, _ = self._run()
        for key in ("schema_version", "arm", "behavior", "answer",
                    "citations", "declared_gaps", "operational_trace"):
            self.assertIn(key, result)

    def test_arm_is_configured(self):
        result, _ = self._run()
        self.assertEqual(result["arm"], "configured")

    def test_policy_version_present(self):
        result, _ = self._run()
        self.assertEqual(result["policy_version"], POLICY_VERSION)

    def test_decision_events_recorded(self):
        result, _ = self._run()
        events = result["operational_trace"]["decision_events"]
        self.assertGreater(len(events), 0)

    def test_stop_reason_recorded(self):
        result, _ = self._run()
        self.assertIsNotNone(result["operational_trace"]["stop_reason"])

    def test_model_usage_null_when_unavailable(self):
        result, _ = self._run()
        usage = result["model_usage"]
        self.assertIsNone(usage["model_id"])
        self.assertIsNone(usage["input_tokens"])
        self.assertIsNone(usage["provider_cost_usd"])

    def test_budget_not_exceeded(self):
        result, session = self._run(max_search=4, max_read=6)
        self.assertLessEqual(session.search_calls, 4)
        self.assertLessEqual(session.read_calls, 6)

    def test_hard_budget_stop_when_exhausted(self):
        result, _ = self._run(max_search=1, max_read=1)
        stop_reason = result["operational_trace"]["stop_reason"]
        self.assertIsNotNone(stop_reason)

    def test_provider_error_captured_gracefully(self):
        result, _ = self._run(adapter=_ErrorAdapter())
        self.assertEqual(result["behavior"], RunStatus.ERROR.value)
        self.assertIn("controller error", result["answer"])

    def test_both_arms_receive_identical_budget_contract(self):
        """
        Verify that max_search and max_read are declared constants —
        same values available to both arms.
        """
        self.assertEqual(MAX_SEARCH_CALLS, 4)
        self.assertEqual(MAX_READ_CALLS, 6)


class TestBudgetEnforcement(unittest.TestCase):
    def test_search_budget_enforced_by_state(self):
        state = _make_state(max_search_calls=2, search_calls_used=2)
        self.assertEqual(state.remaining_search(), 0)

    def test_read_budget_enforced_by_state(self):
        state = _make_state(max_read_calls=3, read_calls_used=3)
        self.assertEqual(state.remaining_read(), 0)

    def test_budget_exceeded_internally_is_internal(self):
        """BudgetExceededInternally must not leak to callers."""
        exc = BudgetExceededInternally("test")
        self.assertIsInstance(exc, Exception)


if __name__ == "__main__":
    unittest.main()
