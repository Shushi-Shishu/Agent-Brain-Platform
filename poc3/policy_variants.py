"""Policy configurations used by the POC 3 sensitivity analysis."""

from __future__ import annotations

import numpy as np

from policies import (
    DiscountedThompson,
    EpsilonGreedy,
    Policy,
    ThompsonSampling,
    UCB1,
)


class UCBConfigured(UCB1):
    exploration_c = 2.0

    def select(self) -> int:
        untried = np.flatnonzero(self.counts == 0)
        if len(untried):
            return int(untried[0])
        bonus = np.sqrt(
            self.exploration_c * np.log(max(self.t, 1)) / self.counts
        )
        return int(np.argmax(self.means + bonus))


class ThompsonConfigured(Policy):
    prior = 1.0

    def select(self) -> int:
        samples = self.rng.beta(
            self.prior + self.successes,
            self.prior + self.counts - self.successes,
        )
        return int(np.argmax(samples))


def _epsilon_class(epsilon: float) -> type[EpsilonGreedy]:
    label = f"EpsilonGreedy(e={epsilon})"

    class ConfiguredEpsilon(EpsilonGreedy):
        name = label

        def __init__(self, k, rng, budget):
            super().__init__(k, rng, budget, epsilon=epsilon)

    return ConfiguredEpsilon


def _ucb_class(c: float) -> type[UCBConfigured]:
    label = f"UCB1(c={c})"

    class ConfiguredUCB(UCBConfigured):
        pass

    ConfiguredUCB.name = label
    ConfiguredUCB.exploration_c = c

    return ConfiguredUCB


def _thompson_class(prior: float) -> type[ThompsonConfigured]:
    label = f"ThompsonSampling(prior={prior})"

    class ConfiguredThompson(ThompsonConfigured):
        pass

    ConfiguredThompson.name = label
    ConfiguredThompson.prior = prior

    return ConfiguredThompson


def _discounted_class(gamma: float) -> type[DiscountedThompson]:
    label = f"DiscountedThompson(g={gamma})"

    class ConfiguredDiscounted(DiscountedThompson):
        name = label

        def __init__(self, k, rng, budget):
            super().__init__(k, rng, budget, gamma=gamma)

    return ConfiguredDiscounted


FAMILY_VARIANTS: dict[str, tuple[type, ...]] = {
    "epsilon_greedy": tuple(_epsilon_class(value) for value in (0.05, 0.10, 0.20)),
    "ucb": tuple(_ucb_class(value) for value in (0.5, 1.0, 2.0, 4.0)),
    "thompson": tuple(_thompson_class(value) for value in (0.5, 1.0, 2.0)),
    "discounted_thompson": tuple(
        _discounted_class(value) for value in (0.80, 0.90, 0.97)
    ),
}

ALL_VARIANTS = tuple(
    policy_class
    for family in FAMILY_VARIANTS.values()
    for policy_class in family
)
