"""Fixed control-policy configurations for POC 2b."""

from __future__ import annotations

import numpy as np


class Policy:
    name = "Policy"

    def __init__(self, k: int, rng: np.random.Generator, budget: int):
        self.k = k
        self.rng = rng
        self.budget = budget
        self.counts = np.zeros(k, dtype=float)
        self.successes = np.zeros(k, dtype=float)
        self.t = 0

    @property
    def means(self) -> np.ndarray:
        return np.divide(
            self.successes,
            self.counts,
            out=np.zeros_like(self.successes),
            where=self.counts > 0,
        )

    def select(self) -> int:
        raise NotImplementedError

    def update(self, branch: int, reward: int) -> None:
        self.counts[branch] += 1
        self.successes[branch] += reward
        self.t += 1


class RoundRobin(Policy):
    name = "RoundRobin"

    def select(self) -> int:
        return self.t % self.k


class ExploreThenCommit(Policy):
    """Try every branch once, then exploit the best empirical mean."""

    name = "ExploreThenCommit"

    def select(self) -> int:
        untried = np.flatnonzero(self.counts == 0)
        if len(untried):
            return int(untried[0])
        return int(np.argmax(self.means))


class EpsilonGreedy(Policy):
    name = "EpsilonGreedy(e=0.1)"

    def __init__(
        self,
        k: int,
        rng: np.random.Generator,
        budget: int,
        epsilon: float = 0.10,
    ):
        super().__init__(k, rng, budget)
        self.epsilon = epsilon

    def select(self) -> int:
        untried = np.flatnonzero(self.counts == 0)
        if len(untried):
            return int(untried[0])
        if self.rng.random() < self.epsilon:
            return int(self.rng.integers(self.k))
        return int(np.argmax(self.means))


class UCB1(Policy):
    name = "UCB1"

    def select(self) -> int:
        untried = np.flatnonzero(self.counts == 0)
        if len(untried):
            return int(untried[0])
        bonus = np.sqrt(2.0 * np.log(max(self.t, 1)) / self.counts)
        return int(np.argmax(self.means + bonus))


class ThompsonSampling(Policy):
    name = "ThompsonSampling"

    def select(self) -> int:
        samples = self.rng.beta(
            1.0 + self.successes,
            1.0 + self.counts - self.successes,
        )
        return int(np.argmax(samples))


class DiscountedThompson(Policy):
    name = "DiscountedThompson(g=0.9)"

    def __init__(
        self,
        k: int,
        rng: np.random.Generator,
        budget: int,
        gamma: float = 0.90,
    ):
        super().__init__(k, rng, budget)
        self.gamma = gamma
        self.discounted_successes = np.zeros(k, dtype=float)
        self.discounted_failures = np.zeros(k, dtype=float)

    def select(self) -> int:
        samples = self.rng.beta(
            1.0 + self.discounted_successes,
            1.0 + self.discounted_failures,
        )
        return int(np.argmax(samples))

    def update(self, branch: int, reward: int) -> None:
        self.discounted_successes *= self.gamma
        self.discounted_failures *= self.gamma
        self.discounted_successes[branch] += reward
        self.discounted_failures[branch] += 1 - reward
        super().update(branch, reward)


POLICIES = (
    RoundRobin,
    ExploreThenCommit,
    EpsilonGreedy,
    UCB1,
    ThompsonSampling,
    DiscountedThompson,
)
