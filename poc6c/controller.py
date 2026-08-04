"""
Candidate 2 search controller — executable runtime implementation.

This module turns the CONFIGURED_AGENT_V2.md prompt into enforced runtime
logic.  The LLM remains the generator; every decision boundary (budget, critic
gate, stop condition) is checked here, outside the model.

Architecture
------------
ControllerState   -- typed mutable state for one run
EvidenceLedger    -- sentence-level claim tracking
EvidenceCritic    -- validates claims against the ledger before output
QualityProtectedStopper -- enforces the stop conditions from the contract
SearchController  -- orchestrates the full decision loop

Provider contract
-----------------
The caller supplies a ProviderAdapter that wraps the actual LLM/tool calls.
This keeps the controller provider-independent and fully testable with stubs.

Trace integration
-----------------
Every state transition is appended to a list of decision events that slot
directly into the trace.py schema (type="decision").
"""

from __future__ import annotations

import dataclasses
import enum
import time
from typing import Any, Callable, Protocol


# ---------------------------------------------------------------------------
# Enums and constants
# ---------------------------------------------------------------------------

class FacetStatus(str, enum.Enum):
    UNSEARCHED = "unsearched"
    PARTIAL    = "partial"
    SUPPORTED  = "supported"
    MISSING    = "missing"
    CONTRADICTORY = "contradictory"


class ClaimStatus(str, enum.Enum):
    SUPPORTED    = "supported"
    UNSUPPORTED  = "unsupported"
    INFERENCE    = "inference"      # explicitly labelled inference/recommendation


class StopReason(str, enum.Enum):
    ALL_FACETS_RESOLVED  = "all_facets_resolved"
    QUALITY_GATE_PASSED  = "quality_gate_passed"
    HARD_BUDGET          = "hard_budget"
    LOW_VOI              = "low_expected_voi"       # value-of-information check
    CRITIC_BLOCKED       = "critic_blocked_finalize" # critic vetoed; answer not ready


class RunStatus(str, enum.Enum):
    ANSWER         = "answer"
    PARTIAL_ANSWER = "partial_answer"
    ABSTAIN        = "abstain"
    ERROR          = "error"


MAX_SEARCH_CALLS = 4
MAX_READ_CALLS   = 6

POLICY_VERSION = "candidate2-v1.0"
DECISION_ARCHITECTURE = "evidence-coverage-controller"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class Facet:
    text: str
    status: FacetStatus = FacetStatus.UNSEARCHED
    supporting_paths: list[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "status": self.status.value,
            "supporting_paths": list(self.supporting_paths),
        }


@dataclasses.dataclass
class Claim:
    sentence: str
    status: ClaimStatus
    citation_path: str | None = None
    excerpt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sentence": self.sentence,
            "status": self.status.value,
            "citation_path": self.citation_path,
            "excerpt": self.excerpt,
        }


@dataclasses.dataclass
class ControllerState:
    """Full mutable state for one controller run."""

    question: str
    facets: list[Facet] = dataclasses.field(default_factory=list)
    claims: list[Claim] = dataclasses.field(default_factory=list)
    search_calls_used: int = 0
    read_calls_used: int = 0
    declared_gaps: list[str] = dataclasses.field(default_factory=list)
    contradictions: list[str] = dataclasses.field(default_factory=list)
    decision_events: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    stop_reason: StopReason | None = None
    run_status: RunStatus | None = None
    final_answer: str = ""
    citations: list[dict[str, str]] = dataclasses.field(default_factory=list)

    # Budget limits (set by controller, enforced here)
    max_search_calls: int = MAX_SEARCH_CALLS
    max_read_calls: int = MAX_READ_CALLS

    def remaining_search(self) -> int:
        return self.max_search_calls - self.search_calls_used

    def remaining_read(self) -> int:
        return self.max_read_calls - self.read_calls_used

    def budget_exhausted(self) -> bool:
        return self.remaining_search() <= 0 and self.remaining_read() <= 0

    def evidence_status_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {s.value: 0 for s in FacetStatus}
        for facet in self.facets:
            counts[facet.status.value] += 1
        return counts

    def to_operational_trace(self) -> dict[str, Any]:
        return {
            "facets": [f.to_dict() for f in self.facets],
            "claims": [c.to_dict() for c in self.claims],
            "search_calls_used": self.search_calls_used,
            "read_calls_used": self.read_calls_used,
            "remaining_search": self.remaining_search(),
            "remaining_read": self.remaining_read(),
            "declared_gaps": list(self.declared_gaps),
            "contradictions": list(self.contradictions),
            "stop_reason": self.stop_reason.value if self.stop_reason else None,
            "run_status": self.run_status.value if self.run_status else None,
            "evidence_status_counts": self.evidence_status_counts(),
        }


