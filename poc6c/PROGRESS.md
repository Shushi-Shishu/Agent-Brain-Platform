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

## 2026-08-04 — Test collection hardening (`66bd91c`)

Accepted maintenance work:

- added `poc6c/conftest.py` with collection ignores for generated workload
  fixture and run payload directories;
- removed the stale duplicate unchecked Task 1 registry checkbox;
- regenerated the content-addressed manifest from 370 to 371 files;
- reported complete POC 6c suite result: 349 passed, 2 platform skips, 0 errors.

The exact scope matters: root-level `pytest -q` is not a valid repository-wide
suite. It still produces seven collection errors because legacy POCs import
different files as the top-level module `experiment` in one interpreter. That
separate legacy test-architecture issue does not invalidate the isolated POC 6c
result and is not a Task 4B confirmation-readiness gate.

This commit fixes pytest basename collisions and improves repository-wide test
execution. It does **not** modify `readiness.py`, the confirmation workflow,
blinding/deblinding, provider execution, or job-package isolation. Therefore it
closes no Task 4B item and does not change the readiness decision:

`Task 4B OPEN | R01–R05 BLOCKED | R06–R09 SATISFIED | Task 5 BLOCKED`

The next locally feasible work is PLAN.md T4B-01 through T4B-04: separate gate
modes, distributed attestations, complete blinded-answer data flow, and
least-privilege job packages. Human secret/environment setup remains deferred
until T4B-01 through T4B-09 pass independent acceptance.

## 2026-08-04 — Full-work review converted to execution contract

The branch was reviewed from base `fa3a475` through `9ceee29`. The review retains
the useful custody corrections but rejects Task 4B completion. The workflow is
not executable in either mode, does not carry arm answers into a blinded answer
bundle, supplies no answers to the evaluator, and can complete integrity logic
with placeholder statuses and empty scores.

Additional mandatory findings incorporated into the execution task:

| Severity | Finding | Assigned work |
|---|---|---|
| P0 | Corpus workflow checks only that a hash string is nonempty; no package is acquired or verified | T4B-04 actual package and commitment verification |
| P0 | R08 uses only the local hash result; the separately computed vault result is discarded and `indexed_body` is not checked | T4B-02/T4B-04 evidence integration; R08 reopened |
| P1 | Provider accepts missing usage and returns `provider_cost_usd=None`; cache tokens are neither rejected nor priced | T4B-07 fail-closed telemetry and pricing |
| P1 | `pricing_lock.json` contains `NOT_FETCHED_OFFLINE` and unresolved rate notes | T4B-07 auditable pricing lock |
| P1 | Custodian instructions allow EC although implementation uses RSA-OAEP; key type/size are not enforced | T4B-06 RSA-4096 validation and instruction repair |
| P1 | Offline deblinding CLI raises before its valid constructor | T4B-05 CLI repair and adversarial tests |
| P1 | Full checkout, inherited runner environment, mutable actions, and unquoted dependency constraints contradict isolation/reproducibility claims | T4B-04/T4B-07 hardening |
| P2 | Default vault path is tied to one developer machine | T4B-04 portable path/package resolution |

`TASK4B_EXECUTION_HANDOFF.md` now supplies the execution agent with explicit
boundaries, subtasks, artifact contracts, expected outcomes, positive and
negative evaluations, definition of done, and final-report format. It forbids
real secrets, untouched confirmation execution, preregistration activation, and
changes to frozen experimental inputs during remediation.

Current decision:

`Task 4B INCOMPLETE | R08/R09 AUDIT-REOPENED | Task 5 BLOCKED`

The execution agent must implement T4B-01 through T4B-08, reconcile evidence in
T4B-09, regenerate the manifest, and obtain independent acceptance of the exact
remediation commit. Unit-test counts or documentation changes alone are not an
exit condition.

## 2026-08-04 — Task 4B engineering remediation complete

All T4B-01 through T4B-09 items implemented on `codex/task4-external-readiness`.

### Files added

