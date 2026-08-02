"""Corrected potential-outcome environments for POC 2b.

Every trial materializes a binary outcome stream for each branch. A policy's
n-th pull of branch b receives outcomes[b, n]. Reusing the same matrix gives
all policies identical per-branch potential outcomes while allowing adaptive
policies to choose different branches at different times.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Regime:
    name: str
    description: str
    k: int
    budget: int
    mode: str
    rates: tuple[float, ...]
    pool_sizes: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"stationary", "finite_urn"}:
            raise ValueError(f"unsupported mode: {self.mode}")
        if len(self.rates) != self.k:
            raise ValueError("rates must have length k")
        if any(rate < 0 or rate > 1 for rate in self.rates):
            raise ValueError("rates must lie in [0, 1]")
        if self.mode == "finite_urn":
            if self.pool_sizes is None or len(self.pool_sizes) != self.k:
                raise ValueError("finite_urn requires one pool size per branch")
            if any(size < 0 for size in self.pool_sizes):
                raise ValueError("pool sizes must be non-negative")


def build_regimes(k: int = 12) -> list[Regime]:
    """Return the locked POC 2b regimes."""
    if k < 3:
        raise ValueError("k must be at least 3")

    return [
        Regime(
            name="stationary_uniform",
            description="True no-effect control: equal stationary branches.",
            k=k,
            budget=4 * k,
            mode="stationary",
            rates=(0.35,) * k,
        ),
        Regime(
            name="stationary_needle",
            description="One high-yield stationary branch among poor branches.",
            k=k,
            budget=4 * k,
            mode="stationary",
            rates=(0.75,) + (0.10,) * (k - 1),
        ),
        Regime(
            name="depleting_needle",
            description="One high-yield finite branch among finite poor branches.",
            k=k,
            budget=4 * k,
            mode="finite_urn",
            rates=(0.75,) + (0.10,) * (k - 1),
            pool_sizes=(64,) + (28,) * (k - 1),
        ),
        Regime(
            name="deceptive_depleting",
            description=(
                "A near-certain shallow trap competes with a lower-rate "
                "sustainable branch."
            ),
            k=k,
            budget=4 * k,
            mode="finite_urn",
            rates=(1.00, 0.38) + (0.10,) * (k - 2),
            pool_sizes=(7, 80) + (24,) * (k - 2),
        ),
        Regime(
            name="scarce_stationary",
            description="A stationary needle with budget for only K + 2 pulls.",
            k=k,
            budget=k + 2,
            mode="stationary",
            rates=(0.75,) + (0.10,) * (k - 1),
        ),
        Regime(
            name="rich_depleting",
            description=(
                "A long finite-urn run where controllers must exploit and "
                "then move after depletion."
            ),
            k=k,
            budget=16 * k,
            mode="finite_urn",
            rates=(0.75,) + (0.20,) * (k - 1),
            pool_sizes=(80,) + (30,) * (k - 1),
        ),
    ]


def _stationary_streams(regime: Regime, rng: np.random.Generator) -> np.ndarray:
    rates = np.asarray(regime.rates, dtype=float)
    return rng.binomial(1, rates[:, None], size=(regime.k, regime.budget)).astype(
        np.int8
    )


def _finite_urn_streams(regime: Regime, rng: np.random.Generator) -> np.ndarray:
    assert regime.pool_sizes is not None
    streams = np.zeros((regime.k, regime.budget), dtype=np.int8)
    for branch, (rate, pool_size) in enumerate(
        zip(regime.rates, regime.pool_sizes, strict=True)
    ):
        successes = int(round(rate * pool_size))
        urn = np.concatenate(
            (
                np.ones(successes, dtype=np.int8),
                np.zeros(pool_size - successes, dtype=np.int8),
            )
        )
        rng.shuffle(urn)
        visible = min(pool_size, regime.budget)
        streams[branch, :visible] = urn[:visible]
    return streams


def build_trial_outcomes(regime: Regime, seed: int) -> np.ndarray:
    """Create one relabelled potential-outcome world.

    Semantic branch identities are randomly mapped to observed branch labels
    on every trial. The returned matrix is immutable by convention.
    """
    rng = np.random.default_rng(seed)
    if regime.mode == "stationary":
        streams = _stationary_streams(regime, rng)
    else:
        streams = _finite_urn_streams(regime, rng)

    observed_labels = rng.permutation(regime.k)
    return streams[observed_labels]


class PotentialOutcomeEnv:
    """Consumes a fixed per-branch outcome stream."""

    def __init__(self, outcomes: np.ndarray, budget: int):
        if outcomes.ndim != 2:
            raise ValueError("outcomes must be a 2D array")
        if budget < 0 or outcomes.shape[1] < budget:
            raise ValueError("outcomes do not cover the requested budget")
        self.outcomes = outcomes
        self.budget = budget
        self.k = outcomes.shape[0]
        self.pulls = np.zeros(self.k, dtype=np.int32)
        self.spent = 0

    def pull(self, branch: int) -> int:
        if self.spent >= self.budget:
            raise RuntimeError("budget exhausted")
        if branch < 0 or branch >= self.k:
            raise IndexError(f"invalid branch: {branch}")
        pull_index = int(self.pulls[branch])
        self.pulls[branch] += 1
        self.spent += 1
        return int(self.outcomes[branch, pull_index])

    @property
    def done(self) -> bool:
        return self.spent >= self.budget
