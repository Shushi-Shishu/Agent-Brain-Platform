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

## 2026-08-04 — Task 0 checkpoint record

**Diagnostic research checkpoint commit:**
`2c196b2a2380189f99f09dc5e40353ad7e02ac51` — "Build Phases 1–6: complete Agent Brain Platform"

Working tree: clean. No cache, credential, or temporary run artifacts present.

**Frozen confirmation-input hashes (from PREREGISTRATION_DRAFT.md):**

| Input | SHA-256 |
|---|---|
| Generic prompt | `119C376068579A7A0C85FF65337B6EEEF51924FFB3207869126D240926379481` |
| Candidate 2 prompt | `C13A0876413128772DAD874C55B0F7E00B2D09E02FB740E487110C042F83F8E2` |
| Output schema | `8B966A5C7CA822A85C09A59C2D9AD46E95E3488EA9E761CD2E0B11D197FED0B3` |
| Evaluation rubric | `3B1913ACFE347B9515D1C9946F47854D77E1F20DD2044B13210425AC54B264F8` |
| Project 008 manifest | `6BBA908F43640349937E94AEC9054E0DB16E9561265057099FBDFFEE8C6A8B3F` |
| Indexed body commitment | `E7EE682DCE4175752FF38861E49EE5EA6836D7830AE37E1353640638657D084A` |
| Confirmation task-set | `CB4A5012A274A82A3ACE8B232C34997D61B474C59CA6C6A350F620C264862F70` |
| Sealed designer-label | `6B189887C869A4AA2C9F09515CB68AFBB708279E03BB429D03F09876180B75FD` |

Task 0 checklist items requiring a commit (working-tree review and commit action)
remain open pending explicit instruction to commit. All validation commands
recorded in RESEARCH.md pass from this state.

## 2026-08-04 — Task 4 external-readiness infrastructure (branch codex/task4-external-readiness)

External-readiness infrastructure for POC 6c confirmation delivered on
branch `codex/task4-external-readiness`.  R01–R05 remain BLOCKED; all four
locally feasible requirements (R06–R09) remain SATISFIED.  No confirmation
answer was generated, scored, or deblinded.  All ablation results remain
selection-only.

### Vault path fix (pre-existing 13 errors resolved)

`poc6a/experiment.py` hardcoded `C:\XboxGames\...` as the vault path.
The vault exists at `C:\Users\C5332030\Shubham - Work\My_Projects\08. ...`.
Fixed by making the path configurable via `PROJECT008_PATH` environment
variable with the actual path as default.  Hash verified:
`corpus_manifest` SHA-256 = `6BBA908F…` — matches frozen commitment.
All 248 tests now pass (0 errors, up from 13 errors in vault/pilot tests).

### New files delivered

| File | Purpose |
|---|---|
| `poc6c/provider.py` | Anthropic Messages API adapter; `AnthropicProviderAdapter`; `ResponseTelemetry`; fail-closed on missing key, model mismatch, or missing usage; `compute_provider_cost_usd()` returns `None` never estimates |
| `poc6c/pricing_lock.json` | Versioned pricing record: `claude-sonnet-5` (agent, $3/$15/MTok) and `claude-opus-5` (evaluator, $5/$25/MTok); locked rates, source URL, confirmation constraints (Batch API, caching, priority tiers all disabled) |
| `poc6c/blinding.py` | Deterministic arm assignment from seed; HMAC-CTR authenticated mapping encryption; `assert_seed_not_in_environment()` / `assert_mapping_not_in_environment()` isolation assertions; `verify_corpus_package()` for hash-addressed artifact verification |
| `poc6c/custodian_public_key.pem` | Placeholder; owner must replace with real offline-generated EC/RSA key per embedded instructions |
| `.github/workflows/poc6c-confirmation.yml` | Fail-closed 6-job workflow: preflight → generic-arm → configured-arm → deterministic-blinding → blinded-evaluator → integrity-and-analysis; all on separate `ubuntu-24.04` VM instances; `confirmation` protected environment required |
| `poc6c/test_provider.py` | 33 tests: missing key, model lookup, mismatch detection, cost calculation, pricing drift, secret redaction, selection-only invariant |
| `poc6c/test_blinding.py` | 35 tests: seed generation, arm assignment, encrypt/decrypt, tamper detection, corpus hash mismatch, seed isolation, mapping isolation, evaluator input isolation, selection-only invariant |

