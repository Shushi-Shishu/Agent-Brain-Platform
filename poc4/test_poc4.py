"""Design and mechanics checks for POC 4."""

from __future__ import annotations

import unittest

import numpy as np

from experiment import (
    BUDGET,
    CONFIRMATION_OFFSET,
    K,
    PROBE_PULLS,
    SHAPES,
    ProbeTrace,
    StandardizedKNN,
    build_regime,
    probe_schedule,
    run_full_policy,
    run_probe_then_policy,
    trace_features,
)
from policies import RoundRobin


class WorkloadIdentificationDesignTests(unittest.TestCase):
    def test_locked_regimes_share_observable_contract(self):
        for shape in SHAPES:
            regime = build_regime(shape)
            self.assertEqual(regime.k, K)
            self.assertEqual(regime.budget, BUDGET)
            self.assertEqual(regime.name, shape)

    def test_probe_counts_and_schedules_are_locked(self):
        self.assertEqual(PROBE_PULLS, (3, 5, 8))
        self.assertEqual(probe_schedule(3), (0, 1, 0))
        self.assertEqual(probe_schedule(5), (0, 1, 2, 0, 1))
        self.assertEqual(probe_schedule(8), (0, 1, 2, 3, 0, 1, 2, 3))

    def test_features_ignore_observed_branch_names(self):
        trace = ProbeTrace(
            branches=(0, 1, 2, 0, 1),
            rewards=(1, 0, 1, 0, 1),
            first_pass_size=3,
        )
        renamed = ProbeTrace(
            branches=(8, 4, 11, 8, 4),
            rewards=trace.rewards,
            first_pass_size=3,
        )
        np.testing.assert_allclose(trace_features(trace), trace_features(renamed))

    def test_knn_learns_separable_training_data(self):
        x = np.asarray([[0.0], [0.1], [0.9], [1.0]])
        y = np.asarray(["low", "low", "high", "high"])
        model = StandardizedKNN(neighbors=1).fit(x, y)
        predicted = model.predict(np.asarray([[0.05], [0.95]]))
        self.assertEqual(predicted.tolist(), ["low", "high"])

    def test_probe_rewards_count_and_budget_is_not_extended(self):
        outcomes = np.ones((K, BUDGET), dtype=np.int8)
        full = run_full_policy(RoundRobin, outcomes, seed=1)
        probed = run_probe_then_policy(
            RoundRobin,
            outcomes,
            probe_pulls=8,
            seed=1,
        )
        self.assertEqual(full, BUDGET)
        self.assertEqual(probed, BUDGET)

    def test_confirmation_seed_namespace_is_disjoint(self):
        self.assertGreaterEqual(CONFIRMATION_OFFSET, 1_000_000)


if __name__ == "__main__":
    unittest.main()
