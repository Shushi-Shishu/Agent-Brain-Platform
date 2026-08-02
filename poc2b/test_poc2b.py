from __future__ import annotations

import unittest

import numpy as np

from environment import (
    PotentialOutcomeEnv,
    Regime,
    build_regimes,
    build_trial_outcomes,
)
from experiment import run_episode
from policies import POLICIES


class EnvironmentTests(unittest.TestCase):
    def test_trial_is_reproducible(self) -> None:
        regime = build_regimes()[1]
        first = build_trial_outcomes(regime, 123)
        second = build_trial_outcomes(regime, 123)
        np.testing.assert_array_equal(first, second)

    def test_semantic_branches_are_relabelled_between_trials(self) -> None:
        regime = Regime(
            name="label_test",
            description="",
            k=4,
            budget=8,
            mode="finite_urn",
            rates=(1.0, 0.0, 0.0, 0.0),
            pool_sizes=(8, 8, 8, 8),
        )
        rich_labels = {
            int(np.argmax(build_trial_outcomes(regime, seed).sum(axis=1)))
            for seed in range(20)
        }
        self.assertGreater(len(rich_labels), 1)

    def test_finite_urn_consumes_successes_and_failures(self) -> None:
        regime = Regime(
            name="urn",
            description="",
            k=3,
            budget=8,
            mode="finite_urn",
            rates=(0.5, 0.0, 0.0),
            pool_sizes=(4, 4, 4),
        )
        outcomes = build_trial_outcomes(regime, 9)
        self.assertEqual(int(outcomes.sum()), 2)
        for branch in range(regime.k):
            self.assertEqual(int(outcomes[branch, 4:].sum()), 0)

    def test_budget_and_branch_validation(self) -> None:
        env = PotentialOutcomeEnv(np.zeros((3, 2), dtype=np.int8), budget=2)
        with self.assertRaises(IndexError):
            env.pull(3)
        env.pull(0)
        env.pull(0)
        with self.assertRaises(RuntimeError):
            env.pull(0)


class PolicyTests(unittest.TestCase):
    def test_every_policy_selects_valid_branches_and_spends_budget(self) -> None:
        regime = build_regimes()[0]
        outcomes = build_trial_outcomes(regime, 77)
        for index, policy_class in enumerate(POLICIES):
            score = run_episode(
                policy_class,
                outcomes,
                regime.budget,
                1000 + index,
            )
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, regime.budget)


if __name__ == "__main__":
    unittest.main()
