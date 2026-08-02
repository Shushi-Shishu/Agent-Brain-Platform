# POC 2b — Corrected Confirmatory Test

**Date**: 2026-07-28  
**Status**: PASS under the locked primary rules  
**Preregistration**: [`PREREGISTRATION.md`](./PREREGISTRATION.md)

## Question

After removing branch-position leakage and using a genuine no-effect control,
do fixed agent-control policies still have materially different viability
across task regimes?

## What was corrected

- Semantic branch identities are randomly relabelled every trial.
- The uniform control is stationary and has no expected policy effect.
- Every policy faces the same pre-generated outcome stream for every branch.
- Finite branches consume successes and failures.
- The baseline is honestly named `ExploreThenCommit`; it is not called an LLM
  proxy.
- Policy selection and confirmation use disjoint seeds.
- Status thresholds and pass/fail conditions were written before execution.

## Locked design

- 6 regimes
- 6 fixed policy configurations
- `K = 12`
- 1,000 selection trials per regime
- 2,000 independent confirmation trials per regime
- Paired potential outcomes

The selection split chooses one locked reference policy per regime. All
classification and pass/fail decisions use only confirmation data.

## Confirmatory results

| Regime | Locked reference | ExploreThenCommit | Material reference uplift beyond 2% |
|---|---|---:|---:|
| stationary uniform control | RoundRobin | 16.79 | No |
| stationary needle | ExploreThenCommit | 22.74 | No |
| depleting needle | ExploreThenCommit | 22.04 | No |
| deceptive depleting | UCB1 | 10.10 | **Yes — raw +13.44%** |
| scarce stationary | ThompsonSampling | 2.76 | No |
| rich depleting | ThompsonSampling | 51.06 | **Yes — raw +44.45%** |

`ExploreThenCommit` is the confirmation mean shown above, not the reference
mean where another reference was locked.

### Policy viability by non-control regime

`V` = viable · `U` = uncertain · `D` = disqualified

| Policy | stationary needle | depleting needle | deceptive | scarce | rich |
|---|---:|---:|---:|---:|---:|
| RoundRobin | D | D | D | D | D |
| ExploreThenCommit | V | V | U | V | D |
| EpsilonGreedy(0.1) | U | V | U | U | U |
| UCB1 | D | D | V | U | V |
| ThompsonSampling | D | D | V | V | V |
| DiscountedThompson(0.9) | D | D | V | U | D |

Four policies satisfy the locked swing rule: viable in at least one
non-control regime and disqualified in another:

- ExploreThenCommit
- UCB1
- ThompsonSampling
- DiscountedThompson(0.9)

## Pre-registered verdict

| Required condition | Result |
|---|---|
| Every policy pair equivalent within ±2% in the stationary uniform control | PASS |
| At least two policies viable somewhere and disqualified elsewhere | PASS — four |
| ExploreThenCommit viable in at least one non-control regime | PASS |

**POC 2b: PASS**

## Interpretation

Within this simulation and these fixed configurations:

1. No single policy is safe to present as a universal default.
2. Simple control is sufficient in several regimes.
3. Adaptive control can create a large material gain in some regimes.
4. The useful product behavior is to test, reject, and explain—not assign
   generic star ratings.

This supports continuing research into a policy-linting and evidence engine. It
does **not** validate automatic natural-language recommendation, transfer to
real agents, or the complete Agent Brain Platform.

## Limitations

- Simulated binary rewards
- Hand-designed stress-test regimes
- One decision block
- One branch count (`K = 12`)
- Fixed policy hyperparameters
- Equal external pull cost
- No controller-computation or LLM-evaluation overhead
- No missing, delayed, or corrupted feedback
- No automatic regime identification
- No live LLM-agent transfer

POC 3 must test sensitivity across `K`, budgets, parameters, and workload
mixtures. POC 4 must test whether the relevant workload structure can be
identified cheaply.

## Reproduce

```powershell
cd poc2b
python -m unittest -v
python experiment.py
```

On the reference Windows workspace the confirmatory run took approximately
106 seconds and required only NumPy.

`experiment.py` exits with code `0` on PASS and `2` on FAIL. Full output is in
[`results.json`](./results.json).