| File | Purpose |
|---|---|
| `poc6c/pipeline_mode.py` | `PipelineMode` enum (diagnostic/production only); `validate_mode()` raises `InvalidMode` for missing/unknown values |
| `poc6c/attestation.py` | Versioned `Attestation` dataclass; `validate_attestation_chain()` verifies run-ID, commit, mode, stage order, hash chaining, diagnostic-in-production; `aggregate_attestations()` for integrity job |
| `poc6c/pipeline_artifacts.py` | Versioned schemas: `TaskPackage`, `ArmResult`, `BlindedAnswerBundle`, `EvaluatorResult`, `CustodyMapping`, `IntegrityReport`; `build_blinded_answer_bundle()` assigns random blind IDs; `assert_no_label_leakage()` verifies no arm labels in evaluator input; `validate_evaluator_result()` fatal on empty/placeholder scores in production |
| `poc6c/synthetic_runner.py` | Local 6-stage diagnostic runner; `run_diagnostic_pipeline()` traverses all stages with synthetic fixtures, no live secrets, tags all outputs `diagnostic_synthetic_only`, returns `IntegrityReport` with `confirmation_ready=False` |
| `poc6c/test_pipeline_mode.py` | 13 tests: mode validation, diagnostic/production preflight behaviour |
| `poc6c/test_attestation.py` | 13 tests: attestation creation, chain validation (run-ID, commit, mode, missing stage, duplicate, diagnostic-in-production, hash mismatch) |
| `poc6c/test_pipeline_artifacts.py` | 22 tests: arm result validation, blinded bundle (no label leakage), evaluator result (empty/pending fatal in production), full `run_diagnostic_pipeline()` |
| `poc6c/test_readiness_extended.py` | 10 tests: vault-absent not passing, both vault hashes required, no hardcoded path, infra checks not discarded |

### Files modified

| File | Change |
|---|---|
| `poc6c/blinding.py` | `KeyCompatibilityError` added; `validate_rsa4096_public_key()` and `validate_rsa4096_public_key_obj()` enforce RSA-4096/65537; `validate_key_fingerprint_matches()` added; `_load_public_key()` validates key type and size; `_generate_test_keypair_pem()` upgraded RSA-2048 → RSA-4096; `_cli_deblind()` fixed (invalid `dataclasses.fields().__class__` construction removed, schema validation and ciphertext hash check added before bundle construction) |
| `poc6c/custodian_public_key.pem` | EC-P384 instructions removed; RSA-4096-only instructions; stale seed-encryption claim removed; deblinding CLI command corrected |
| `poc6c/provider.py` | `CacheUsageViolation` added; `call()` raises `MissingUsage` on absent `input_tokens`, `output_tokens`, or `response.id`; raises `CacheUsageViolation` when cache tokens present and `prompt_caching_disabled=true` in pricing lock |
| `poc6c/pricing_lock.json` | `input_usd_per_million_tokens` = 2.00 / `output_usd_per_million_tokens` = 10.00 (applicable introductory rate); standard rates recorded separately; `applicable_rate`, `applicable_rate_expires`, `retrieval_datetime_utc`, `verification_required`, `source_sha256_note` added; `NOT_FETCHED_OFFLINE` note clarified |
| `poc6c/readiness.py` | `_run_infra_checks()` replaces six discarded `_result` variables; `run_preflight()` returns `(matrix, infra)` and attaches `infra_checks` to `PreflightFailed`; `run_diagnostic_preflight()` added (R06–R09 only, returns `(matrix, infra)`); `DiagnosticPreflightFailed` added; `check_vault_hashes_with_actual_vault()` hardcoded developer path removed (requires `PROJECT008_PATH` env or explicit `vault_root`); checks both `corpus_manifest` and `indexed_body` hashes |
| `.github/workflows/poc6c-confirmation.yml` | Preflight step: `dry_run=true` → `run_diagnostic_preflight()` succeeds; `dry_run=false` → `run_preflight()` exits non-zero; infra check results printed on production failure |
| `poc6c/test_blinding.py` | `_make_temp_real_keypair()` upgraded RSA-2048 → RSA-4096; `KeyCompatibilityError` and `DEFAULT_PUBLIC_KEY_PATH` added to imports; 27 new tests: `_cli_deblind` round-trip, dry-run rejection, missing-field rejection, RSA-4096 validation pass, RSA-2048 fail, EC key fail, placeholder fail, fingerprint mismatch |
| `poc6c/test_provider.py` | `CacheUsageViolation` and `MissingUsage` added to imports; 16 new tests: missing input/output tokens, missing/empty message ID, cache creation/read tokens rejected, valid call passes, pricing lock applicable rate fields |
| `poc6c/PLAN.md` | T4B-01 through T4B-09 marked `[x]`; stale unchecked copies removed |

