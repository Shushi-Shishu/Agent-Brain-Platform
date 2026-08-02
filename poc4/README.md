# POC 4 — Cheap Workload Identification

## Verdict

**FAIL under the rules locked before the first run.**

A true-regime oracle could improve reward, but the cheap detector could not
identify the useful exception and made performance worse.

## Objective

POC 2b found that the suitable policy can depend on hidden workload shape.
POC 4 asked whether a small initial probe could discover enough of that shape
to select a better policy after accounting for the probe's opportunity cost.

This is the bridge required for an automatic recommendation product:

```text
Observe a small sample
        ↓
Identify workload
        ↓
Select policy
        ↓
Earn more than a strong fixed default
```

## Approach

The test used:

- 12 branches;
- a total budget of 48 pulls;
- four equally likely hidden workload shapes;
- six fixed candidate policies;
- probe sizes of 3, 5, and 8 pulls;
- a standardized 31-nearest-neighbor detector;
- 2,000 selection worlds;
- 6,000 separate confirmation worlds.

Probe pulls produced reward and consumed the same task budget. The selected
continuation policy received the probe history. Every strategy faced the same
per-branch potential outcomes.

The selection stage locked:

- best fixed policy: `ExploreThenCommit`;
- stationary needle: `ExploreThenCommit`;
- depleting needle: `ExploreThenCommit`;
- deceptive depleting: `UCB1(c=2.0)`;
- heterogeneous depleting: `ExploreThenCommit`;
- probe size: 3 pulls.

The same-probe fixed-policy control separated the value of classification from
the effect of taking the probe itself.

## Locked output

| Condition | Effect | Verdict |
|---|---:|---|
| Free oracle vs best fixed | +2.22% | PASS |
| Probe oracle vs probe fixed | +2.11% | PASS |
| Probe detector vs probe fixed | −2.36% | FAIL |
| Probe detector vs best fixed from start | −2.43% | FAIL |

All four conditions were required, so POC 4 failed.

The paired 95% confidence interval for the detector's reward loss versus the
best fixed policy was `[-0.556, -0.381]` findings per task. The loss was not
sampling ambiguity.

## Detector behavior

The locked detector achieved:

- exact workload accuracy: **25.15%**;
- random-chance workload accuracy: **25%**;
- policy-selection accuracy: **71.93%**;
- implicit policy accuracy from always using the fixed policy: **75%**.

Three workloads used `ExploreThenCommit`; only deceptive-depleting used UCB.
The detector recognized only 53 of 1,500 deceptive worlds. It also selected
UCB incorrectly on other workloads. Those false switches erased the small
oracle opportunity.

### Confusion matrix

Rows are actual workloads and columns are predictions.

| Actual \ Predicted | stationary | depleting | deceptive | heterogeneous |
|---|---:|---:|---:|---:|
| stationary needle | 1,435 | 0 | 51 | 14 |
| depleting needle | 1,435 | 0 | 54 | 11 |
| deceptive depleting | 1,424 | 0 | 53 | 23 |
| heterogeneous depleting | 1,347 | 0 | 132 | 21 |

Exact labels are less important than choosing the correct policy, but the
detector was also worse than the trivial fixed-policy choice on that measure.

## Secondary probe sizes

| Probe | Exact accuracy | Policy accuracy | Versus probe fixed | Versus fixed from start |
|---:|---:|---:|---:|---:|
| 3 pulls | 25.15% | 71.93% | −2.36% | −2.43% |
| 5 pulls | 26.60% | 74.80% | −0.15% | −0.63% |
| 8 pulls | 27.40% | 75.00% | 0.00% | −1.33% |

These are secondary because the 3-pull probe was locked using selection data.
Still, none of the alternatives created positive classification value.

## Meaning for the product

The experiment found both sides of the problem:

1. Policy selection had genuine value, but its maximum was small: 2.22%.
2. Identification errors cost more than that available gain.

Therefore, the current automatic-recommendation concept is not supported:

> A small sample from one task is not enough to infer the hidden workload and
> safely switch controllers.

The evidence favors a measurement product:

- replay multiple historical tasks;
- compare candidate controllers directly;
- use shadow or controlled live evaluation;
- retain a strong default unless switching evidence exceeds its error cost;
- monitor whether the measured workload changes.

Natural-language descriptions and short probes can help generate hypotheses,
but they should not be treated as sufficient evidence for controller choice.

## What remains untested

- Detectors trained on many historical tasks from the user's real workload
- Decision-boundary prediction instead of exact workload classification
- Learned or adaptive probe schedules
- Larger probe budgets
- Distribution shift and unseen workloads
- Real LLM, retrieval, search, or debugging agents
- Controller, evaluator, latency, and monetary costs

## Reproduce

```bash
cd poc4
python -m unittest -v
python experiment.py
```

The runner exits with code `2` because the locked verdict is FAIL. Full
machine-readable results are in `results.json`.
