# POC 3 — Sensitivity Preregistration

**Locked before first execution**: 2026-07-28

## Question

Does POC 2b's regime-dependent policy viability persist when the number of
branches, available budget, workload shape, and reasonable policy parameters
change?

POC 3 protects against building a product around one convenient simulation
setting.

## Inherited corrections

POC 3 uses POC 2b's corrected design:

- Semantic branch labels are randomized every trial.
- Policies face identical per-branch potential outcomes.
- Stationary control branches have equal expected reward.
- Finite urns consume successes and failures.
- Selection and confirmation seeds are disjoint.
- The simple baseline is `ExploreThenCommit`, not an LLM proxy.

## Primary grid

### Branch counts

`K ∈ {5, 12, 30}`

### Budget multipliers

`budget / K ∈ {1, 4, 16}`

This creates nine size-budget settings.

### Workload shapes

One control and four non-control shapes are evaluated at every setting:

1. `stationary_uniform` — equal stationary branches
2. `stationary_needle` — one strong stationary branch
3. `depleting_needle` — one strong finite branch
4. `deceptive_depleting` — a shallow high-rate trap and a sustainable branch
5. `heterogeneous_depleting` — one strong finite branch among moderate finite
   branches

Finite pool sizes scale with `K` so the relative workload shape remains
approximately comparable.

### Fixed primary policies

- `RoundRobin`
- `ExploreThenCommit`
- `EpsilonGreedy(e=0.1)`
- `UCB1(c=2.0)`
- `ThompsonSampling(prior=1.0)`
- `DiscountedThompson(g=0.9)`

### Trials

- Selection trials per cell: `250`
- Confirmation trials per cell: `750`
- Selection base seed: `20260728`
- Confirmation offset: `2_000_000`
- Policy randomness uses a separate deterministic seed stream.

A cell is one `(K, budget multiplier, workload shape)` combination. The
highest selection mean becomes the locked reference for that cell.

## Classification

The POC 2b classification is retained:

- **viable** when the lower 95% paired normal confidence bound of
  `mean(policy - 0.95 * locked_reference)` is at least zero
- **disqualified** when the upper 95% paired normal confidence bound of
  `mean(policy - 0.80 * locked_reference)` is below zero
- **uncertain** otherwise

A policy **swings in a setting** when it is viable in at least one of the four
non-control workload shapes and disqualified in at least one other at the same
`K` and budget multiplier.

## Parameter perturbation

At `K = 12`, on the same three budgets and four non-control workload shapes,
the following configurations are compared with the primary cell's locked
reference:

- Epsilon Greedy: `epsilon ∈ {0.05, 0.10, 0.20}`
- UCB: `c ∈ {0.5, 1.0, 2.0, 4.0}` in
  `sqrt(c * log(t) / pulls)`
- Thompson Sampling symmetric Beta prior:
  `prior ∈ {0.5, 1.0, 2.0}`
- Discounted Thompson: `gamma ∈ {0.80, 0.90, 0.97}`

Base configurations reuse primary confirmation scores. Additional variants use
the same confirmation worlds. Parameter analysis has no separate selection
stage and cannot replace a primary locked reference.

A family has a **parameter-robust swing** when at least two configurations in
that family are viable somewhere and disqualified somewhere across the twelve
`K=12` non-control cells.

## Primary pass/fail rules

POC 3 **passes** only if all conditions hold:

1. **Controls remain fair:** in every one of the nine stationary-uniform
   control cells, the maximum confirmation mean difference between any two
   policies is at most 3% of that cell's grand mean.
2. **Persistent regime dependence:** at least two primary fixed policies swing
   in at least three of the nine size-budget settings.
3. **Simple policy sometimes sufficient:** `ExploreThenCommit` is viable in at
   least one non-control shape in at least six of nine settings.
4. **Not a single-parameter artifact:** at least two adaptive policy families
   have a parameter-robust swing.

POC 3 **fails** if any condition fails. Thresholds will not be changed after
execution. Corrections require a new POC identifier.

## Secondary outputs

The experiment also reports:

- Confirmation ranking in every cell
- Which policy families are most sensitive to parameters
- Material locked-reference improvement beyond 2% over ExploreThenCommit
- Counts of viable, uncertain, and disqualified results

These do not affect the locked verdict.

## Limitations fixed in advance

- Simulation only
- Hand-designed workload families
- Binary rewards
- Exploration decision block only
- Equal external pull cost
- No controller computation or LLM-evaluator cost
- Fixed thresholds inherited from POC 2b
- Normal confidence approximation with 750 confirmation trials
- Parameter analysis only at `K=12`
- No learned or automatically inferred workload description
- No production workload mixture or prevalence estimate