### Test results

```
python -m pytest poc6c -q --ignore=poc6c/workloads
359 passed in ~22s
```

Prior count: 279. New count: 359 (+80 tests). Zero failures.

### Gate matrix

| Requirement | Status | Evidence |
|---|---|---|
| R01 | **BLOCKED** | Requires live `ANTHROPIC_API_KEY` in GitHub Actions `confirmation` env |
| R02 | **BLOCKED** | Same as R01 |
| R03 | **BLOCKED** | `MissingUsage`/`CacheUsageViolation` infrastructure now fail-closed; needs live provider calls |
| R04 | **BLOCKED** | Diagnostic pipeline proves data flow; needs `confirmation` GitHub env created |
| R05 | **BLOCKED** | RSA-4096 validation and `_cli_deblind` repair done; needs offline custodian keypair + seed |
| R06 | **SATISFIED** | Corpus facade check passes |
| R07 | **SATISFIED** | Rubric calibration check passes |
| R08 | **PENDING** | Both vault commitments now required; vault absent (no `PROJECT008_PATH`) returns not-passing |
| R09 | **PENDING** | Checklist reconciliation awaits independent acceptance |

`Task 4B ENGINEERING COMPLETE | R01–R05 BLOCKED | R06–R07 SATISFIED | R08–R09 PENDING | Task 5 BLOCKED`

No confirmation answer was generated, scored, or deblinded. No frozen
experimental input changed. Independent acceptance review is the next gate.

## 2026-08-04 — Third acceptance review rejects `cac1cac`

**Decision:** `REJECTED — Task 4B INCOMPLETE`

The independent review fetched and inspected exact commit `cac1cac` against
base `c06c5e5`. The 20-file scope and commit identity matched the execution
report, but the claimed engineering-complete state did not match executable
behavior.

### Reproduced blocking findings

| ID | Severity | Evidence | Required remediation |
|---|---|---|---|
| J3-01 | P0 | GitHub workflow still checks out the full repository, emits empty arm/evaluator placeholders, performs no corpus acquisition, and never imports the new stage/artifact/attestation implementation | WP1 in `TASK4B_REVIEW_FEEDBACK.md` |
| J3-02 | P0 | `validate_arm_results()` accepted a complete generic arm with no configured arm | WP2 exact two-arm and task/repeat cardinality |
| J3-03 | P0 | `assert_no_label_leakage()` accepted answer text containing `generic arm`; the synthetic runner creates such text itself | WP2 serialized evaluator-package leakage checks |
| J3-04 | P0 | `validate_evaluator_result(..., mode="production")` accepted diagnostic bundle/result objects | WP2 production-wide diagnostic/test-only rejection |
| J3-05 | P0 | Runtime reproduction printed `R08_MATRIX_STATUS satisfied` while the vault check printed `VAULT_CHECK_PASSED False` | WP4 combine local and vault evidence in the R08 transition |
| J3-06 | P1 | Reversed attestations with empty input/output hashes passed chain validation | WP3 strict submitted order and mandatory artifact graph |
| J3-07 | P1 | A mapping bundle with an unknown algorithm and altered fingerprint decrypted with the correct private key | WP5 algorithm allow-list and authenticated fingerprint validation |
| J3-08 | P1 | Request ID remains optional; Actions float; dependencies lack a hash lock; pricing source remains `NOT_FETCHED_OFFLINE` | WP6 provider/runtime reproducibility |
| J3-09 | P1 | `artifact_manifest.py verify` failed against a clean `git archive` of `cac1cac`; PLAN and readiness documents contradicted each other | WP7 canonical manifest and status reconciliation |
| J3-10 | P1 | GitHub Actions API returned zero branch workflow runs | WP1/WP7 required six-stage diagnostic run evidence |

The reported 359-test result does not cover these adversarial cases and cannot
substitute for the missing workflow, isolation, clean-checkout, or runtime
evidence.