# ---------------------------------------------------------------------------
# Evidence ledger
# ---------------------------------------------------------------------------

class EvidenceLedger:
    """Tracks sentence-level claim support for one run."""

    def __init__(self, state: ControllerState) -> None:
        self._state = state

    def record_claim(
        self,
        sentence: str,
        status: ClaimStatus,
        citation_path: str | None = None,
        excerpt: str | None = None,
    ) -> None:
        if not sentence or not sentence.strip():
            raise ValueError("claim sentence must not be empty")
        if status == ClaimStatus.SUPPORTED and not citation_path:
            raise ValueError("SUPPORTED claim requires a citation_path")
        if status == ClaimStatus.SUPPORTED and not excerpt:
            raise ValueError("SUPPORTED claim requires an excerpt")
        self._state.claims.append(
            Claim(
                sentence=sentence.strip(),
                status=status,
                citation_path=citation_path,
                excerpt=excerpt,
            )
        )

    def unsupported_claims(self) -> list[Claim]:
        return [c for c in self._state.claims if c.status == ClaimStatus.UNSUPPORTED]

    def supported_claims(self) -> list[Claim]:
        return [c for c in self._state.claims if c.status == ClaimStatus.SUPPORTED]

    def all_claims_resolved(self) -> bool:
        """True when every recorded claim is either supported or labelled inference."""
        return all(
            c.status in (ClaimStatus.SUPPORTED, ClaimStatus.INFERENCE)
            for c in self._state.claims
        )


# ---------------------------------------------------------------------------
# Evidence critic gate
# ---------------------------------------------------------------------------

class CriticVeto(Exception):
    """Raised when the critic blocks an answer from being finalized."""

    def __init__(self, unsupported: list[Claim]) -> None:
        self.unsupported = unsupported
        sentences = "; ".join(c.sentence[:80] for c in unsupported[:3])
        super().__init__(f"Critic veto: {len(unsupported)} unsupported claim(s): {sentences}")


class EvidenceCritic:
    """
    Validates the ledger before finalizing an answer.

    Rules (from CONFIGURED_AGENT_V2.md):
    1. Every substantive claim must be SUPPORTED or labelled INFERENCE.
    2. At least one important facet must be supported or declared as a gap.
    3. If claims exist but none are supported, the answer is not ready.
    """

    def __init__(self, state: ControllerState, ledger: EvidenceLedger) -> None:
        self._state = state
        self._ledger = ledger

    def check(self) -> None:
        """
        Raise CriticVeto if the answer is not ready to finalize.
        Record the critic decision in the decision_events list either way.
        """
        unsupported = self._ledger.unsupported_claims()

        # At least one facet must be resolved or explicitly bounded
        facets_resolved = any(
            f.status in (FacetStatus.SUPPORTED, FacetStatus.PARTIAL, FacetStatus.MISSING)
            for f in self._state.facets
        )

        # Claims exist but none are supported: not ready
        has_claims = bool(self._state.claims)
        has_support = bool(self._ledger.supported_claims())

        passed = (
            not unsupported
            and facets_resolved
            and (not has_claims or has_support)
        )

        event: dict[str, Any] = {
            "type": "decision",
            "block": "critic",
            "policy": "evidence-coverage-critic",
            "passed": passed,
            "unsupported_count": len(unsupported),
            "supported_count": len(self._ledger.supported_claims()),
            "facets_resolved": facets_resolved,
        }
        if unsupported:
            event["unsupported_sentences"] = [c.sentence[:120] for c in unsupported[:5]]
        self._state.decision_events.append(event)

        if not passed:
            raise CriticVeto(unsupported)


# ---------------------------------------------------------------------------
# Quality-protected stopper
# ---------------------------------------------------------------------------

