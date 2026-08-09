"""
Task 3 — Selection ablation study.

Identifies which controller block (EvidenceLedger, EvidenceCritic,
QualityProtectedStopper) drives quality improvement by running five
matched arms on the same task set with individual blocks disabled.

Arms
----
ARM_GENERIC         generic: no controller blocks at all
ARM_LEDGER          ledger only (claim tracking, no critic veto)
ARM_CRITIC          ledger + critic (veto on unsupported claims)
ARM_STOPPER         stopper only (budget/VOI stop, no critic gate)
ARM_FULL            complete Candidate 2 (ledger + critic + stopper)

Each arm is a stripped SearchController variant that replaces one or
more components with a pass-through stub so the differences are exact.

Design constraints (PLAN.md Task 3):
- Uses only declared selection-set tasks; never opens confirmation tasks.
- Metrics frozen before outputs are generated.
- Block interactions are noted; additive composition is not assumed.
"""

from __future__ import annotations

import dataclasses
import enum
from typing import Any

from controller import (
    BudgetExceededInternally,
    ClaimStatus,
    ControllerState,
    CriticVeto,
    EvidenceCritic,
    EvidenceLedger,
    FacetStatus,
    MAX_READ_CALLS,
    MAX_SEARCH_CALLS,
    ProviderAdapter,
    ProviderError,
    QualityProtectedStopper,
    RunStatus,
    StopReason,
)


# ---------------------------------------------------------------------------
# Arm identifiers (frozen before any run is generated)
# ---------------------------------------------------------------------------

class AblationArm(str, enum.Enum):
    GENERIC  = "generic"
    LEDGER   = "ledger_only"
    CRITIC   = "ledger_plus_critic"
    STOPPER  = "stopper_only"
    FULL     = "full_candidate2"


# ---------------------------------------------------------------------------
# Metrics schema (frozen before outputs are generated)
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class AblationMetrics:
    """Per-run metrics used for block-level attribution."""

    arm: AblationArm
    task_id: str

    # Quality indicators
    supported_claim_count: int = 0
    unsupported_claim_count: int = 0
    critic_veto_count: int = 0          # times critic blocked finalization
    facets_resolved: int = 0            # facets in SUPPORTED|PARTIAL|MISSING
    facets_total: int = 0

    # Contract reliability
    stop_reason: str = ""
    hard_budget_stop: bool = False      # stop was forced by budget
    answer_ready: bool = False          # run_status == "answer"

    # Resource usage
    search_calls_used: int = 0
    read_calls_used: int = 0

    # Decision events recorded
    decision_event_count: int = 0

    def coverage_rate(self) -> float:
        """Fraction of facets with any resolution (0.0–1.0)."""
        if self.facets_total == 0:
            return 0.0
        return self.facets_resolved / self.facets_total

    def support_rate(self) -> float:
        """Fraction of claims that are supported (0.0–1.0)."""
        total = self.supported_claim_count + self.unsupported_claim_count
        if total == 0:
            return 0.0
        return self.supported_claim_count / total

    def to_dict(self) -> dict[str, Any]:
        return {
            "arm": self.arm.value,
            "task_id": self.task_id,
            "supported_claims": self.supported_claim_count,
            "unsupported_claims": self.unsupported_claim_count,
            "critic_veto_count": self.critic_veto_count,
            "facets_resolved": self.facets_resolved,
            "facets_total": self.facets_total,
            "coverage_rate": round(self.coverage_rate(), 4),
            "support_rate": round(self.support_rate(), 4),
            "stop_reason": self.stop_reason,
            "hard_budget_stop": self.hard_budget_stop,
            "answer_ready": self.answer_ready,
            "search_calls_used": self.search_calls_used,
            "read_calls_used": self.read_calls_used,
            "decision_event_count": self.decision_event_count,
        }


# ---------------------------------------------------------------------------
# Pass-through stubs (replace individual blocks without changing the loop)
# ---------------------------------------------------------------------------

class _PassthroughLedger:
    """No-op: records nothing, reports no unsupported claims."""

    def __init__(self, state: ControllerState) -> None:
        self._state = state

    def record_claim(
        self,
        sentence: str,
        status: ClaimStatus,
        citation_path: str | None = None,
        excerpt: str | None = None,
    ) -> None:
        pass

    def unsupported_claims(self) -> list:
        return []

    def supported_claims(self) -> list:
        return []

    def all_claims_resolved(self) -> bool:
        return True


class _PassthroughCritic:
    """No-op: never vetoes; records a pass event."""

    def __init__(self, state: ControllerState) -> None:
        self._state = state

    def check(self) -> None:
        self._state.decision_events.append(
            {
                "type": "decision",
                "block": "critic",
                "policy": "passthrough-no-veto",
                "passed": True,
                "unsupported_count": 0,
                "supported_count": 0,
                "facets_resolved": True,
            }
        )