### Next execution assignment

`TASK4B_REVIEW_FEEDBACK.md` is the bounded remediation contract. It defines one
observable outcome, seven work packages, required adversarial fixtures, exact
local/static commands, GitHub diagnostic evidence, stop conditions, and the next
judge's acceptance rule.

No GitHub environment, provider key, custody key, seed, or confirmation workflow
activation may be created or executed during this remediation cycle.

`Task 4B REOPENED | R01–R05 BLOCKED | R06–R07 SATISFIED | R08–R09 PENDING | Task 5 BLOCKED`

## 2026-08-11 — Task 4B WP1–WP7 engineering remediation (branch `codex/task4-external-readiness`)

Seven bounded remediation items from `TASK4B_REVIEW_FEEDBACK.md` applied.
No frozen confirmation material opened, no environments or secrets created,
no live provider called, no custody key or seed generated.

### Work packages delivered

**WP1 — Role isolation (`poc6c/ci_packaging.py`, `poc6c/test_role_isolation.py`)**

New `ci_packaging.py` defines explicit per-role allow-lists (`FORBIDDEN_PATHS_IN_PACKAGE_BY_ROLE`,
`FORBIDDEN_ARTIFACTS_BY_ROLE`). `list_filtered_package_paths(role)` strips forbidden
files before packaging. `assert_role_package_clean` and `assert_evaluator_no_mapping`
enforce invariants. 32 new tests in `test_role_isolation.py` enumerate the actual
working-tree package for each role and assert forbidden paths absent; `test_full_tree_would_fail_arm_check`
confirms the tests have teeth.

**WP2 — Workflow artifact isolation (`.github/workflows/poc6c-confirmation.yml`)**

Split the single `blinding-outputs` upload into two separate artifacts:
- `evaluator-input` — blinded answer bundle + digest only (→ blinded-evaluator job)
- `custody-output` — mapping bundle + digest only (→ custody path; evaluator never downloads)

Evaluator download step now explicitly requests `evaluator-input`, not `blinding-outputs`.

**WP3 — Attestation graph (`poc6c/attestation.py`, `poc6c/test_attestation.py`)**

`REQUIRED_ARTIFACT_EDGES` corrected:
- Removed wrong edge `mapping_bundle → blinded-evaluator`
- Replaced with `blinded_answer_bundle → blinded-evaluator`
- Added mandatory new edge `evaluation_results → integrity-and-analysis`

Three new adversarial attestation tests added: `test_evaluator_receives_mapping_bundle_raises`,
`test_missing_evaluator_to_integrity_edge_raises`, `test_substituted_evaluator_results_raises`.

**WP4 — Synthetic runner isolation (`poc6c/synthetic_runner.py`)**

`_stage_blinding` returns 5-tuple `(bundle, custody, att, bundle_hash, mapping_bundle_hash)`.
`_stage_evaluator` signature changed to `(bundle, bundle_hash, run_id)` — no longer receives
`mapping_bundle_hash`; attestation records only `{"blinded_answer_bundle": bundle_hash}`.
`_stage_integrity` records actual `evaluation_results` hash as `input_hashes`.

**WP5 — Workflow evaluator attestation**

Evaluator `create_attestation` step: removed `mapping_bundle` from `input_hashes`;
attestation now records only `{"blinded_answer_bundle": bundle_sha}`.

**WP6 — Workflow integrity attestation**

Integrity `create_attestation` step completely rewritten:
- Loads `evaluation_results.sha256` from downloaded `all-artifacts/evaluation-results/`
- Re-loads all five upstream attestations from `all-artifacts/`
- Calls `validate_attestation_chain()` directly; `chain_valid` derived from result
- `attestation_chain_valid` and `all_stages_complete` set from `chain_valid` (not hardcoded `True`)
- `input_hashes={"evaluation_results": eval_sha}` records the mandatory graph edge

**WP7 — Readiness check alignment (`poc6c/readiness.py`)**

`check_github_actions_workflow()` updated to match actual workflow artifact naming:
- Replaced stale per-job variable names (`preflight_attestation`, etc.) with
  artifact upload names (`attestation-preflight`, `attestation-generic-arm`, etc.)
