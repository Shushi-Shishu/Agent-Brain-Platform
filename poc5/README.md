# POC 5 — Stopping-Rule Generality

## Verdict

**PASS under all rules locked before the first run.**

Workload-dependent decision logic appeared at a second decision point:
deciding when to stop.

## Objective

Earlier POCs tested how an agent chooses which branch to investigate. POC 5
asked:

> Does the appropriate stopping rule also depend on the workload, or is one
> universal stopping rule sufficient?

If stopping showed the same viability/disqualification pattern, the concept
would extend beyond one branch-selection algorithm library.

## Approach

Stopping was isolated from exploration:

1. A fixed Thompson Sampling controller generated one complete 192-pull reward
   trajectory.
2. Every stopping rule received that identical trajectory.
3. Each rule selected a prefix length.
4. Utility included both findings and work performed:
   `utility = findings - 0.20 × pulls`.

The six rules were:

- full fixed budget;
- half fixed budget;
- an eight-failure patience heuristic;
- a recent-window marginal-value threshold;
- confidence-bound marginal stopping;
- trend-based marginal stopping.

The experiment used five workloads, 2,500 selection trajectories, and 7,500
separate confirmation trajectories.

## Locked output

All five required conditions passed:

| Condition | Verdict |
|---|---|
| Shared-prefix and zero-cost sanity | PASS |
| Positive reference utility in every workload | PASS |
| A rule becomes viable and disqualified across workloads | PASS |
| Full-budget continuation is viable somewhere | PASS |
| Efficient adaptive stopping is viable somewhere | PASS |

Four rules swung between viable and disqualified:

- `FixedBudget`
- `FixedHalf`
- `ConfidenceMarginal(24,z=1.28)`
- `TrendMarginal(12+12)`

## Best stopping behavior by workload

| Workload | Locked rule | Utility | Findings | Pulls |
|---|---|---:|---:|---:|
| Stationary uniform | FixedBudget | 28.96 | 67.36 | 192.0 |
| Stationary needle | FixedBudget | 74.05 | 112.45 | 192.0 |
| Depleting needle | FixedHalf | 26.12 | 45.32 | 96.0 |
| Deceptive depleting | TrendMarginal | 3.08 | 9.43 | 31.8 |
| Heterogeneous depleting | ConfidenceMarginal | 38.18 | 69.80 | 158.1 |

## Simple interpretation

When useful findings kept arriving, continuing was correct. When findings
depleted, continuing could destroy net value.

Examples:

- Stationary needle:
  - full budget: **74.05** utility;
  - half budget: **26.09**.
- Depleting needle:
  - half budget: **26.12**;
  - full budget: **17.11**.
- Deceptive depletion:
  - trend stopping: **+3.08** utility at 31.8 pulls;
  - full budget: **−3.16** utility at 192 pulls.
- Heterogeneous depletion:
  - confidence stopping: **38.18** utility at 158.1 pulls;
  - full budget: **35.34** at 192 pulls.

Therefore, “always continue” and “always stop early” were both wrong.

## Rejection is useful

The recent-window rule was disqualified in all five workloads. It reacted too
aggressively to short-term noise.

The informal patience heuristic was never viable. It was uncertain in the
deceptive workload and disqualified in the other four.

This supports a product that rejects dangerous stopping configurations rather
than presenting every mathematical technique as equally useful.

## Product meaning

Supported in this simulation:

- stopping is a distinct, testable decision block;
- the cost contract changes appropriate stopping behavior;
- advanced stopping is sometimes useful;
- fixed continuation is sometimes the correct answer;
- poorly calibrated mathematical and heuristic rules can both be harmful.

Not supported:

- automatically inferring the workload from task text;
- using one stopping rule across different costs;
- transfer to a real LLM agent;
- answer quality after early stopping;
- delayed rewards or evaluator costs;
- generalization beyond the five designed workloads.

POC 5 strengthens the measurement-workbench concept:

```text
Replay representative trajectories
        ↓
Apply candidate stopping rules to shared prefixes
        ↓
Measure quality, work, and cost
        ↓
Reject early-stop and overrun failures
        ↓
Deploy a tested rule
```

It does not reopen the broad product build gate because POCs 3 and 4 remain
failed.

## Reproduce

```bash
cd poc5
python -m unittest -v
python experiment.py
```

Machine-readable results are in `results.json`; the locked design is in
`PREREGISTRATION.md`.