class QualityProtectedStopper:
    """
    Enforces the stopping contract from CONFIGURED_AGENT_V2.md §5:

    Stop only when:
      (a) important facets are supported or declared as gaps, AND
      (b) every substantive sentence passes the evidence critic, AND
      (c) another retrieval has low expected coverage gain (VOI check), OR
      (d) the hard budget is reached.

    This class checks conditions (a), (c), (d) — (b) is enforced by
    EvidenceCritic.check() which must be called before should_stop().
    """

    def __init__(self, state: ControllerState) -> None:
        self._state = state

    def _important_facets_resolved(self) -> bool:
        return all(
            f.status in (FacetStatus.SUPPORTED, FacetStatus.MISSING, FacetStatus.PARTIAL)
            for f in self._state.facets
        )

    def _low_voi(self) -> bool:
        """
        Heuristic: VOI is low when:
          - remaining read budget is 0, OR
          - all facets are SUPPORTED (no gap left to fill), OR
          - remaining search AND read are both <= 0
        """
        all_supported = all(
            f.status == FacetStatus.SUPPORTED for f in self._state.facets
        )
        return (
            self._state.remaining_read() <= 0
            or self._state.remaining_search() <= 0 and all_supported
        )

    def should_stop(self, critic_passed: bool) -> tuple[bool, StopReason]:
        """
        Returns (stop, reason).  Caller must have run EvidenceCritic.check()
        first; pass critic_passed=True if it did not raise.
        """
        # Hard budget always wins
        if self._state.budget_exhausted():
            return True, StopReason.HARD_BUDGET

        if not critic_passed:
            return False, StopReason.CRITIC_BLOCKED

        if self._important_facets_resolved():
            if self._low_voi():
                return True, StopReason.LOW_VOI
            # All facets resolved, critic passed
            return True, StopReason.ALL_FACETS_RESOLVED

        return False, StopReason.QUALITY_GATE_PASSED

    def record_stop(self, reason: StopReason) -> None:
        self._state.stop_reason = reason
        self._state.decision_events.append(
            {
                "type": "decision",
                "block": "stopper",
                "policy": "quality-protected-stopper",
                "reason": reason.value,
                "remaining_search": self._state.remaining_search(),
                "remaining_read": self._state.remaining_read(),
                "facet_statuses": [f.status.value for f in self._state.facets],
            }
        )


# ---------------------------------------------------------------------------
# Provider adapter protocol
# ---------------------------------------------------------------------------

class ProviderAdapter(Protocol):
    """
    Minimal interface the controller requires from any LLM provider.

    All methods raise ProviderError on failure.
    The controller never calls the provider directly for budget checks —
    those are enforced by ControllerState counters.
    """

    def decompose_question(self, question: str) -> list[str]:
        """Return 3–5 facet strings for the question."""
        ...

    def select_next_query(
        self,
        state: ControllerState,
    ) -> str | None:
        """
        Return the highest-VOI search query given current state, or None if
        the controller should skip to a read or stop.
        """
        ...

    def select_note_to_read(
        self,
        state: ControllerState,
        search_hits: list[dict[str, Any]],
    ) -> str | None:
        """
        Return the relative path of the most valuable note to read next,
        or None to skip reading.
        """
        ...

    def extract_claims(
        self,
        state: ControllerState,
        note_content: str,
        note_path: str,
    ) -> list[dict[str, Any]]:
        """
        Return a list of claim dicts:
          {"sentence": str, "status": "supported"|"unsupported"|"inference",
           "excerpt": str|None}
        """
        ...

    def synthesize_answer(self, state: ControllerState) -> dict[str, Any]:
        """
        Return:
          {"answer": str, "citations": [{"path": str, "supporting_excerpt": str}],
           "declared_gaps": [str], "run_status": "answer"|"partial_answer"|"abstain"}
        """
        ...


class ProviderError(RuntimeError):
    """Raised by ProviderAdapter implementations on LLM/tool failure."""


# ---------------------------------------------------------------------------
# Main controller
# ---------------------------------------------------------------------------

