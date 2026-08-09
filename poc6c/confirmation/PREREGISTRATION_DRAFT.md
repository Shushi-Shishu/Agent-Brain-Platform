# Search Confirmation Preregistration — Draft, Not Yet Activated

This document becomes active only after every readiness gate below is met and
the 32-task confirmation file is frozen and hashed. Until then, all agent runs
are diagnostic or configuration selection.

## Claim

With the model, task, tools, corpus, access mode, and hard budgets held
constant, Search Candidate 2 improves evidence-grounded answer quality over a
strong generic research agent.

## Frozen arms

- Generic prompt SHA-256:
  `119C376068579A7A0C85FF65337B6EEEF51924FFB3207869126D240926379481`
- Configured Candidate 2 prompt SHA-256:
  `C13A0876413128772DAD874C55B0F7E00B2D09E02FB740E487110C042F83F8E2`
- Output schema SHA-256:
  `8B966A5C7CA822A85C09A59C2D9AD46E95E3488EA9E761CD2E0B11D197FED0B3`
- Evaluation rubric SHA-256:
  `3B1913ACFE347B9515D1C9946F47854D77E1F20DD2044B13210425AC54B264F8`
- Project 008 manifest SHA-256:
  `6BBA908F43640349937E94AEC9054E0DB16E9561265057099FBDFFEE8C6A8B3F`
- Indexed body commitment:
  `E7EE682DCE4175752FF38861E49EE5EA6836D7830AE37E1353640638657D084A`
- Confirmation task-set SHA-256:
  `CB4A5012A274A82A3ACE8B232C34997D61B474C59CA6C6A350F620C264862F70`
- Sealed designer-label SHA-256:
  `6B189887C869A4AA2C9F09515CB68AFBB708279E03BB429D03F09876180B75FD`

No prompt, controller, rubric, threshold, or task may change after activation.

## Design

- 32 untouched independent tasks;
- 3 repeat trials per task and arm;
- 192 agent runs;
- vault-only access;
- maximum 4 search queries and 6 indexed note reads per run;
- arm order randomized inside each task/repeat;
- answers anonymized and shuffled before evaluation;
- two fixed-version blind evaluators score each answer independently;
- if evaluator totals differ by more than 15 points, a third fixed-version
  evaluator is invoked and the median total is used;
- repeats and evaluator scores are averaged within task before inference;
- tasks, not runs or evaluator calls, are the independent units.

Selection Batch 1 and all configuration-search artifacts are permanently
excluded.

## Primary route: quality superiority

Primary metric: configured-minus-generic difference in anchored 100-point
quality score.

Candidate 2 passes search confirmation only if all conditions hold:

1. mean paired task difference is at least +5.0 points;
2. task-cluster bootstrap 95% confidence interval lower bound is above 0;
3. task-level paired sign-flip p-value is below 0.05;
4. the median task difference is positive;
5. at least two of three repeat-index mean differences are positive;
6. leave-one-task-out mean direction never becomes negative;
7. configured critical failures do not exceed generic critical failures;
8. total measured model/tool cost is not more than 10% higher, unless a
   separately declared transaction-value model shows a positive lower-bound
   incremental value after the increase.

The absolute +5 threshold is the materiality gate. Relative percentages are
reported descriptively and are suppressed for unstable denominators.

## Secondary metrics

Report without changing the primary verdict:

- each rubric component;
- exact-citation validation failure rate;
- complete/partial/abstain behavior;
- search and note-read calls;
- input/output tokens, tool cost, evaluator cost, and wall time;
- critical failures;
- evaluator disagreement;
- repeat variance and worst task.

No secondary result can rescue a failed primary gate.

## Readiness gates before activation

Gate IDs correspond to R01–R09 in `confirmation/READINESS_MATRIX.md` and
`PLAN.md` Task 4.

**Audit hold (2026-08-04):** Task 4B engineering remediation remains open;
independent review rejected commit `cac1cac`.
The separate-VM skeleton and passing unit tests do not yet establish R04 or
R05. No checkbox below may be completed, and this draft must not be activated,
until the remediation commit has passed independent acceptance review and the
required real per-job evidence has been recorded.

- [x] **R00a** task file contains 32 questions unseen during configuration selection;
- [x] **R00b** task file and all prompts/schemas/rubrics are hashed
  (reverified as R08 below);
- [ ] **R01** fixed agent model ID and version are auditable
  — BLOCKED (Runtime): requires provider-supplied model identifier;
- [ ] **R02** fixed evaluator model IDs and versions are auditable
  — BLOCKED (Runtime): requires provider-supplied evaluator identifier;
- [ ] **R03** provider token and cost usage is captured for every call
  — BLOCKED (Runtime): requires API response telemetry;
- [ ] **R04** isolated run sandboxes prevent either arm from reading the
  other arm, mapping, evaluator, task-development notes, or out-of-scope files
  — BLOCKED (Isolation): requires OS-enforced process/filesystem isolation;
- [x] **R06** deterministic corpus facade is the only vault access path
  — SATISFIED: `readiness.check_corpus_facade_enforced()` passes; see
  `test_readiness.py`;
- [x] **R07** numeric rubric anchors pass a dry-run schema/calibration check
  that does not use confirmation answers
  — SATISFIED: `rubric.validate_rubric()` passes; hash matches preregistration;
  calibration used non-confirmation pilot material only;
- [ ] **R08** task, prompt, schema, rubric, corpus, label, and manifest hashes
  reverified
  — PENDING: all six local artifact hashes match, but the executable R08 gate
  currently ignores the failing vault result; both `corpus_manifest` and
  `indexed_body` must be integrated and match before activation;
- [ ] **R05** randomization seed and blind-mapping custody location are locked
  — BLOCKED (Custody): requires neutral human-held custody location;
- [x] **R09** preregistration checklist updated without changing outcome
  thresholds or incorporating confirmation outputs
  — SATISFIED (documentation gate): checklist reconciled to executable gate
  evidence; R06/R07 marked [x]; R08/R01–R05 PENDING/BLOCKED as warranted;
  no thresholds or confirmation outputs changed; independent acceptance of the
  final remediation commit required before activation;
- [x] no investigator has inspected confirmation outputs.

If any readiness gate is absent, do not label the run confirmation.

## Missing data and invalid runs

- Missing cost/token values remain missing; they are never estimated from
  characters.
- Citation, corpus, mapping, leakage, model-version, or budget violations
  invalidate the affected pair before scoring.
- A task with one invalid arm is excluded as a pair and reported. If more than
  10% of tasks become unusable, the confirmation is invalid and may not be
  replenished after outcomes are seen.
- No optional stopping or threshold changes are allowed.

## Business extrapolation

Only a passed confirmation effect may enter transaction economics. Search is
modeled separately from code development, code review, and code testing.
Report incremental value per transaction, value per 1,000 transactions,
break-even volume, and low/base/high portfolio scenarios. Do not apply the
search percentage to unrelated workloads.
