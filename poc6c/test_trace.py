"""Tests for POC 6c trace integrity and matched-arm isolation."""

from __future__ import annotations

import copy
import unittest

from trace import blind_id, matched_pair_errors, usage_summary, validate_trace


def sample_trace(arm: str) -> dict:
    architecture = (
        None
        if arm == "generic"
        else {
            "explorer": "explore_then_commit",
            "stopper": "evidence_marginal",
            "critic": "citation_support",
        }
    )
    return {
        "schema_version": 1,
        "run_id": f"Q001-T1-{arm}",
        "blind_id": blind_id("Q001", 1, arm, "test-salt"),
        "arm": arm,
        "invariants": {
            "task_id": "Q001",
            "trial": 1,
            "model_id": "test-model",
            "model_version": "locked",
            "task_prompt_sha256": "A" * 64,
            "data_snapshot_sha256": "B" * 64,
            "access_mode": "vault_only",
            "tool_allowlist": ["vault_search", "read_document"],
            "max_model_calls": 8,
            "max_tool_calls": 20,
            "max_input_tokens": 100_000,
            "max_output_tokens": 4_000,
            "max_wall_seconds": 600,
        },
        "policy": {
            "decision_architecture": architecture,
            "policy_version": "generic-v1" if arm == "generic" else "brain-v1",
        },
        "events": [
            {"sequence": 1, "type": "vault_search", "query": "agent reliability"},
            {
                "sequence": 2,
                "type": "document_read",
                "path": "AI & SDLC/example.md",
            },
            {"sequence": 3, "type": "decision", "decision": "enough evidence"},
            {"sequence": 4, "type": "stop", "reason": "evidence threshold"},
            {"sequence": 5, "type": "answer", "status": "answer"},
        ],
        "usage": {
            "model_calls": 2,
            "tool_calls": 2,
            "input_tokens": None,
            "output_tokens": None,
            "wall_milliseconds": 1000,
            "provider_cost_usd": None,
        },
        "result": {
            "status": "answer",
            "answer": "A supported answer.",
            "citations": ["AI & SDLC/example.md"],
            "declared_gaps": [],
        },
    }


class TraceValidationTests(unittest.TestCase):
    def test_valid_generic_and_configured_traces(self):
        self.assertEqual(validate_trace(sample_trace("generic")), [])
        self.assertEqual(validate_trace(sample_trace("configured")), [])

    def test_generic_cannot_claim_configured_architecture(self):
        trace = sample_trace("generic")
        trace["policy"]["decision_architecture"] = {"stopper": "confidence"}
        self.assertIn(
            "generic arm cannot declare a decision architecture",
            validate_trace(trace),
        )

    def test_configured_requires_architecture(self):
        trace = sample_trace("configured")
        trace["policy"]["decision_architecture"] = None
        self.assertIn(
            "configured arm requires a decision architecture",
            validate_trace(trace),
        )

    def test_budget_overrun_is_rejected(self):
        trace = sample_trace("generic")
        trace["usage"]["tool_calls"] = 21
        self.assertIn("tool_calls exceeds matched budget", validate_trace(trace))

    def test_pair_requires_identical_invariants(self):
        generic = sample_trace("generic")
        configured = sample_trace("configured")
        self.assertEqual(matched_pair_errors(generic, configured), [])
        changed = copy.deepcopy(configured)
        changed["invariants"]["max_tool_calls"] = 21
        self.assertIn(
            "pair invariant mismatch: max_tool_calls",
            matched_pair_errors(generic, changed),
        )

    def test_blind_ids_do_not_reveal_arm(self):
        generic_id = blind_id("Q001", 1, "generic", "secret")
        configured_id = blind_id("Q001", 1, "configured", "secret")
        self.assertNotEqual(generic_id, configured_id)
        self.assertNotIn("generic", generic_id)
        self.assertNotIn("configured", configured_id)

    def test_usage_summary_counts_observable_events(self):
        summary = usage_summary(sample_trace("configured"))
        self.assertEqual(summary["vault_searches"], 1)
        self.assertEqual(summary["documents_read"], 1)
        self.assertEqual(summary["decisions_recorded"], 1)
        self.assertEqual(summary["input_tokens"], None)


if __name__ == "__main__":
    unittest.main()

