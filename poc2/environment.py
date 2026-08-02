"""
Simulated relationship-search environment.

Models the decision problem inside a relationship search agent:
a seed entity has K candidate branches (relationship paths / entity
neighbourhoods). Each expansion costs one unit of budget (one retrieval +
one relevance judgement) and either surfaces a new relevant relationship
or does not.

Two properties make this the real problem rather than a textbook bandit:

  1. Branch yields are hidden. The agent only learns by spending budget.
  2. Branches DEPLETE. A branch holds a finite pool of relevant items;
     as it is mined its hit rate falls. Search is non-stationary, so a
     policy that locks onto an early winner eventually starves.

The agent's job: maximise relationships found within a fixed budget.
"""

from dataclasses import dataclass, field
import numpy as np


@dataclass
class Regime:
    """A task archetype — the 'goal' in Agent Brain Platform terms."""
    name: str
    description: str
    base_yields: list      # intrinsic hit rate per branch when untouched
    pool_sizes: list       # how many relevant items each branch holds
    budget: int            # total expansions allowed

    @property
    def k(self) -> int:
        return len(self.base_yields)


class RelationshipSearchEnv:
    """Budgeted, depleting, multi-branch search."""

    def __init__(self, regime: Regime, rng: np.random.Generator):
        self.regime = regime
        self.rng = rng
        self.base = np.array(regime.base_yields, dtype=float)
        self.pool = np.array(regime.pool_sizes, dtype=float)
        self.remaining = self.pool.copy()
        self.budget = regime.budget
        self.spent = 0

    def current_yield(self, branch: int) -> float:
        """Hit probability now — falls linearly as the branch is mined."""
        if self.pool[branch] <= 0:
            return 0.0
        return float(self.base[branch] * (self.remaining[branch] / self.pool[branch]))

    def expand(self, branch: int) -> int:
        """Spend one unit of budget on `branch`. Returns 1 if a relevant
        relationship was found, else 0."""
        if self.spent >= self.budget:
            raise RuntimeError("budget exhausted")
        self.spent += 1
        p = self.current_yield(branch)
        if self.rng.random() < p:
            self.remaining[branch] -= 1
            return 1
        return 0

    def done(self) -> bool:
        return self.spent >= self.budget


# ── Task archetypes ──────────────────────────────────────────────────────
# Each regime is a different shape of search problem. If the best control
# policy is the same in all of them, goal-aware technique selection has no
# value and the platform premise fails.

K = 12

REGIMES = [
    Regime(
        name="uniform",
        description="All branches roughly equal. CONTROL CONDITION — "
                    "no policy should win here; any 'winner' is noise.",
        base_yields=[0.45] * K,
        pool_sizes=[40] * K,
        budget=50,
    ),
    Regime(
        name="needle",
        description="One rich branch hidden among poor ones. Finding it "
                    "fast is everything.",
        base_yields=[0.75] + [0.10] * (K - 1),
        pool_sizes=[60] + [25] * (K - 1),
        budget=50,
    ),
    Regime(
        name="deceptive",
        description="A dazzling but shallow branch runs dry fast, while the "
                    "richest branch looks mediocre on a single sample. "
                    "Punishes committing to first impressions.",
        # branch 0: irresistible on sample, only 10 items -> the trap
        # branch 1: low per-pull yield, 100 items -> the real prize,
        #           and one sample of it looks like noise
        base_yields=[0.95, 0.30] + [0.12] * (K - 2),
        pool_sizes=[10, 100] + [20] * (K - 2),
        budget=50,
    ),
    Regime(
        name="scarce",
        description="Budget barely covers one look per branch. Exploration "
                    "is a luxury you cannot afford.",
        base_yields=[0.75] + [0.10] * (K - 1),
        pool_sizes=[60] + [25] * (K - 1),
        budget=14,
    ),
    Regime(
        name="rich",
        description="Budget far exceeds what any single branch holds. "
                    "Everything gets found eventually; only order differs.",
        base_yields=[0.75] + [0.10] * (K - 1),
        pool_sizes=[60] + [25] * (K - 1),
        budget=200,
    ),
]

REGIME_BY_NAME = {r.name: r for r in REGIMES}