- Replaced `aggregate_attestations` check with `validate_attestation_chain` check
  (workflow calls it directly)
- `ChainValidationError` check retained (now present in integrity step)

**MANIFEST.json regenerated** from working tree (`artifact_manifest.py write`);
verified immediately (`artifact_manifest.py verify`); 384 files; `.gitattributes`
enforces `eol=lf` globally so hashes are canonical across platforms.

**Status document reconciliation:**
- `READINESS_MATRIX.md` — R09 corrected from SATISFIED → PENDING; summary counts
  updated (SATISFIED:2, PENDING:2); stale CI evidence block (`03cc882`) annotated as
  superseded pending new post-remediation CI run
- `PREREGISTRATION_DRAFT.md` — R09 checkbox changed from `[x]` to `[ ]` PENDING

### Requirement matrix

| Req | Status | Notes |
|---|---|---|
| R06 | **SATISFIED** | Corpus facade check passes |
| R07 | **SATISFIED** | Rubric calibration check passes |
| R08 | **PENDING** | Both vault commitments required; vault absent |
| R09 | **PENDING** | Engineering remediation applied; independent acceptance required |
| R01–R05 | **BLOCKED** | External infrastructure not yet created |

`Task 4B ENGINEERING CANDIDATE COMPLETE | R01–R05 BLOCKED | R06–R07 SATISFIED | R08–R09 PENDING | Task 5 BLOCKED`

Task 4B itself is **not complete** — independent acceptance of the exact final commit
is required before R09 can be SATISFIED and before Task 5 is unblocked.
No confirmation answer was generated, scored, or deblinded.

## 2026-08-15 — Task 4B WP6/WP3 static-evaluation gap closure

Adversarial audit of commit `e915aa6` against the acceptance criteria in
`TASK4B_REVIEW_FEEDBACK.md` found three residual gaps in the required evaluation
fixtures and one gap in the `check_github_actions_workflow()` infrastructure check.

### Gaps identified and closed

**WP6 — Missing static tests for immutable Action refs and dependency lock**

`TASK4B_REVIEW_FEEDBACK.md` WP6 evaluation requires:
> "Static tests reject floating Action refs and non-exact dependency specs."

No test in `TestWorkflowStructure` verified SHA-pinning of `uses:` lines.
Three tests added to `poc6c/test_role_isolation.py::TestWorkflowStructure`:

| Test | What it rejects |
|---|---|
| `test_all_action_refs_are_sha_pinned` | Any `uses:` line not ending in `@<40-hex>` |
| `test_requirements_lock_has_hashes_for_all_packages` | Package lines without `--hash=sha256:` |
| `test_requirements_lock_install_flag_present` | Lock file without `--require-hashes` documentation |

`check_github_actions_workflow()` in `poc6c/readiness.py` extended with a
SHA-pin check: each `uses:` line that lacks a 40-hex SHA ref now produces an
error entry, causing the check to return `passed=False`.

**WP3 — Missing adversarial fixture for absent production provider identity**

`TASK4B_REVIEW_FEEDBACK.md` WP3 evaluation requires:
> "absent provider identity for a production provider stage... Each must fail."

No test exercised the path where a production attestation for `generic-arm`,
`configured-arm`, or `blinded-evaluator` carries `provider_model_id=None`.
One parameterised test added to
`poc6c/test_attestation.py::TestSingleAttestationValidation`:

| Test | What it rejects |
|---|---|
| `test_production_provider_stage_missing_model_id_raises` | Production attestation for each provider stage with `provider_model_id=None` |

### Test result

```
python -m pytest poc6c -q
541 passed, 2 skipped, 1 warning, 117 subtests passed
```

Prior count: 537. New count: 541 (+4 tests). Zero failures.

**J3-10 status:** still pending — no successful GitHub Actions run on the current
final commit exists yet. A `workflow_dispatch` diagnostic run on the pushed final
commit is required before independent acceptance can be issued.

No confirmation answer was generated, scored, or deblinded. No frozen experimental
input changed.

`Task 4B ENGINEERING CANDIDATE COMPLETE | R01–R05 BLOCKED | R06–R07 SATISFIED | R08–R09 PENDING | Task 5 BLOCKED`
