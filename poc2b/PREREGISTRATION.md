# POC 2b — Preregistration

**Locked before first execution**: 2026-07-28

## Question

After removing branch-position leakage and using a genuine no-effect control,
do fixed agent-control policies still have materially different viability
across task regimes?

This POC tests a narrow claim:

> Workload structure can disqualify some control policies, so an agent
> decision platform may create value by testing policies rather than blindly
> recommending one universal default.

It does **not** test transfer to a live LLM agent, automatic discovery of the
regime, or the broader multi-block platform.

## Corrections relative to POC 2

1. The high-yield, trap, and sustainable branches are randomly relabelled on
   every trial.
2. The uniform control is stationary, so allocation policy has no expected
   effect.
3. Each trial creates a fixed potential-outcome stream for every branch. Every
   policy faces the same per-branch outcomes, even when policies pull branches
   in different orders.
4. Depleting branches use finite urns. Successes and failures are both consumed.
5. `Greedy(LLM-proxy)` is renamed `ExploreThenCommit`; no claim is made about
   real LLM behaviour.
6. Policy selection and confirmation use disjoint seeds.
7. Viability thresholds and tests are locked below before results are run.
8. Controller overhead is reported as unmeasured rather than assumed equal to
   zero in the real world.

## Policies

- `RoundRobin`
- `ExploreThenCommit`
- `EpsilonGreedy(e=0.1)`
- `UCB1`
- `ThompsonSampling`
- `DiscountedThompson(g=0.9)`

These are fixed configurations, not optimized policy families. Conclusions
apply only to these configurations.

## Regimes

One genuine control and five deliberately different workloads:

1. `stationary_uniform` — equal stationary Bernoulli branches
2. `stationary_needle` — one high-yield stationary branch
3. `depleting_needle` — one high-yield finite branch
4. `deceptive_depleting` — a high-rate shallow trap plus a sustainable branch
5. `scarce_stationary` — a needle problem with only `K + 2` pulls
6. `rich_depleting` — sufficient budget to exhaust attractive finite branches

Regimes are hand-designed stress tests. They do not estimate the prevalence of
these workloads in production.

## Sample and seed split

- `K = 12`
- Selection trials per regime: `1000`
- Confirmation trials per regime: `2000`
- Selection seeds: `20260728 + [0, 999]`
- Confirmation seeds: `20260728 + 1_000_000 + [0, 1999]`
- Policy randomness uses a separate deterministic seed stream.

The highest-mean policy on the selection split becomes the locked reference
for that regime. All classifications and pass/fail decisions use only the
confirmation split.

## Classification

For policy score vector `P` and locked reference score vector `R`:

- **viable** if the lower 95% normal confidence bound of
  `mean(P - 0.95 * R)` is at least zero
- **disqualified** if the upper 95% normal confidence bound of
  `mean(P - 0.80 * R)` is below zero
- **uncertain** otherwise

The paired construction is used in every comparison. With 2,000 bounded
confirmation observations, normal confidence intervals are the pre-registered
approximation.

## Primary pass/fail rules

POC 2b **passes** only if all conditions hold:

1. **Valid control:** for every policy pair in `stationary_uniform`, the paired
   95% confidence interval for the mean difference lies entirely within
   `+/- 2%` of the confirmation grand mean.
2. **Regime-dependent disqualification:** at least two fixed policy
   configurations are viable in at least one non-control regime and
   disqualified in at least one other non-control regime.
3. **Non-universal sophistication:** `ExploreThenCommit` is viable in at least
   one non-control regime.

POC 2b **fails** if any condition fails. A failure withdraws POC 2's claim that
the current simulation supports a policy-linting product.

## Secondary, non-gating result

For each regime, compare the locked reference with `ExploreThenCommit`.
An adaptive-policy improvement is called material only when the lower 95%
confidence bound of:

`reference - 1.02 * ExploreThenCommit`

is above zero.

This result is descriptive and does not affect the primary verdict.

## Known limitations fixed in advance

- Simulation only; no LLM or real retrieval system
- Hand-designed regimes
- One decision block: exploration
- One value of `K`
- Fixed policy hyperparameters
- Binary rewards
- Equal external pull cost
- No measured controller computation or LLM-evaluation overhead
- No delayed, corrupted, or missing feedback
- No automatic regime identification

Sensitivity across `K`, budgets, parameters, and regime mixtures remains POC 3.
Transfer remains POC 6.
