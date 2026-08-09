"""
Tests for the Technique Registry — schema conformance and evidence claims.
"""

import json
import unittest
from pathlib import Path

from validate import validate, VALID_BLOCK_IDS, VALID_EVIDENCE_GRADES

REGISTRY_PATH = Path(__file__).parent / "techniques.json"


def load():
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


class TestRegistryLoads(unittest.TestCase):
    def test_file_exists(self):
        self.assertTrue(REGISTRY_PATH.exists())

    def test_valid_json(self):
        data = load()
        self.assertIn("techniques", data)

    def test_meta_present(self):
        data = load()
        self.assertIn("_meta", data)
        self.assertIn("schema_version", data["_meta"])


class TestNoDuplicateIds(unittest.TestCase):
    def test_unique_ids(self):
        techniques = load()["techniques"]
        ids = [r["id"] for r in techniques]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate technique IDs found")


class TestRequiredFields(unittest.TestCase):
    def setUp(self):
        self.techniques = load()["techniques"]

    def test_all_have_id(self):
        for r in self.techniques:
            self.assertIn("id", r, f"Missing 'id': {r}")

    def test_all_have_name(self):
        for r in self.techniques:
            self.assertIn("name", r, f"[{r.get('id')}] missing 'name'")

    def test_all_have_schema_version(self):
        for r in self.techniques:
            self.assertIn("schema_version", r, f"[{r.get('id')}] missing schema_version")
            self.assertIn(r["schema_version"], (1, 2), f"[{r['id']}] invalid schema_version")

    def test_all_have_description(self):
        for r in self.techniques:
            self.assertIn("description", r, f"[{r.get('id')}] missing 'description'")
            self.assertGreater(len(r["description"]), 10, f"[{r['id']}] description too short")

    def test_all_have_example_use_case(self):
        for r in self.techniques:
            self.assertIn("example_use_case", r, f"[{r.get('id')}] missing 'example_use_case'")


class TestV2Records(unittest.TestCase):
    def setUp(self):
        self.v2 = [r for r in load()["techniques"] if r.get("schema_version") == 2]

    def test_at_least_five_v2_records(self):
        self.assertGreaterEqual(len(self.v2), 5, "Need at least 5 fully-curated v2 records")

    def test_v2_have_classification(self):
        for r in self.v2:
            self.assertIn("classification", r, f"[{r['id']}] v2 missing classification")

    def test_v2_have_assumptions(self):
        for r in self.v2:
            self.assertIn("assumptions", r, f"[{r['id']}] v2 missing assumptions")

    def test_v2_have_evidence(self):
        for r in self.v2:
            self.assertIn("evidence", r, f"[{r['id']}] v2 missing evidence")

    def test_v2_have_failure_modes(self):
        for r in self.v2:
            fm = r.get("failure_modes", [])
            self.assertGreater(len(fm), 0, f"[{r['id']}] v2 missing failure_modes")

    def test_v2_have_incompatible_when(self):
        for r in self.v2:
            self.assertIn("incompatible_when", r, f"[{r['id']}] v2 missing incompatible_when")

    def test_v2_evidence_grades_valid(self):
        for r in self.v2:
            grade = r.get("evidence", {}).get("grade")
            self.assertIn(grade, VALID_EVIDENCE_GRADES, f"[{r['id']}] invalid evidence grade {grade!r}")

    def test_v2_decision_blocks_known(self):
        for r in self.v2:
            blocks = r.get("classification", {}).get("decision_blocks", [])
            for b in blocks:
                self.assertIn(b, VALID_BLOCK_IDS, f"[{r['id']}] unknown decision_block {b!r}")

    def test_v2_executable_policies_have_baseline(self):
        for r in self.v2:
            if r.get("classification", {}).get("type") == "executable-policy":
                self.assertIn("baseline", r, f"[{r['id']}] executable-policy missing baseline")
                self.assertTrue(r["baseline"].get("id"), f"[{r['id']}] baseline.id is empty")


class TestCuratedTechniques(unittest.TestCase):
    """Spot-checks for the five fully curated techniques."""

    def setUp(self):
        self.index = {r["id"]: r for r in load()["techniques"]}

    def _get(self, rid):
        self.assertIn(rid, self.index, f"Technique '{rid}' not found in registry")
        return self.index[rid]

    def test_explore_then_commit_exists_and_curated(self):
        r = self._get("explore-then-commit")
        self.assertEqual(r["schema_version"], 2)
        self.assertIn("explorer", r["classification"]["decision_blocks"])
        self.assertEqual(r["evidence"]["grade"], "B")

    def test_ucb1_exists_and_curated(self):
        r = self._get("ucb1")
        self.assertEqual(r["schema_version"], 2)
        self.assertIn("explorer", r["classification"]["decision_blocks"])

    def test_thompson_sampling_exists_and_curated(self):
        r = self._get("thompson-sampling")
        self.assertEqual(r["schema_version"], 2)
        self.assertIn("explorer", r["classification"]["decision_blocks"])

    def test_fixed_budget_stopper_exists_and_curated(self):
        r = self._get("fixed-budget-stopper")
        self.assertEqual(r["schema_version"], 2)
        self.assertIn("stopper", r["classification"]["decision_blocks"])

    def test_evidence_critic_exists_and_curated(self):
        r = self._get("evidence-critic")
        self.assertEqual(r["schema_version"], 2)
        self.assertIn("critic", r["classification"]["decision_blocks"])

    def test_trend_marginal_stopper_exists(self):
        r = self._get("trend-marginal-stopper")
        self.assertEqual(r["schema_version"], 2)
        self.assertIn("stopper", r["classification"]["decision_blocks"])

    def test_confidence_marginal_stopper_exists(self):
        r = self._get("confidence-marginal-stopper")
        self.assertEqual(r["schema_version"], 2)
        self.assertIn("stopper", r["classification"]["decision_blocks"])


class TestValidatorPasses(unittest.TestCase):
    def test_validate_no_errors(self):
        ok = validate(strict=False)
        self.assertTrue(ok, "validate() returned False — check ERROR lines above")


if __name__ == "__main__":
    unittest.main()
