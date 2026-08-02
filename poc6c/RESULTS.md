# POC 6c Diagnostic Results

**Date:** 2026-07-31  
**Status:** instrumentation and configuration selection; no product verdict

## What was tested

The same collaboration runtime was assigned matched tasks under two control
styles:

- a strong generic agent;
- a configured Agent Brain controller with explicit planning, exploration,
  critic, budget, and stopping decisions appropriate to the workload.

Tasks, public data, tool scope, and hard task budgets were matched. Private
evaluators, exact corpus checks, workspace hashes, and leakage canaries were
used where applicable. Provider model identity, tokens, cost, and hard OS
isolation were not available, so every result below is diagnostic.

## Results by workload

| Workload | Generic | Configured | Diagnostic decision |
|---|---:|---:|---|
| Search Candidate 1 | 84.6 / 87.2 mean blind quality | 76.5 / 80.6 | Reject Candidate 1 |
| Search Candidate 2 | 77.3 / 80.8 | 83.3 / 85.6 | Provisionally select Candidate 2 |
| Code development | 4/5 tasks passed | 5/5 tasks passed | Configured selection signal |
| Code review | 5/5 valid outputs; one FP | 3/5 valid outputs; no FP on valid runs | Retain generic baseline |
| Code testing | 2.6/3 faults exposed per task | 2.8/3 | Configured selection signal |

Search values show evaluator 1 / evaluator 2. Absolute score levels moved
between evaluator cohorts, but within-pair direction was consistent:

- Candidate 1 configured-minus-generic: -8.1 and -6.6 points;
- Candidate 2 configured-minus-generic: +6.0 and +4.8 points;
- evaluator pair-preference agreement: 90% in both runs.

## What changed in real behavior

- Search Candidate 1 stopped after fewer reads but left evidence gaps
  unbounded. Candidate 2 made sentence support and explicit gap handling hard
  stopping conditions and reversed the selection direction.
- In code development, both arms solved four tasks. On CSV parsing, both used
  the correct standard parser, but only the configured test critic challenged
  whitespace-only blank records and passed the evaluator-only boundary test.
- In code review, structure did not help. Valid paired reviews were perfect
  ties, while the configured arm violated the JSON contract twice.
- In code testing, four pairs tied. The configured tester allocated a test to
  a numerical-weighting risk that exposed one additional seeded fault.

This is exactly the platform behavior the vision requires: select a controller
where evidence supports it and retain the generic baseline where added
structure does not help.

## Instrumentation defects found and repaired

The pilot also tested the benchmark:

1. exact citation validation found paraphrased excerpts and unindexed note
   paths before scoring;
2. the initial review scorer incorrectly required an undisclosed exact
   category label;
3. the review JSON validator incorrectly rejected distinct findings sharing a
   source location/category;
4. the testing harness initially treated interpreter cache files as
   unauthorized edits.

Each issue was repaired and regression-tested. Pre-repair review reports are
retained and excluded from summaries.

## Why no percentage is extrapolated

The transfer workloads contain five seen pilot tasks each. Search Batch 1 was
also inspected during design. These samples can select or reject candidate
controllers, but cannot estimate market-wide uplift.

Formal search confirmation now has:

- 32 frozen tasks;
- an anchored 100-point rubric;
- frozen generic and Candidate 2 prompt hashes;
- a task-level analysis and pass/fail draft.

It cannot activate until model/evaluator versions, token/cost telemetry,
deterministic corpus-only access, secret mapping custody, and hard execution
isolation satisfy
[`confirmation/PREREGISTRATION_DRAFT.md`](confirmation/PREREGISTRATION_DRAFT.md).

## Current view

The platform idea remains promising, but the evidence argues for a
measurement-and-retention product, not a universal “configured is better”
claim:

- search configuration matters and a bad controller can materially hurt;
- explicit test criticism produced small real transfer signals in development
  and test design;
- review showed that more structure can add failure modes;
- the platform's valuable action is often to keep the generic baseline.

No transaction economics are populated until a confirmation effect and
auditable cost data exist. The calculation code is ready, but missing values
remain missing rather than being invented.