class SearchController:
    """
    Orchestrates one Candidate 2 search run.

    Usage
    -----
    adapter = MyProviderAdapter(...)
    session = SearchSession(corpus, max_search_calls=4, max_read_calls=6)
    result  = SearchController(adapter, session).run(question)
    """

    def __init__(
        self,
        adapter: ProviderAdapter,
        session: Any,   # corpus.SearchSession
        *,
        max_search_calls: int = MAX_SEARCH_CALLS,
        max_read_calls: int = MAX_READ_CALLS,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._adapter  = adapter
        self._session  = session
        self._clock    = clock or time.monotonic
        self._max_search = max_search_calls
        self._max_read   = max_read_calls

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, question: str) -> dict[str, Any]:
        """
        Execute the full controller loop for one question.
        Returns a dict conforming to OUTPUT_FORMAT.json (single-case variant).
        Never raises on LLM/tool error — captures error into run_status.
        """
        t0 = self._clock()

        state = ControllerState(
            question=question,
            max_search_calls=self._max_search,
            max_read_calls=self._max_read,
        )
        ledger  = EvidenceLedger(state)
        critic  = EvidenceCritic(state, ledger)
        stopper = QualityProtectedStopper(state)

        try:
            self._phase_plan(state)
            self._phase_explore(state, ledger, critic, stopper)
            self._phase_finalize(state, critic, stopper)
        except BudgetExceededInternally:
            # Budget was already recorded as HARD_BUDGET stop
            if state.stop_reason is None:
                stopper.record_stop(StopReason.HARD_BUDGET)
        except ProviderError as exc:
            state.run_status = RunStatus.ERROR
            state.final_answer = f"[controller error: {exc}]"
            state.decision_events.append(
                {"type": "error", "message": str(exc)}
            )

        wall_ms = int((self._clock() - t0) * 1000)
        return self._build_output(state, wall_ms)

    # ------------------------------------------------------------------
    # Internal phases
    # ------------------------------------------------------------------

    def _phase_plan(self, state: ControllerState) -> None:
        """Facet planner: decompose question into 3–5 answer facets."""
        facet_texts = self._adapter.decompose_question(state.question)
        for text in facet_texts[:5]:
            state.facets.append(Facet(text=text))
        state.decision_events.append(
            {
                "type": "decision",
                "block": "planner",
                "policy": "facet-planner",
                "facets": [f.text for f in state.facets],
            }
        )

    def _phase_explore(
        self,
        state: ControllerState,
        ledger: EvidenceLedger,
        critic: EvidenceCritic,
        stopper: QualityProtectedStopper,
    ) -> None:
        """Value-of-information explorer: iterate search → read → record."""
        while not state.budget_exhausted():
            # Reset per-iteration flags — must be at top to prevent stale values
            # leaking into the infinite-loop guard at the bottom.
            query: str | None = None
            path: str | None = None

            # Decide next query (explorer block)
            if state.remaining_search() > 0:
                query = self._adapter.select_next_query(state)
                if query:
                    self._do_search(state, query)

            # Decide next read (explorer block, VOI on search results)
            if state.remaining_read() > 0:
                recent_hits = self._recent_search_hits(state)
                path = self._adapter.select_note_to_read(state, recent_hits)
                if path:
                    self._do_read(state, ledger, path)

            # Check whether to stop exploring (stopper pre-check before critic)
            critic_passed = True
            try:
                critic.check()
            except CriticVeto:
                critic_passed = False

            stop, reason = stopper.should_stop(critic_passed)
            if stop:
                stopper.record_stop(reason)
                return

            # Both adapter calls returned None and budget isn't exhausted —
            # nothing more to do; stop on low VOI.
            if query is None and path is None:
                stopper.record_stop(StopReason.LOW_VOI)
                return

        # Budget fully exhausted
        stopper.record_stop(StopReason.HARD_BUDGET)

    def _phase_finalize(
        self,
        state: ControllerState,
        critic: EvidenceCritic,
        stopper: QualityProtectedStopper,
    ) -> None:
        """Synthesize the final answer and apply the critic gate."""
        if state.stop_reason is None:
            # Exploration ended without recording a stop — record one now
            stopper.record_stop(StopReason.QUALITY_GATE_PASSED)

        # Run critic one final time before synthesis
        try:
            critic.check()
        except CriticVeto:
            # Critic still blocked — synthesize a partial/abstain answer
            pass

        result = self._adapter.synthesize_answer(state)
        state.final_answer = result.get("answer", "")
        state.citations    = result.get("citations", [])
        state.declared_gaps = result.get("declared_gaps", [])

        raw_status = result.get("run_status", "partial_answer")
        try:
            state.run_status = RunStatus(raw_status)
        except ValueError:
            state.run_status = RunStatus.PARTIAL_ANSWER

        state.decision_events.append(
            {
                "type": "answer",
                "run_status": state.run_status.value,
                "citation_count": len(state.citations),
                "declared_gap_count": len(state.declared_gaps),
            }
        )

    # ------------------------------------------------------------------
    # Tool wrappers (record budget consumption)
    # ------------------------------------------------------------------

    def _do_search(self, state: ControllerState, query: str) -> None:
        if state.remaining_search() <= 0:
            raise BudgetExceededInternally("search budget exceeded")
        hits = self._session.search(query)
        state.search_calls_used += 1
        result_paths = [h.path if hasattr(h, "path") else h.get("path", "") for h in hits]
        state.decision_events.append(
            {
                "type": "decision",
                "block": "explorer",
                "policy": "value-of-information-explorer",
                "action": "search",
                "query": query,
                "hits": len(hits),
                "result_paths": result_paths,
                "remaining_search": state.remaining_search(),
                "remaining_read": state.remaining_read(),
            }
        )

    def _do_read(
        self,
        state: ControllerState,
        ledger: EvidenceLedger,
        path: str,
    ) -> None:
        if state.remaining_read() <= 0:
            raise BudgetExceededInternally("read budget exceeded")
        note = self._session.read_note(path)
        state.read_calls_used += 1
        state.decision_events.append(
            {
                "type": "decision",
                "block": "explorer",
                "policy": "value-of-information-explorer",
                "action": "read",
                "path": path,
                "remaining_search": state.remaining_search(),
                "remaining_read": state.remaining_read(),
            }
        )
        # Extract and record claims from this note
        raw_claims = self._adapter.extract_claims(state, note["content"], path)
        for raw in raw_claims:
            try:
                status = ClaimStatus(raw.get("status", "unsupported"))
            except ValueError:
                status = ClaimStatus.UNSUPPORTED
            ledger.record_claim(
                sentence=raw.get("sentence", ""),
                status=status,
                citation_path=path if status == ClaimStatus.SUPPORTED else None,
                excerpt=raw.get("excerpt"),
            )
        # Update relevant facet statuses based on what we found
        self._update_facets(state, raw_claims, path)

    def _update_facets(
        self,
        state: ControllerState,
        raw_claims: list[dict[str, Any]],
        path: str,
    ) -> None:
        supported_count = sum(
            1 for c in raw_claims if c.get("status") == ClaimStatus.SUPPORTED.value
        )
        if supported_count > 0:
            for facet in state.facets:
                if facet.status == FacetStatus.UNSEARCHED:
                    facet.status = FacetStatus.PARTIAL
                    facet.supporting_paths.append(path)
                    break

    def _recent_search_hits(
        self, state: ControllerState
    ) -> list[dict[str, Any]]:
        """Return the last search event's result paths as dicts."""
        for event in reversed(state.decision_events):
            if (
                event.get("type") == "decision"
                and event.get("action") == "search"
            ):
                return [{"path": p} for p in event.get("result_paths", [])]
        return []

    # ------------------------------------------------------------------
    # Output builder
    # ------------------------------------------------------------------

    def _build_output(
        self, state: ControllerState, wall_ms: int
    ) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "arm": "configured",
            "policy_version": POLICY_VERSION,
            "decision_architecture": DECISION_ARCHITECTURE,
            "behavior": state.run_status.value if state.run_status else "error",
            "answer": state.final_answer,
            "citations": state.citations,
            "declared_gaps": state.declared_gaps,
            "operational_trace": {
                **state.to_operational_trace(),
                "decision_events": state.decision_events,
                "wall_milliseconds": wall_ms,
            },
            "model_usage": {
                "model_id": None,
                "input_tokens": None,
                "output_tokens": None,
                "provider_cost_usd": None,
            },
        }


# ---------------------------------------------------------------------------
# Internal sentinel
# ---------------------------------------------------------------------------

class BudgetExceededInternally(Exception):
    """Raised within the controller when a budget is crossed unexpectedly."""
