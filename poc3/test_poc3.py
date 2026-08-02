from __future__ import annotations

import unittest

import numpy as np

from experiment import (
    BUDGET_MULTIPLIERS,
    K_VALUES,
    NON_CONTROL_SHAPES,
    PRIMARY_POLICIES,
    SHAPES,
    build_regime,
    run_episode,
)
from policy_variants import ALL_VARIANTS, FAMILY_VARIANTS


class SensitivityDesignTests(unittest.TestCase):
    def test_grid_has_45_primary_cells(self) -> None:
        self.assertEqual(
            len(K_VALUES) * len(BUDGET_MULTIPLIERS) * len(SHAPES),
            45,
        )

    def test_every_regime_matches_requested_size_and_budget(self) -> None:
        for k in K_VALUES:
            for multiplier in BUDGET_MULTIPLIERS:
                for shape in SHAPES:
                    regime = build_regime(shape, k, multiplier)
                    self.assertEqual(regime.k, k)
                    self.assertEqual(regime.budget, k * multiplier)
                    self.assertEqual(len(regime.rates), k)
                    if regime.mode == "finite_urn":
                        self.assertEqual(len(regime.pool_sizes), k)

    def test_parameter_variants_have_unique_names(self) -> None:
        names = [variant.name for variant in ALL_VARIANTS]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(FAMILY_VARIANTS), {
            "epsilon_greedy",
            "ucb",
            "thompson",
            "discounted_thompson",
        })

    def test_every_primary_and_variant_policy_executes(self) -> None:
        regime = build_regime("deceptive_depleting", 5, 4)
        outcomes = np.zeros((regime.k, regime.budget), dtype=np.int8)
        for index, policy_class in enumerate(PRIMARY_POLICIES + ALL_VARIANTS):
            score = run_episode(
                policy_class,
                outcomes,
                regime.budget,
                1000 + index,
            )
            self.assertEqual(score, 0)

    def test_parameter_grid_uses_twelve_non_control_cells(self) -> None:
        self.assertEqual(len(BUDGET_MULTIPLIERS) * len(NON_CONTROL_SHAPES), 12)


if __name__ == "__main__":
    unittest.main()
