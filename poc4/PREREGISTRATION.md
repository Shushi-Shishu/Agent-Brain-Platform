# POC 4 — Cheap Workload Identification Preregistration

**Locked before first execution**: 2026-07-28

## Question

Can a small, outcome-producing probe identify enough hidden workload structure
to choose a better branch-selection policy than the best fixed policy, after
paying the probe's opportunity cost?

POC 2b showed that policy viability can depend on workload shape. POC 3 showed
that broad fixed-policy robustness is not established. POC 4 tests the
load-bearing step between those findings and a useful product: detecting the
workload cheaply enough to act.

## Scope

The test uses one known observable contract:

- Branches: `K = 12`
- Total pull budget: `48` (`4 × K`)
- Binary rewards
- Equal pull cost

The hidden workload is drawn with equal probability from four POC 3 shapes:

1. `stationary_needle`
2. `depleting_needle`
3. `deceptive_depleting`
4. `heterogeneous_depleting`

The equal mixture is part of the locked estimand. Results do not claim a
production prevalence distribution.

## Candidate continuation policies

The fixed POC 3 configurations are retained:

- `RoundRobin`
- `ExploreThenCommit`
- `EpsilonGreedy(e=0.1)`
- `UCB1(c=2.0)`
- `ThompsonSampling(prior=1.0)`
- `DiscountedThompson(g=0.9)`

On the selection split:

- the highest equal-mixture mean becomes the locked **best fixed policy**;
- the highest mean within each workload shape becomes that shape's locked
  **oracle policy**.

No policy or parameter is added after confirmation begins.

## Probe

Probe fractions are:

- `5%` of budget: `ceil(0.05 × 48) = 3` pulls
- `10%` of budget: `ceil(0.10 × 48) = 5` pulls
- `15%` of budget: `ceil(0.15 × 48) = 8` pulls

The diagnostic schedule is fixed and outcome-independent:

1. Let `m = ceil(probe_pulls / 2)`.
2. Pull observed branches `0 ... m-1` once.
3. Use remaining probe pulls for a second pass over the same branches.

Semantic branch identities are randomized on every trial, so these labels do
not reveal the hidden regime. Probe rewards count toward total task reward.
After the probe, the chosen continuation policy receives the probe trace as
history and uses only the remaining budget.

## Detector

One detector is trained for each probe fraction. It receives only
permutation-invariant summaries of the probe trace:

- probe reward rate;
- fraction of branches sampled;
- fraction of sampled branches with a success;
- maximum and standard deviation of per-branch empirical reward rates;
- first-pass and repeat-pass reward rates;
- repeat-minus-first reward-rate change;
- success-to-failure and failure-to-success transition fractions;
- maximum successes on one sampled branch.

The detector is a standardized `k=31` nearest-neighbor classifier with
deterministic distance and label tie-breaking. It may predict only the four
locked workload labels.

## Selection and confirmation

- Selection trials: `500` per workload (`2,000` balanced trials)
- Confirmation trials: `1,500` per workload (`6,000` balanced trials)
- Selection base seed: `20260728`
- Confirmation seed offset: `4,000,000`
- Policy randomness uses a separate deterministic seed namespace.

Selection performs stratified five-fold out-of-fold evaluation for each probe
fraction. The fraction with the highest out-of-fold end-to-end mean reward is
locked; ties choose the smaller probe.

After selecting the fraction, its detector is refit on all selection traces.
Confirmation evaluates the locked strategy once. Confirmation results for the
other two fractions are secondary and cannot replace the locked choice.

All compared strategies face identical per-branch potential outcomes.

## Confirmation strategies

1. **Best fixed** — locked fixed policy from the first pull.
2. **Probe + best fixed** — diagnostic probe, then the locked best fixed
   policy with the probe history. This controls for the probe itself.
3. **Probe + detected policy** — diagnostic probe, predict workload, then use
   its locked oracle policy with the probe history.
4. **Probe + true-regime oracle** — same probe, then use the true workload's
   locked oracle policy. This measures the attainable value after probe cost.
5. **Free true-regime oracle** — true workload's locked oracle policy from the
   first pull. This measures whether policy-selection opportunity exists.

## Statistical and practical comparison

For paired confirmation scores `A` and `B`, a material win requires both:

1. `mean(A) / mean(B) - 1 >= 2%`; and
2. the lower 95% paired normal confidence bound of `mean(A - B)` is greater
   than zero.

The primary utility is mean total reward across the equal workload mixture.

## Primary pass/fail rules

POC 4 **passes only if all conditions hold**:

1. **Selection opportunity exists:** free true-regime oracle materially beats
   best fixed.
2. **Opportunity survives probe cost:** probe + true-regime oracle materially
   beats probe + best fixed at the locked probe fraction.
3. **Detection creates value:** probe + detected policy materially beats probe
   + best fixed at the locked probe fraction.
4. **Net task value is positive:** probe + detected policy materially beats
   best fixed from the first pull.

POC 4 **fails** if any condition fails. Thresholds, workload weights, probe
schedule, classifier, candidates, and trial counts will not change after the
first execution. Corrections require a new POC identifier.

## Secondary outputs

- Exact workload-classification accuracy
- Policy-selection accuracy (predicted and true workloads map to the same
  policy)
- Confusion matrix
- Per-workload rewards and paired effects
- Results for all three probe fractions
- Fraction of free-oracle gain captured

These outputs explain the result but do not alter the locked verdict.

## Limitations fixed in advance

- Simulation only
- One branch count and one budget
- Four hand-designed, equally weighted workloads
- The detector is trained on the exact workload families later tested
- Binary, immediate rewards
- Exploration decision block only
- No LLM, tool, evaluator, or controller-computation cost
- A fixed diagnostic schedule rather than a learned probe
- Normal confidence approximation
- Candidate policies and parameters inherited from POC 3
- No distribution shift or previously unseen workload family
