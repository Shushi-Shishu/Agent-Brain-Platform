# POC 5 — Stopping-Rule Generality Preregistration

**Locked before first execution**: 2026-07-28

## Question

Does workload-dependent decision logic appear at a second agent decision point:
when to stop?

POCs 2b–4 concerned branch selection. If stopping behavior also changes
between viable and harmful across workloads, the decision-block thesis extends
beyond one algorithm library. If one stopping rule is sufficient everywhere,
the broader platform claim weakens.

## Isolation strategy

Every stopping rule observes the same reward trajectory.

For each trial:

1. Materialize one randomized potential-outcome world.
2. Run one fixed `ThompsonSampling(prior=1.0)` branch-selection controller for
   the maximum budget.
3. Record its ordered binary reward trajectory.
4. Evaluate every stopping rule on prefixes of that identical trajectory.

Stopping rules cannot change branch selection. This isolates stopping from the
exploration decision tested earlier.

## Workload contract

- Branches: `K = 12`
- Maximum budget: `192` pulls (`16 × K`)
- Value per finding: `1.0`
- Cost per pull: `0.20`
- Net utility: `findings - 0.20 × pulls`

The five POC 3 workload shapes are:

1. `stationary_uniform`
2. `stationary_needle`
3. `depleting_needle`
4. `deceptive_depleting`
5. `heterogeneous_depleting`

The cost is part of the decision contract, not inferred by the stopper.

## Fixed stopping rules

1. **FixedBudget** — use all 192 pulls.
2. **FixedHalf** — stop after 96 pulls.
3. **PatienceStop(8)** — after at least 12 pulls, stop following eight
   consecutive failures. This is an honestly named proxy for informal
   "nothing useful is happening" behavior, not an LLM.
4. **WindowMarginal(24)** — after at least 24 pulls, stop when the reward rate
   in the last 24 pulls is at most the known pull cost, `0.20`.
5. **ConfidenceMarginal(24,z=1.28)** — after at least 24 pulls, stop when
   `p_hat + 1.28 * sqrt((p_hat*(1-p_hat)+0.25)/(window+2)) <= 0.20`.
6. **TrendMarginal(12+12)** — after at least 24 pulls, stop when the last
   12-pull reward rate is below `0.20` and at least `0.10` below the preceding
   12-pull rate.

Rules check only after observing a reward. Ties at the stopping threshold stop.
All configurations are fixed before execution.

## Selection and confirmation

- Selection trials: `500` per workload
- Confirmation trials: `1,500` per workload
- Selection base seed: `20260728`
- Confirmation seed offset: `6,000,000`
- Thompson policy randomness uses a separate deterministic seed namespace.

Within each workload, the rule with the highest selection mean net utility
becomes the locked reference. Ties follow the rule order listed above.
Confirmation seeds are disjoint and cannot change the reference.

## Classification

Against the locked reference on paired confirmation trajectories:

- **viable** when the lower 95% paired normal confidence bound of
  `rule - 0.95 × reference` is at least zero;
- **disqualified** when the upper 95% paired normal confidence bound of
  `rule - 0.80 × reference` is below zero;
- **uncertain** otherwise.

The reference's confirmation mean must be positive. A non-positive reference
invalidates relative classification and fails the POC.

A rule **swings** when it is viable in at least one workload and disqualified
in another.

## Zero-cost sanity control

On the same stationary-uniform confirmation trajectories, scores are also
computed with pull cost set to zero. Because binary findings are non-negative
and all rules consume prefixes of the same trajectory, `FixedBudget` must
weakly dominate every shorter prefix on every trial.

This validates shared-prefix and utility accounting. Failure invalidates the
POC.

## Primary pass/fail rules

POC 5 **passes only if all conditions hold**:

1. **Shared-prefix sanity passes:** `FixedBudget` weakly dominates every rule
   on every zero-cost stationary-uniform confirmation trial.
2. **Relative scoring is valid:** every locked reference has positive mean
   confirmation utility.
3. **Workload-dependent stopping exists:** at least one fixed stopping rule
   swings between viable and disqualified across workloads.
4. **Continuing is sometimes justified:** `FixedBudget` is viable in at least
   one workload.
5. **Early stopping is sometimes useful:** at least one of `PatienceStop`,
   `WindowMarginal`, `ConfidenceMarginal`, or `TrendMarginal` is viable in a
   workload while using at most 80% of the maximum budget on average.

POC 5 **fails** if any condition fails. Thresholds, workload shapes, cost,
rules, configurations, and trial counts will not change after the first
execution. Corrections require a new POC identifier.

## Secondary outputs

- Selection and confirmation ranking per workload
- Mean findings, pulls, and net utility
- Hindsight-optimal prefix utility as an unattainable ceiling
- Utility gained or lost relative to `FixedBudget`
- Viable/uncertain/disqualified table
- Which rules swing

These explain the result but cannot alter the locked verdict.

## Limitations fixed in advance

- Simulation only
- One branch-selection controller
- One branch count, maximum budget, finding value, and pull cost
- Five hand-designed workloads
- Binary, immediate rewards
- Stopping rules use fixed parameters
- No LLM, evaluator, latency, or monetary cost
- No terminal answer-quality constraint beyond accumulated findings
- No delayed reward or irreversible action
- Hindsight oracle is descriptive only
- Normal confidence approximation