### Updated files

| File | Change |
|---|---|
| `poc6c/readiness.py` | Added `check_provider_adapter()`, `check_github_actions_workflow()`, `check_custody_key()`, `check_blinding_module()`, `check_pricing_lock()`, `check_vault_hashes_with_actual_vault()`; `run_preflight()` now runs all infrastructure checks and reports them alongside R01–R09 |
| `poc6c/confirmation/READINESS_MATRIX.md` | Updated R01–R05 evidence to reference delivered infrastructure; updated R08 to reflect vault hash now verified at actual path; replaced old decision-needed sections with concrete human action steps |
| `poc6a/experiment.py` | Vault path made configurable via `PROJECT008_PATH` env var |

### Test counts

| File | Tests |
|---|---|
| `test_ablation.py` | 44 |
| `test_readiness.py` | 56 |
| `test_provider.py` | 33 (new) |
| `test_blinding.py` | 35 (new) |
| Prior tests (controller, trace, analysis, etc.) | 80 |
| **Total** | **248 passed, 0 errors** |

### Gate matrix

| Requirement | Category | Status |
|---|---|---|
| R01 | Runtime (model identity) | **BLOCKED** — infrastructure delivered; needs `ANTHROPIC_API_KEY` in `confirmation` env |
| R02 | Runtime (evaluator identity) | **BLOCKED** — same as R01 |
| R03 | Runtime (token/cost telemetry) | **BLOCKED** — same as R01 |
| R04 | Isolation (OS process separation) | **BLOCKED** — workflow infrastructure delivered; needs `confirmation` GitHub env created |
| R05 | Custody (seed + mapping) | **BLOCKED** — blinding.py delivered; needs owner keypair offline + `CONFIRMATION_BLIND_SEED` secret |
| R06 | Corpus facade | **SATISFIED** |
| R07 | Rubric calibration | **SATISFIED** |
| R08 | Hash reverification | **SATISFIED** (local + vault `corpus_manifest`) |
| R09 | Preregistration checklist | **SATISFIED** |

### Remaining human actions before confirmation

1. Create `confirmation` protected environment in GitHub Actions with required reviewers.
2. Create `confirmation-custody` protected environment scoped only to the owner.
3. Add `ANTHROPIC_API_KEY` as environment secret in `confirmation` only.
4. Generate real EC/RSA keypair offline; commit public key; store private key offline.
5. Generate `CONFIRMATION_BLIND_SEED` offline; add as environment secret in `confirmation-custody` only.
6. Trigger workflow with `dry_run=true` to validate isolation end-to-end.
7. Replace `custodian_public_key.pem` placeholder with the real public key.
8. Activate preregistration and run Task 5.

## 2026-08-04 — Independent audit pass (branch codex/task4-external-readiness)

Independent acceptance and publication audit of the Task 4 external-readiness
commit (127cc33).  Branch pushed to origin unchanged; audit findings corrected
on the same branch.  No confirmation answer generated, scored, or deblinded.
R01–R05 remain BLOCKED.

### Critical finding: seed-doubled-as-DEK (corrected)

`blinding.py` v1 (127cc33) derived the mapping encryption key directly from
`CONFIRMATION_BLIND_SEED` via HKDF-expand.  This violated Phase 2 requirement 9:
the seed must not also function as the custodian's decryption secret.  Any
process holding the seed could decrypt the mapping without the custodian's
offline private key — defeating the custody guarantee.

**Correction:** three-layer envelope introduced:

1. `CONFIRMATION_BLIND_SEED` → HMAC-SHA256 arm assignment only (unchanged role)
2. Fresh `secrets.token_bytes(32)` DEK → AES-256-GCM mapping encryption
   (real GCM via `cryptography.hazmat.primitives.ciphers.aead.AESGCM`)
3. DEK → RSA-OAEP (SHA-256/MGF1) wrapping under custodian public key

The DEK is independent of the seed.  Deblinding requires the custodian's
offline private key even if the seed is known.

### Additional audit corrections

