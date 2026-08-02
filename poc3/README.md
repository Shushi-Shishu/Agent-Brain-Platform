# POC 3 — Sensitivity Study

## Verdict

**FAIL under the rules locked before the first run.**

The simulation supports workload- and parameter-sensitive testing, but it does
not support the preregistered broad fixed-policy generalization.

## What was tested

POC 3 inherited the corrected POC 2b design:

- randomized semantic branch labels;
- identical per-branch potential outcomes for every policy in a trial;
- a stationary no-effect control;
- finite urns that consume successes and failures;
- separate selection and confirmation samples;
- a real simple baseline, `ExploreThenCommit`.

The primary grid contained:

- branch counts: `K = 5, 12, 30`;
- budgets per branch: `1, 4, 16`;
- five workload shapes at every size-budget setting;
- six fixed policies;
- 250 selection trials and 750 confirmation trials per cell.

This produced 45 primary cells. A second analysis tested 13 configurations
across four adaptive families in the 12 non-control cells at `K=12`.

See `PREREGISTRATION.md` for the definitions and locked thresholds.

## Locked results

| Condition | Required | Observed | Verdict |
|---|---:|---:|---|
| Stationary controls pass | 9/9 | 9/9; maximum gap 1.45% | PASS |
| Fixed policies swing in ≥3 settings | ≥2 | 1 | FAIL |
| `ExploreThenCommit` viable in settings | ≥6/9 | 4/9 | FAIL |
| Parameter-robust adaptive families | ≥2 | 4 | PASS |

The whole POC fails because every condition was required.

## Fixed-policy persistence

A policy "swings" in a size-budget setting when it is viable in at least one
non-control workload shape and disqualified in another.

| Policy | Swinging settings out of 9 |
|---|---:|
| `UCB1(c=2.0)` | 4 |
| `ThompsonSampling(prior=1.0)` | 2 |
| `DiscountedThompson(g=0.9)` | 2 |
| `RoundRobin` | 1 |
| `ExploreThenCommit` | 1 |
| `EpsilonGreedy(e=0.1)` | 1 |

Only UCB met the persistence threshold of three settings.

## Setting-level result

| Setting | Control max gap | ETC viable somewhere? | Swinging fixed policies |
|---|---:|---|---|
| K=5, B/K=1 | 1.45% | No | none |
| K=5, B/K=4 | 0.51% | Yes | RoundRobin |
| K=5, B/K=16 | 0.65% | No | UCB, Discounted Thompson |
| K=12, B/K=1 | 1.31% | No | none |
| K=12, B/K=4 | 0.62% | Yes | UCB, Thompson, Discounted Thompson |
| K=12, B/K=16 | 0.77% | No | Epsilon Greedy, UCB |
| K=30, B/K=1 | 1.25% | No | none |
| K=30, B/K=4 | 0.60% | Yes | UCB, Thompson |
| K=30, B/K=16 | 0.19% | Yes | ExploreThenCommit |

`ExploreThenCommit` was viable somewhere in all three `B/K=4` settings and in
the largest high-budget setting. That is meaningful coverage, but below the
locked 6/9 requirement.

## Parameter sensitivity

All four adaptive families passed the parameter-robust swing rule:

| Family | Configurations that swing |
|---|---:|
| Epsilon Greedy | 2 of 3 |
| UCB | 4 of 4 |
| Thompson Sampling | 3 of 3 |
| Discounted Thompson | 3 of 3 |

This does not rescue the primary verdict. It changes the product lesson:
choosing a technique family is insufficient; parameter calibration can change
whether the same family is viable or disqualified.

## Additional evidence

Across 36 non-control primary cells:

| Policy | Viable | Uncertain | Disqualified |
|---|---:|---:|---:|
| Discounted Thompson | 9 | 10 | 17 |
| Epsilon Greedy | 8 | 23 | 5 |
| ExploreThenCommit | 10 | 15 | 11 |
| RoundRobin | 1 | 11 | 24 |
| Thompson Sampling | 23 | 7 | 6 |
| UCB | 6 | 15 | 15 |

The locked reference materially exceeded `ExploreThenCommit` beyond the 2%
floor in 25 of 36 non-control cells. The largest raw uplift was 111.31% in the
`K=5`, `B/K=16`, deceptive-depleting simulation. These numbers describe the
hand-designed simulation only and are not forecasts for live agents.

## Product interpretation

Supported:

- the test harness has valid no-effect controls across the tested grid;
- workload and budget can change whether a fixed policy is acceptable;
- reasonable hyperparameter choices can change viability;
- a simple baseline is sometimes sufficient and sometimes very costly.

Not supported:

- universal star ratings or a universal best policy;
- broad robustness of the POC 2b fixed-policy result;
- a static mapping from a natural-language task to a controller;
- production value or transfer to an LLM agent.

The evidence favors a workbench that measures and calibrates candidate
controllers against a workload contract. It does not yet justify building a
general block registry or recommendation UI.

## Reproduce

```bash
cd poc3
python -m unittest -v
python experiment.py
```

The experiment exits with code `2` because the locked verdict is FAIL. The
machine-readable record is `results.json`.
