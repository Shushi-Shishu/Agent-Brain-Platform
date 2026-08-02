"""Design and mechanics checks for POC 5."""

from __future__ import annotations

import unittest

import numpy as np

from experiment import (
    BUDGET,
    CONFIRMATION_OFFSET,
    K,
    RULE_CLASSES,
    SHAPES,
    ConfidenceMarginal,
    FixedBudget,
    FixedHalf,
    PatienceStop,
    TrendMarginal,
    WindowMarginal,
    build_regime,
    evaluate_rule,
)


class StoppingRuleDesignTests(unittest.TestCase):
    def test_workloads_share_maximum_contract(self):
        for shape in SHAPES:
            regime = build_regime(shape)
            self.assertEqual(regime.k, K)
            self.assertEqual(regime.budget, BUDGET)
            self.assertEqual(regime.name, shape)

    def test_rule_names_are_unique(self):
        names = [rule.name for rule in RULE_CLASSES]
        self.assertEqual(len(names), len(set(names)))

    def test_all_success_sequence_keeps_adaptive_rules_running(self):
        rewards = np.ones(BUDGET, dtype=np.int8)
        self.assertEqual(FixedBudget().stop_time(rewards), BUDGET)
        self.assertEqual(FixedHalf().stop_time(rewards), BUDGET // 2)
        self.assertEqual(PatienceStop().stop_time(rewards), BUDGET)
        self.assertEqual(WindowMarginal().stop_time(rewards), BUDGET)
        self.assertEqual(ConfidenceMarginal().stop_time(rewards), BUDGET)
        self.assertEqual(TrendMarginal().stop_time(rewards), BUDGET)

    def test_all_failure_sequence_triggers_locked_minimums(self):
        rewards = np.zeros(BUDGET, dtype=np.int8)
        self.assertEqual(PatienceStop().stop_time(rewards), 12)
        self.assertEqual(WindowMarginal().stop_time(rewards), 24)
        self.assertEqual(ConfidenceMarginal().stop_time(rewards), 24)

    def test_utility_accounts_for_findings_and_pull_cost(self):
        rewards = np.ones(BUDGET, dtype=np.int8)
        result = evaluate_rule(FixedHalf, rewards, pull_cost=0.20)
        self.assertEqual(result.pulls, 96)
        self.assertEqual(result.findings, 96)
        self.assertAlmostEqual(result.utility, 76.8)

    def test_zero_cost_full_prefix_weakly_dominates(self):
        rewards = np.asarray(([1, 0, 1, 0] * (BUDGET // 4)), dtype=np.int8)
        full = evaluate_rule(FixedBudget, rewards, pull_cost=0.0)
        for rule in RULE_CLASSES:
            candidate = evaluate_rule(rule, rewards, pull_cost=0.0)
            self.assertGreaterEqual(full.findings, candidate.findings)

    def test_confirmation_seed_namespace_is_disjoint(self):
        self.assertGreaterEqual(CONFIRMATION_OFFSET, 1_000_000)


if __name__ == "__main__":
    unittest.main()
