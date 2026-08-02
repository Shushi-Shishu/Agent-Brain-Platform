"""
Control policies for the exploration/exploitation decision point.

Every policy answers the same question the agent faces on each step:
"which branch do I expand next?" — the decision an unguided agent
currently makes by asking the LLM.

Interface:
    select() -> int          which branch to expand
    update(branch, reward)   observe the outcome
"""

import numpy as np


class Policy:
    name = "base"

    def __init__(self, k: int, rng: np.random.Generator, budget: int):
        self.k = k
        self.rng = rng
        self.budget = budget
        self.counts = np.zeros(k)
        self.successes = np.zeros(k)
        self.t = 0

    def select(self) -> int:
        raise NotImplementedError

    def update(self, branch: int, reward: int):
        self.counts[branch] += 1
        self.successes[branch] += reward
        self.t += 1

    @property
    def means(self):
        with np.errstate(invalid="ignore", divide="ignore"):
            m = np.where(self.counts > 0, self.successes / np.maximum(self.counts, 1), 0.0)
        return m


class RoundRobin(Policy):
    """Naive baseline: spread budget evenly. 'Search everything a bit.'"""
    name = "RoundRobin"

    def select(self) -> int:
        return self.t % self.k


class Greedy(Policy):
    """Proxy for an unguided LLM loop: sample each branch once, then commit
    to whatever looks best so far. Latches onto early winners — the
    characteristic failure of 'let the model decide'."""
    name = "Greedy(LLM-proxy)"

    def select(self) -> int:
        untried = np.flatnonzero(self.counts == 0)
        if len(untried) > 0:
            return int(untried[0])
        return int(np.argmax(self.means))


class EpsilonGreedy(Policy):
    name = "EpsilonGreedy"

    def __init__(self, k, rng, budget, epsilon: float = 0.10):
        super().__init__(k, rng, budget)
        self.epsilon = epsilon
        self.name = f"EpsilonGreedy(e={epsilon})"

    def select(self) -> int:
        untried = np.flatnonzero(self.counts == 0)
        if len(untried) > 0:
            return int(untried[0])
        if self.rng.random() < self.epsilon:
            return int(self.rng.integers(self.k))
        return int(np.argmax(self.means))


class UCB1(Policy):
    """Optimism under uncertainty. Requires one pull per branch to start —
    which is exactly what makes it expensive on tight budgets."""
    name = "UCB1"

    def select(self) -> int:
        untried = np.flatnonzero(self.counts == 0)
        if len(untried) > 0:
            return int(untried[0])
        bonus = np.sqrt(2.0 * np.log(max(self.t, 1)) / self.counts)
        return int(np.argmax(self.means + bonus))


class ThompsonSampling(Policy):
    """Bayesian posterior sampling over Beta(1+hits, 1+misses).
    Needs no initialisation sweep — it can commit early on prior
    uncertainty alone, which matters when budget is tight."""
    name = "ThompsonSampling"

    def select(self) -> int:
        samples = self.rng.beta(1.0 + self.successes,
                                1.0 + (self.counts - self.successes))
        return int(np.argmax(samples))


class DiscountedThompson(Policy):
    """Thompson with a decay on old evidence — designed for NON-STATIONARY
    problems, i.e. branches that deplete. Forgets that a now-exhausted
    branch used to be good."""
    name = "DiscountedThompson"

    def __init__(self, k, rng, budget, gamma: float = 0.90):
        super().__init__(k, rng, budget)
        self.gamma = gamma
        self.s = np.zeros(k)
        self.f = np.zeros(k)
        self.name = f"DiscountedThompson(g={gamma})"

    def select(self) -> int:
        samples = self.rng.beta(1.0 + self.s, 1.0 + self.f)
        return int(np.argmax(samples))

    def update(self, branch: int, reward: int):
        self.s *= self.gamma
        self.f *= self.gamma
        self.s[branch] += reward
        self.f[branch] += (1 - reward)
        super().update(branch, reward)


class OracleGreedy(Policy):
    """Reference upper bound. Sees true current yields and takes the best
    one every step. Greedy on a depleting problem is not provably optimal,
    so treat this as a strong reference line, not a true optimum."""
    name = "Oracle(reference)"

    def __init__(self, k, rng, budget, env=None):
        super().__init__(k, rng, budget)
        self.env = env

    def select(self) -> int:
        yields = np.array([self.env.current_yield(b) for b in range(self.k)])
        return int(np.argmax(yields))


POLICIES = [
    RoundRobin,
    Greedy,
    EpsilonGreedy,
    UCB1,
    ThompsonSampling,
    DiscountedThompson,
]