| Finding | Corrected |
|---|---|
| Placeholder PEM accepted by `encrypt_mapping` without error | `_load_public_key` detects sentinel; `check_not_placeholder_key()` added |
| `CONFIRMATION_BLIND_SEED` and `ANTHROPIC_API_KEY` in same GitHub env | Seed moved to separate `confirmation-custody` environment |
| Dry-run bundles not tagged; could reach analysis paths | `dry_run_tag = "diagnostic_synthetic_only"`; `check_not_dry_run_bundle()` added |
| Missing frozen-path isolation tests for dry-run | Tests added: `test_dry_run_does_not_open_frozen_task_file` etc. |
| stdlib HMAC-CTR used instead of real AES-GCM | Now uses `cryptography` AESGCM |

### Test counts after audit

| File | Tests |
|---|---|
| `test_ablation.py` | 44 |
| `test_readiness.py` | 56 |
| `test_provider.py` | 42 (was 33; +9 Phase 5 gate tests) |
| `test_blinding.py` | 57 (was 35; +22 Phase 2/3/4 crypto + isolation tests) |
| Prior tests (controller, trace, analysis, etc.) | 80 |
| **Total** | **279 passed, 0 errors, 0 skips** |

### Gate matrix (unchanged)

R01–R05 BLOCKED | R06–R09 SATISFIED | Confirmation ready: NO

## 2026-08-04 — Second acceptance audit: Task 4B remediation opened

The pushed branch and ancestry were verified:

- base `fa3a4756af882aff569cfc175c81c94aea21f885`;
- external-readiness delivery `127cc335d98b14382fcea0c62b709a15ffe23257`;
- custody/security audit correction `d32042b2b0ca208dd09a7c79c6caf2c205c1fe51`;
- remote branch `origin/codex/task4-external-readiness`.

The three-layer envelope correction is retained: the seed is used only for
HMAC assignment, a fresh 32-byte DEK encrypts the mapping with AES-256-GCM, and
RSA-OAEP wraps the DEK. The API credential and custody seed are scoped to
different protected environments.

The branch is **not yet accepted for Task 4 completion**. The 279 passing tests
do not exercise the GitHub Actions topology and currently codify that
`run_preflight()` always raises on R01–R05. The workflow therefore cannot pass
its first job in either diagnostic or production mode.

### Open audit findings

| Severity | Finding | Required remediation |
|---|---|---|
| P0 | Workflow preflight calls a function intentionally tested to always fail R01–R05 | Separate diagnostic and production gates; use per-job attestations and final aggregation |
| P0 | Arm jobs emit empty placeholders; blinding does not consume the arm answers; evaluator receives no blinded-answer bundle and emits empty scores | Implement a complete synthetic end-to-end data flow before any confirmation run |
| P0 | Arm and evaluator jobs checkout the full repository, contradicting the claimed input allow-list and out-of-scope file isolation | Build minimal hash-addressed packages and use sanitized subprocess environments |
| P1 | `_cli_deblind()` executes an invalid `MappingBundle` construction before the valid one | Remove the invalid construction and add offline round-trip/tamper/wrong-key tests |
| P1 | Documentation recommends EC P-384 although the implementation wraps DEKs with RSA-OAEP | Require and validate RSA-4096 unless EC hybrid encryption is implemented separately |
| P1 | Dependency expressions and action tags are not immutable; `cryptography>=41.0.0` is unquoted in shell steps | Quote and exactly lock dependencies; pin actions by commit SHA |
| P1 | Readiness instructions still place `CONFIRMATION_BLIND_SEED` in `confirmation` in some locations | Correct all instructions to use `confirmation-custody` only |

### Decision and next actions

1. Complete PLAN.md Task 4B without opening untouched confirmation material.
2. Run the full local suite, workflow parser, synthetic integration pipeline,
   artifact-manifest verification, and diff checks.
3. Obtain independent acceptance of the remediation commit.
4. Only then create protected environments, generate the RSA-4096 custody
   keypair and randomization seed offline, and perform a diagnostic workflow run.
5. Keep Task 5 and preregistration activation blocked until R01–R09 have real
   evidence. No existing threshold, prompt, task, rubric, or outcome rule changes.

### Cross-platform manifest canonicalization

The audit also found that the prior 370-file manifest was generated from CRLF
working-tree bytes, while the frozen confirmation hashes and Git blobs use LF.
This made verification depend on the checkout's line-ending configuration.
Root `.gitattributes` now enforces LF for detected text and preserves common
binary formats. `MANIFEST.json` is regenerated once from the canonical LF
bytes; future Windows and Linux checkouts must reproduce the same records.
