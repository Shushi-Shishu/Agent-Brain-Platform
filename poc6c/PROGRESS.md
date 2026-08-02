# POC 6c Progress

## 2026-07-31 — Autonomous execution checkpoint 1

Completed:

- corrected objective to matched generic-agent versus configured-agent value;
- cross-workload plan for search, code development, code review, and code
  testing;
- workload-specific transaction-economics formulas and draft gates;
- provider-independent trace schema and matched-pair validation;
- frozen Project 008 corpus facade with manifest and content commitments;
- traversal protection, deterministic BM25 search, and tool-budget enforcement;
- task-cluster bootstrap, randomization sensitivity, power planning, Holm
  adjustment, and portfolio economics;
- Batch 1 vault-only task fixture, generic/configured prompts, blind evaluator
  rubric, output formats, validation, and deterministic blinding;
- 34 local POC 6c tests passing before pilot execution.

In progress:

- isolated generic and configured sub-agents are producing the 10-case Batch 1
  diagnostic outputs;
- code-workload public/private fixture integrity core.

Locked limitations:

- Batch 1 has already been examined and is instrumentation/selection only;
- the collaboration runtime does not expose auditable provider token/cost
  telemetry;
- collaboration sub-agents share the host filesystem, so this pilot cannot
  prove hard isolation;
- no efficacy or market percentage may be claimed from this pilot.

Next:

1. validate both raw pilot outputs;
2. generate blinded answers and keep the mapping outside evaluator inputs;
3. run blind diagnostic scoring;
4. publish an instrumentation report;
5. repair the harness before creating untouched search confirmation tasks.

## 2026-07-31 — Autonomous execution checkpoint 2

Search Batch 1 instrumentation completed:

- 10 matched vault-only tasks, 20 agent outputs;
- both arms passed strict task order, access-budget, recorded-read, corpus-path,
  and exact-excerpt validation;
- answers were anonymized and scored by two independent blind evaluators;
- evaluator 1: generic 84.6, configured Candidate 1 76.5;
- evaluator 2: generic 87.2, configured Candidate 1 80.6;
- paired configured-minus-generic means: -8.1 and -6.6 points;
- evaluator pair-preference agreement: 90%; critical-failure agreement: 100%.

Candidate 1 is rejected for search selection. It reduced mean note reads from
4.2 to 2.5 but did not protect evidence coverage or explicitly bound missing
support. That is an efficiency/quality trade in the wrong direction, not a
platform win. Candidate 2 now makes evidence coverage a hard stopping
condition and is being tested on the same selection-only batch.

Transfer infrastructure completed:

- sealed public/private package integrity and canary detection;
- five distinct code-development pilot tasks with evaluator-only tests;
- persistent manual-agent boundaries, matched workspace hashes, protected-root
  checks, post-agent evaluation, and nullable provider telemetry;
- five distinct code-review pilot fixtures with severity-weighted defect
  inventories and false-positive scoring;
- code-testing fixtures in progress.

The search results remain diagnostic: the tasks were seen during design, model
identity/token/cost telemetry is unavailable, and collaboration agents share
the host filesystem. No efficacy, market, or financial uplift is claimed.

Candidate 2 selection result:

- evaluator 1 paired configured-minus-generic mean: +6.0 points (8/0/2);
- evaluator 2 paired configured-minus-generic mean: +4.8 points (9/0/1);
- inter-evaluator pair preference agreement: 90%;
- Candidate 2 used 4.0 searches and 3.2 reads per task versus generic 1.4 and
  4.2; quality protection improved, but search-call efficiency did not.

Candidate 2 is provisionally frozen for search. Formal confirmation remains
gated on an anchored rubric, fixed auditable model identity and usage
telemetry, stronger run isolation, and untouched adequately powered tasks.

Code-development Batch 1 completed:

- 5 matched tasks, 10 arm runs, all runs valid with no canary leakage;
- configured: 5/5 tasks passed all evaluator-only checks;
- generic: 4/5 tasks passed all evaluator-only checks;
- paired outcomes: four both-pass, one configured-only pass;
- the differentiating task was CSV parsing: both agents adopted the standard
  parser, but only the configured test critic checked a whitespace-only blank
  record and passed the private boundary test.

This is an encouraging transfer diagnostic, not a 20-point efficacy claim.
Five tasks provide no reliable generalization estimate, provider cost/token
telemetry is missing, and recorded duration includes orchestration queue time.

Code-review Batch 1 completed:

- an initial scorer defect treated a valid category synonym as a false
  positive; it was repaired, regression-tested, logged, and P001 was rerun;
- three of five task pairs were valid;
- on all three valid pairs, both arms achieved severity-weighted recall 1.0,
  precision 1.0, and zero false positives;
- after the schema repair/rerun, generic produced 5/5 valid outputs with one
  false positive overall; configured produced two schema-invalid outputs and
  zero false positives on its three valid runs;
- configured therefore showed no review-quality gain and worse output-contract
  reliability.

Current selection decision: retain the generic reviewer for code review.
Do not force the configured risk/critic controller merely because it is more
structured.

Search confirmation preparation also reached 32 frozen tasks with task-set
SHA-256 `CB4A5012A274A82A3ACE8B232C34997D61B474C59CA6C6A350F620C264862F70`.
Formal execution remains blocked by the unchecked readiness gates in
`confirmation/PREREGISTRATION_DRAFT.md`.

Code-testing Batch 1 completed:

- 5 matched tasks, 10 valid runs;
- no implementation-coupled or unstable candidate suites;
- configured mean distinct faults exposed: 2.8 of 3;
- generic mean distinct faults exposed: 2.6 of 3;
- four task pairs tied; on TST-P004 configured exposed 3/3 faults versus
  generic 2/3;
- both arms used the same eight-test maximum.

The configured risk/budget/critic/stopper controller receives a provisional
selection signal for code testing. The one-fault difference on five seen tasks
does not establish an uplift percentage or economic value.

## 2026-07-31 — Autonomous execution checkpoint 3

Final local validation:

- 118 POC 6c tests passed;
- 2 symlink tests skipped because Windows symlink creation was unavailable;
- frozen confirmation validator passed for all 32 tasks;
- content-addressed manifest written and verified for 356 POC 6c files;
- `git diff --check` passed.

Selection decisions:

- search: reject Candidate 1; provisionally freeze Candidate 2;
- code development: configured selection signal;
- code review: retain generic baseline;
- code testing: configured selection signal.

The product/build verdict remains open. Formal confirmation and transaction
economics cannot be executed honestly in this runtime because fixed model and
evaluator identities, provider token/cost telemetry, deterministic
corpus-only tool enforcement, secret mapping custody, and OS-level isolation
are not available. These are explicit unchecked gates, not values to estimate
or silently waive.

## 2026-08-02 — Completion audit

The independent close-out audit verified:

- all six frozen-input SHA-256 values still match the preregistration draft;
- the confirmation validator still accepts all 32 frozen tasks;
- the regenerated 356-file content-addressed artifact manifest verifies after
  this documentation-only reconciliation;
- roadmap, vision, and benchmark summaries now consistently describe POC 6c
  as diagnostic selection complete and formal confirmation not activated.

The external readiness boundary is unchanged: this workspace does not expose
fixed auditable agent/evaluator identities, provider usage telemetry,
OS-enforced isolation, runtime-enforced corpus-only access, or activated secret
mapping custody. Numeric evaluator calibration must also occur with the fixed
evaluator before activation. The benchmark therefore ends at a reproducible
diagnostic result and confirmation-ready design, not a claimed production
uplift percentage.