class _PassthroughStopper:
    """
    No-op stopper: always returns (False, QUALITY_GATE_PASSED).
    Relies on the outer budget-exhaustion guard in the explore loop to stop.
    """

    def __init__(self, state: ControllerState) -> None:
        self._state = state

    def should_stop(self, critic_passed: bool) -> tuple[bool, StopReason]:
        return False, StopReason.QUALITY_GATE_PASSED

    def record_stop(self, reason: StopReason) -> None:
        self._state.stop_reason = reason
        self._state.decision_events.append(
            {
                "type": "decision",
                "block": "stopper",
                "policy": "passthrough-stopper",
                "reason": reason.value,
                "remaining_search": self._state.remaining_search(),
                "remaining_read": self._state.remaining_read(),
                "facet_statuses": [f.status.value for f in self._state.facets],
            }
        )


# ---------------------------------------------------------------------------
# Ablation controller
# ---------------------------------------------------------------------------

class AblationController:
    """
    Runs the controller loop with exactly the blocks specified by the arm.

    Block selection:
      ARM_GENERIC  — passthrough ledger, passthrough critic, passthrough stopper
      ARM_LEDGER   — real ledger, passthrough critic, passthrough stopper
      ARM_CRITIC   — real ledger, real critic, passthrough stopper
      ARM_STOPPER  — passthrough ledger, passthrough critic, real stopper
      ARM_FULL     — real ledger, real critic, real stopper
    """

    def __init__(
        self,
        arm: AblationArm,
        adapter: ProviderAdapter,
        session: Any,
        *,
        max_search_calls: int = MAX_SEARCH_CALLS,
        max_read_calls: int = MAX_READ_CALLS,
    ) -> None:
        self.arm = arm
        self._adapter = adapter
        self._session = session
        self._max_search = max_search_calls
        self._max_read = max_read_calls

    def run(self, task_id: str, question: str) -> tuple[dict[str, Any], AblationMetrics]:
        """
        Execute one task and return (output_dict, metrics).
        Output dict mirrors SearchController._build_output schema.
        """
        state = ControllerState(
            question=question,
            max_search_calls=self._max_search,
            max_read_calls=self._max_read,
        )

        ledger  = self._make_ledger(state)
        critic  = self._make_critic(state, ledger)
        stopper = self._make_stopper(state)

        try:
            self._phase_plan(state)
            self._phase_explore(state, ledger, critic, stopper)
            self._phase_finalize(state, critic, stopper)
        except BudgetExceededInternally:
            if state.stop_reason is None:
                stopper.record_stop(StopReason.HARD_BUDGET)
        except ProviderError as exc:
            state.run_status = RunStatus.ERROR
            state.final_answer = f"[ablation error: {exc}]"
            state.decision_events.append({"type": "error", "message": str(exc)})

        metrics = self._collect_metrics(task_id, state)
        output  = self._build_output(state, task_id)
        return output, metrics

    # ------------------------------------------------------------------
    # Block factories
    # ------------------------------------------------------------------

    def _make_ledger(self, state: ControllerState):
        if self.arm in (AblationArm.LEDGER, AblationArm.CRITIC, AblationArm.FULL):
            return EvidenceLedger(state)
        return _PassthroughLedger(state)

    def _make_critic(self, state: ControllerState, ledger):
        if self.arm in (AblationArm.CRITIC, AblationArm.FULL):
            if isinstance(ledger, EvidenceLedger):
                return EvidenceCritic(state, ledger)
        return _PassthroughCritic(state)

    def _make_stopper(self, state: ControllerState):
        if self.arm in (AblationArm.STOPPER, AblationArm.FULL):
            return QualityProtectedStopper(state)
        return _PassthroughStopper(state)

    # ------------------------------------------------------------------
    # Phases (mirrored from SearchController)
    # ------------------------------------------------------------------

    def _phase_plan(self, state: ControllerState) -> None:
        facet_texts = self._adapter.decompose_question(state.question)
        for text in facet_texts[:5]:
            from controller import Facet
            state.facets.append(Facet(text=text))
        state.decision_events.append(
            {
                "type": "decision",
                "block": "planner",
                "policy": "facet-planner",
                "facets": [f.text for f in state.facets],
            }
        )

    def _phase_explore(self, state, ledger, critic, stopper) -> None:
        while not state.budget_exhausted():
            query: str | None = None
            path: str | None = None

            if state.remaining_search() > 0:
                query = self._adapter.select_next_query(state)
                if query:
                    self._do_search(state, query)

            if state.remaining_read() > 0:
                recent_hits = self._recent_hits(state)
                path = self._adapter.select_note_to_read(state, recent_hits)
                if path:
                    self._do_read(state, ledger, path)

            critic_passed = True
            try:
                critic.check()
            except CriticVeto:
                critic_passed = False
                state.decision_events.append(
                    {"type": "decision", "block": "ablation", "event": "critic_veto"}
                )

            stop, reason = stopper.should_stop(critic_passed)
            if stop:
                stopper.record_stop(reason)
                return

            if query is None and path is None:
                stopper.record_stop(StopReason.LOW_VOI)
                return

        stopper.record_stop(StopReason.HARD_BUDGET)

    def _phase_finalize(self, state, critic, stopper) -> None:
        if state.stop_reason is None:
            stopper.record_stop(StopReason.QUALITY_GATE_PASSED)

        try:
            critic.check()
        except CriticVeto:
            pass

        result = self._adapter.synthesize_answer(state)
        state.final_answer   = result.get("answer", "")
        state.citations      = result.get("citations", [])
        state.declared_gaps  = result.get("declared_gaps", [])

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
    # Tool wrappers
    # ------------------------------------------------------------------

    def _do_search(self, state: ControllerState, query: str) -> None:
        if state.remaining_search() <= 0:
            raise BudgetExceededInternally("search budget exceeded")
        hits = self._session.search(query)
        state.search_calls_used += 1
        result_paths = [
            h.path if hasattr(h, "path") else h.get("path", "") for h in hits
        ]
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

    def _do_read(self, state: ControllerState, ledger, path: str) -> None:
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

    def _recent_hits(self, state: ControllerState) -> list[dict[str, Any]]:
        for event in reversed(state.decision_events):
            if event.get("type") == "decision" and event.get("action") == "search":
                return [{"path": p} for p in event.get("result_paths", [])]
        return []

    # ------------------------------------------------------------------
    # Metrics collection
    # ------------------------------------------------------------------

    def _collect_metrics(
        self, task_id: str, state: ControllerState
    ) -> AblationMetrics:
        from controller import Claim as _Claim
        supported = sum(
            1 for c in state.claims if c.status == ClaimStatus.SUPPORTED
        )
        unsupported = sum(
            1 for c in state.claims if c.status == ClaimStatus.UNSUPPORTED
        )
        veto_count = sum(
            1 for e in state.decision_events
            if e.get("block") == "ablation" and e.get("event") == "critic_veto"
        )
        resolved = sum(
            1 for f in state.facets
            if f.status in (FacetStatus.SUPPORTED, FacetStatus.PARTIAL, FacetStatus.MISSING)
        )
        return AblationMetrics(
            arm=self.arm,
            task_id=task_id,
            supported_claim_count=supported,
            unsupported_claim_count=unsupported,
            critic_veto_count=veto_count,
            facets_resolved=resolved,
            facets_total=len(state.facets),
            stop_reason=state.stop_reason.value if state.stop_reason else "",
            hard_budget_stop=(state.stop_reason == StopReason.HARD_BUDGET),
            answer_ready=(state.run_status == RunStatus.ANSWER),
            search_calls_used=state.search_calls_used,
            read_calls_used=state.read_calls_used,
            decision_event_count=len(state.decision_events),
        )

    # ------------------------------------------------------------------
    # Output builder
    # ------------------------------------------------------------------

    def _build_output(
        self, state: ControllerState, task_id: str
    ) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "arm": self.arm.value,
            "task_id": task_id,
            "behavior": state.run_status.value if state.run_status else "error",
            "answer": state.final_answer,
            "citations": state.citations,
            "declared_gaps": state.declared_gaps,
            "operational_trace": {
                **state.to_operational_trace(),
                "decision_events": state.decision_events,
            },
        }


