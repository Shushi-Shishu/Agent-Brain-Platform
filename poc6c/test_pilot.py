"""Tests for search-pilot validation and arm blinding."""

from __future__ import annotations

import copy
import unittest

from corpus import FrozenCorpus
from pilot import (
    blinded_cases,
    load_tasks,
    operational_summary,
    validate_pilot_output,
)


class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = FrozenCorpus()
        hit = cls.corpus.search("agent observability", limit=1)[0]
        note = cls.corpus.read_note(hit.path)
        cls.path = hit.path
        cls.excerpt = " ".join(note["content"].split())[:120]

    def output(self, arm: str) -> dict:
        cases = []
        for task in load_tasks()["cases"]:
            cases.append(
                {
                    "id": task["id"],
                    "behavior": "answer",
                    "answer": "A concise evidence-based answer.",
                    "citations": [
                        {
                            "path": self.path,
                            "supporting_excerpt": self.excerpt,
                        }
                    ],
                    "declared_gaps": [],
                    "operational_trace": {
                        "facets": [] if arm == "generic" else ["reliability"],
                        "search_queries": ["agent observability"],
                        "documents_read": [self.path],
                        "evidence_status_counts": {
                            "supported": None,
                            "partial": None,
                            "contradictory": None,
                            "unsupported": None,
                        },
                        "stop_reason": "answer supported",
                    },
                }
            )
        return {
            "schema_version": 1,
            "stage": "instrumentation_only",
            "arm": arm,
            "model_usage": {
                "model_id": "test",
                "input_tokens": None,
                "output_tokens": None,
                "provider_cost_usd": None,
            },
            "cases": cases,
        }

    def test_valid_outputs(self):
        self.assertEqual(
            validate_pilot_output(self.output("generic"), self.corpus),
            [],
        )
        self.assertEqual(
            validate_pilot_output(self.output("configured"), self.corpus),
            [],
        )

    def test_fabricated_excerpt_is_rejected(self):
        output = self.output("generic")
        output["cases"][0]["citations"][0]["supporting_excerpt"] = "not present"
        self.assertIn(
            "Q001: citation 1 excerpt not found in note",
            validate_pilot_output(output, self.corpus),
        )

    def test_citation_must_be_recorded_as_read(self):
        output = self.output("generic")
        output["cases"][0]["operational_trace"]["documents_read"] = []
        self.assertIn(
            "Q001: citation 1 note not recorded as read",
            validate_pilot_output(output, self.corpus),
        )

    def test_budget_overrun_is_rejected(self):
        output = self.output("configured")
        output["cases"][0]["operational_trace"]["search_queries"] = [
            f"query {index}" for index in range(5)
        ]
        self.assertIn(
            "Q001: search-query budget exceeded",
            validate_pilot_output(output, self.corpus),
        )

    def test_blinding_removes_arm_and_trace_and_is_stable(self):
        generic = self.output("generic")
        configured = self.output("configured")
        first = blinded_cases(generic, configured, salt="secret")
        second = blinded_cases(generic, configured, salt="secret")
        self.assertEqual(first, second)
        rendered = str(first)
        self.assertNotIn("operational_trace", rendered)
        self.assertNotIn("'arm'", rendered)
        self.assertNotIn("generic", rendered)
        self.assertNotIn("configured", rendered)

    def test_different_case_sets_cannot_be_blinded(self):
        generic = self.output("generic")
        configured = copy.deepcopy(self.output("configured"))
        configured["cases"].pop()
        with self.assertRaises(ValueError):
            blinded_cases(generic, configured, salt="secret")

    def test_operational_summary_reports_observed_usage_only(self):
        generic = self.output("generic")
        configured = self.output("configured")
        configured["cases"][0]["operational_trace"]["search_queries"].append(
            "second query"
        )
        configured["cases"][0]["declared_gaps"].append("missing evidence")
        summary = operational_summary(generic, configured)
        self.assertEqual(
            summary["status"],
            "instrumentation_only_no_efficacy_claim",
        )
        self.assertEqual(summary["arms"]["generic"]["mean_search_queries"], 1)
        self.assertGreater(
            summary["arms"]["configured"]["mean_search_queries"],
            summary["arms"]["generic"]["mean_search_queries"],
        )
        self.assertNotIn("quality", summary["arms"]["generic"])


if __name__ == "__main__":
    unittest.main()