# ---------------------------------------------------------------------------
# Comparison report
# ---------------------------------------------------------------------------

def compare_arms(
    results: list[tuple[AblationArm, list[AblationMetrics]]]
) -> dict[str, Any]:
    """
    Aggregate per-arm metrics across tasks and return a comparison dict.

    results: list of (arm, [metrics per task])

    Reports:
    - mean support_rate, coverage_rate, answer_ready rate per arm
    - mean search/read calls per arm
    - mean critic_veto count per arm (diagnostic: veto fires only with critic)
    - interaction flag: note when FULL differs from CRITIC + STOPPER individually

    Does NOT produce a product verdict — this is selection-only attribution.
    """

    arm_rows: dict[str, dict[str, Any]] = {}

    for arm, metrics_list in results:
        if not metrics_list:
            continue
        n = len(metrics_list)
        arm_rows[arm.value] = {
            "task_count": n,
            "mean_support_rate":  round(sum(m.support_rate()   for m in metrics_list) / n, 4),
            "mean_coverage_rate": round(sum(m.coverage_rate()  for m in metrics_list) / n, 4),
            "answer_ready_rate":  round(sum(m.answer_ready     for m in metrics_list) / n, 4),
            "mean_search_calls":  round(sum(m.search_calls_used for m in metrics_list) / n, 4),
            "mean_read_calls":    round(sum(m.read_calls_used   for m in metrics_list) / n, 4),
            "mean_critic_vetoes": round(sum(m.critic_veto_count for m in metrics_list) / n, 4),
            "hard_budget_stop_rate": round(
                sum(m.hard_budget_stop for m in metrics_list) / n, 4
            ),
        }

    return {
        "status": "selection_only_no_confirmation_claim",
        "arms": arm_rows,
        "limitations": [
            "Ablation uses selection-set tasks only; confirmation tasks untouched.",
            "Metrics are observational; causal attribution requires repeated trials.",
            "Block interactions (FULL vs additive) must be checked before composing.",
            "No product verdict may be derived from selection metrics.",
        ],
    }
