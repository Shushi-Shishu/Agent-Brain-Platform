# Task 4 — Confirmation Readiness Matrix

**Status date:** 2026-08-04 (third acceptance review: REJECTED)
**Overall Task 4 status: BLOCKED** — Task 4B engineering remediation remains
incomplete at rejected commit `cac1cac`; R01–R05 external evidence is absent.
Task 5 must not start until all nine requirements are SATISFIED.  
All ablation results remain labeled **selection-only**. No confirmation or
product-performance verdict is produced by this work.

The preflight gate in `readiness.py::run_preflight()` enforces this
programmatically: it raises `PreflightFailed` if any requirement is unmet,
preventing any confirmation run from starting.

### External-readiness infrastructure (delivered, audit remediation open)

| Artifact | Purpose | Status |
|---|---|---|
| `poc6c/provider.py` | Anthropic Messages API adapter rejects missing token counts/message ID and cache use, but still accepts a missing provider request ID and does not lock timeout, retries, sampling, tier, or retry telemetry | **PARTIAL — blocks R03** |
| `poc6c/pricing_lock.json` | Versioned pricing record, but source digest remains `NOT_FETCHED_OFFLINE` with `verification_required=true` | **REMEDIATION REQUIRED — blocks R03** |
| `poc6c/blinding.py` | Three-layer cryptographic envelope is present, but production deblinding does not enforce the algorithm allow-list or recorded key fingerprint; tampered metadata can decrypt | **PARTIAL — blocks R05** |
| `poc6c/custodian_public_key.pem` | Placeholder; production requires an offline-generated RSA-4096 public key. EC keys are not compatible with the current RSA-OAEP implementation | **PLACEHOLDER — blocks R05** |
| `.github/workflows/poc6c-confirmation.yml` | Six-job topology and separate credential/custody environment scopes exist, but preflight cannot advance, arm/evaluator steps are placeholders, full-repository checkout violates the declared minimal-input boundary, and blinded-answer data flow is incomplete | **REMEDIATION REQUIRED — blocks R04** |
| `poc6c/test_provider.py` | 42 tests: missing key, model lookup, mismatch, cost, pricing drift, secret redaction, R01–R03 gate checks | **DELIVERED (expanded)** |
| `poc6c/test_blinding.py` | 57 tests: seed, HMAC assignment, AES-GCM+OAEP round-trip, tamper detection, placeholder-key rejection, test-only-bundle rejection, dry-run isolation (frozen-path checks), seed/mapping isolation, evaluator input isolation, cross-arm rejection | **DELIVERED (expanded)** |
| `poc6c/conftest.py` | Excludes generated workload fixture/run payloads from pytest collection, preventing duplicate-basename import collisions without excluding the real workload harness tests | **DELIVERED (`66bd91c`)** |
| `poc6a/experiment.py` (vault path) | Vault path configurable via `PROJECT008_PATH`; 13 pre-existing errors resolved | **FIXED** |

Commit `66bd91c` reports 349 passed, 2 platform skips, and 0 errors for the
complete POC 6c suite after the collection fix. Root-level multi-POC collection
remains unsupported because legacy POCs reuse top-level module names. This is
test-infrastructure evidence only; it does not satisfy or partially satisfy
R01–R05 and closes none of PLAN.md T4B-01 through T4B-09.

### Key audit findings corrected (2026-08-04)

| Finding | Severity | Resolution |
|---|---|---|
| `blinding.py` derived mapping encryption key directly from `CONFIRMATION_BLIND_SEED` via HKDF — seed doubled as custodian decryption secret | **Critical** (Phase 2 req 9) | Replaced with three-layer design: fresh random DEK → AES-256-GCM → RSA-OAEP wrapping. Seed is now used only for HMAC arm assignment |
| Placeholder PEM was accepted by `encrypt_mapping` without failing closed | **High** (Phase 2 req 7) | `_load_public_key` now raises `PlaceholderPublicKey` on the sentinel string; `check_not_placeholder_key()` added to preflight |
| `CONFIRMATION_BLIND_SEED` was available to the same GitHub Actions `confirmation` env as `ANTHROPIC_API_KEY` | **High** (Phase 3) | Seed moved to a separate `confirmation-custody` environment; blinding job uses only that env |
| Dry-run bundles were not tagged and could reach analysis paths | **Medium** (Phase 4) | `dry_run_tag = "diagnostic_synthetic_only"` on all dry-run bundles; `check_not_dry_run_bundle()` rejects them in analysis; `check_not_test_only_bundle()` rejects test-only algorithm bundles |
| Dry-run isolation tests were missing | **Medium** (Phase 4) | Added tests proving `encrypt_mapping(dry_run=True)` never opens `tasks_v1.json`, rubric, or sealed labels |
| Workflow used stdlib HMAC-CTR instead of real AES-GCM | **Medium** (Phase 2) | Now uses `cryptography.hazmat.primitives.ciphers.aead.AESGCM` for real AES-256-GCM |

### Third acceptance review — `cac1cac` rejected (2026-08-04)

| Finding | Severity | Current disposition |
|---|---|---|
| Workflow is placeholder-only and violates least privilege | **P0 — OPEN** | Arm/evaluator outputs remain empty; full checkout remains; workflow does not use stage/artifact/attestation modules; no diagnostic run exists |
| Artifact cardinality, label isolation, and production-mode rejection fail open | **P0 — OPEN** | One arm passes, raw labels in answers pass, and diagnostic artifacts pass production evaluator validation |
| R08 reports satisfied while vault evidence fails | **P0 — OPEN** | `build_requirements_matrix()` still uses only the local hash result; reproduced with vault `passed=False` |
| Attestation order and artifact graph are not enforced | **P1 — OPEN** | Reversed, entirely unlinked attestations validate |
| Deblinding accepts unknown algorithm and fingerprint tampering | **P1 — OPEN** | Fingerprint helper is not invoked and unknown algorithms fall through to RSA unwrap |
| Runtime is not reproducible | **P1 — OPEN** | Missing request ID is accepted; Actions/dependencies float; pricing digest remains a placeholder |
| Manifest and status evidence are inconsistent | **P1 — OPEN** | Clean archive verification fails; PLAN and readiness claims conflict |

The bounded response is `poc6c/TASK4B_REVIEW_FEEDBACK.md`. Its WP1–WP7
outcomes and evaluations must all pass before another acceptance request.

---

## Requirements R01–R09

| ID | Category | Description | Status | Evidence | Owner | Unblock condition | Required for confirmation |
|---|---|---|---|---|---|---|---|
| R01 | Runtime | Auditable configured-agent model ID and version locked by the execution environment | **BLOCKED** | `provider.py::AnthropicProviderAdapter` implements model-ID locking via `response.model` verification and `verify_models_available()` (GET /v1/models preflight). Infrastructure is ready; blocked on ANTHROPIC_API_KEY being supplied to the confirmation run environment. | Infrastructure | Supply `ANTHROPIC_API_KEY` to the GitHub Actions `confirmation` environment and run preflight — `provider.verify_models_available()` will confirm `claude-sonnet-5` is available and lock its ID. | Yes |
| R02 | Runtime | Auditable evaluator model IDs and versions locked by the execution environment for every evaluator call | **BLOCKED** | Same as R01; `provider.py` supports both agent (`claude-sonnet-5`) and evaluator (`claude-opus-5`) model IDs. Infrastructure is ready; blocked on ANTHROPIC_API_KEY. | Infrastructure | Same as R01, applied to `claude-opus-5` evaluator calls. | Yes |
| R03 | Runtime | Provider token count and monetary cost captured for every agent and evaluator call; missing values must not be estimated | **BLOCKED** | Token/message checks and cache rejection exist, but request ID is optional, provider behavior is unlocked, dependencies are not hash-pinned, and pricing source verification remains incomplete. | Engineering + infrastructure | Complete WP6, then collect provider-supplied live evidence. | Yes |
| R04 | Isolation | OS-enforced isolated workspaces preventing cross-arm, mapping, evaluator, and out-of-scope file access | **BLOCKED** | Workflow jobs still checkout the complete repository, inherit unsanitized execution context, emit placeholders, and do not use the implemented stage contracts or attestations. | Engineering + infrastructure | Complete WP1–WP3 and pass the no-secret GitHub diagnostic before creating protected environments. | Yes |
| R05 | Custody | Randomization seed and blind-mapping file locked in a custody location inaccessible to agents and evaluators | **BLOCKED** | RSA-4096 envelope infrastructure exists, but unknown-algorithm and fingerprint-tampered bundles decrypt; the committed public key remains a placeholder. | Engineering + human custodian | Complete WP5 and obtain independent acceptance before generating the real offline keypair or seed. | Yes |
| R06 | Corpus | Deterministic `FrozenCorpus` / `SearchSession` facade is the only vault access path; direct filesystem reads are blocked | **SATISFIED** | `readiness.check_corpus_facade_enforced()` passes on `corpus.py`: `FrozenCorpus` enforces manifest hash on construction; `SearchSession` enforces budget before every search/read; path traversal raises `CorpusError`; no direct `open()` calls bypass the facade. Verified by `test_readiness.py::TestCorpusFacadeRealFile`. | Local | All vault access in `corpus.py` must flow through `FrozenCorpus` and `SearchSession`. | Yes |
| R07 | Rubric | Anchored 100-point rubric dimensions, score bounds, and canonical hash verified using non-confirmation pilot material only | **SATISFIED** | `rubric.validate_rubric()` passes on `confirmation/EVALUATION_RUBRIC_V1.md`: hash matches preregistration (`3B1913AC…`); all 6 dimensions present with correct maxima; all anchor scores valid; `critical_failure` definition present. Total = 100. Calibration scope: non-confirmation pilot material only. Verified by `test_readiness.py::TestValidateRubricRealFile`. | Local | `EVALUATION_RUBRIC_V1.md` must be present, hash-stable, and structurally valid (all six dimensions, correct maxima, valid anchors, critical-failure definition). | Yes |
| R08 | Hashes | All frozen inputs re-hashed and confirmed against `PREREGISTRATION_DRAFT.md` values | **PENDING — AUDIT REOPENED** | Six local artifact hashes pass, but `build_requirements_matrix()` marks R08 satisfied without consuming the failing vault result. Both vault hash functions exist but are not part of the requirement transition. | Engineering + local | Complete WP4: one R08 evidence result must require all six local hashes plus matching `corpus_manifest` and `indexed_body`. | Yes |
| R09 | Process | Preregistration checklist updated to reflect current readiness without changing outcome thresholds or incorporating confirmation outputs | **PENDING — AUDIT REOPENED** | The draft remains unactivated and now records R08/R09 pending, but the rejected implementation, invalid clean-checkout manifest, and absent independent acceptance prevent closure. | Local | Complete WP7 after all engineering remediation: reconcile executable evidence, preserve every frozen decision rule, verify no confirmation output was incorporated, and record acceptance of the exact commit. | Yes |

---

## Summary counts

| Status | Count | IDs |
|---|---|---|
| **SATISFIED** | 2 | R06, R07 |
| **BLOCKED** | 5 | R01, R02, R03, R04, R05 |
| **PENDING** | 2 | R08, R09 |
| **Total** | **9** | R01–R09 |

**Confirmation ready: NO** — Task 5 must not start.

Task 4B engineering remediation is incomplete. The third acceptance review
rejected `cac1cac` with open P0/P1 findings. Engineering WP1–WP7 must be
completed before any protected environment, live credential, custody key, or
seed is created. Passing unit tests alone does not satisfy the workflow,
isolation, custody, clean-checkout, or runtime evidence gates.

---

## Ordered remediation and human actions

### Phase A — engineering remediation before any real secret is created

1. Execute `TASK4B_REVIEW_FEEDBACK.md` together with
   `TASK4B_EXECUTION_HANDOFF.md` and complete every Task 4B item in `PLAN.md`.
2. Prove a fully synthetic diagnostic traversal across all six logical stages.
3. Prove production rejects absent, synthetic, test-only, or mismatched
   attestations and artifacts.
4. Obtain an independent acceptance review and record the accepted commit.

Until Phase A is accepted, do not create the GitHub environments, custody key,
seed, or confirmation outputs.

### R01 + R02 + R03 — Provider credentials and model identity

5. Go to the repository **Settings → Environments** and create an environment
   named exactly `confirmation` with required reviewers (the repository owner).
6. Add `ANTHROPIC_API_KEY` as an environment secret scoped to `confirmation`
   only.
7. Run the non-confirmatory provider-readiness probe and record the provider-
   supplied model identifiers. This probe is distinct from the offline
   synthetic diagnostic.

### R04 — OS isolation

8. Create `confirmation-custody` with a separate reviewer boundary.
9. Run the accepted diagnostic workflow and verify that:
   - generic-arm and configured-arm run on different runner instances,
   - each arm/evaluator receives only its minimal content-addressed package,
   - evaluator job asserts `CONFIRMATION_BLIND_SEED` absent,
   - custody job asserts `ANTHROPIC_API_KEY` absent,
   - no artifact uploads raw vault content.

### R05 — Custody keypair and blinding seed

10. On a separate offline custodian machine and outside every repository,
    generate an RSA-4096 keypair:
   ```
   openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 \
     -out custodian_private.pem
   openssl pkey -pubout -in custodian_private.pem \
     -out custodian_public_key.pem
   ```
11. Store `custodian_private.pem` in a password manager or encrypted offline
    location. Never copy it to a repository, agent host, or GitHub runner.
12. Transfer only `custodian_public_key.pem` into `poc6c/`, verify its
    fingerprint, and commit the public key.
13. Generate the blinding seed on the offline custodian machine:
   ```python
   python -c "import secrets; print(secrets.token_bytes(32).hex().upper())"
   ```
14. Add the seed as `CONFIRMATION_BLIND_SEED` in `confirmation-custody` only.
    Do not save it anywhere accessible to agent or evaluator jobs.

### Activation runbook (after all five unblocked)

When all nine requirements are SATISFIED:

1. Verify the diagnostic gate, each production job attestation, and final
   integrity aggregation under the accepted Task 4B design.
2. Run the full test suite: `python -m pytest poc6c/ --ignore=poc6c/workloads -q`.
   All tests must pass.
3. Verify the content-addressed manifest and accepted workflow commit.
4. Timestamp and countersign `confirmation/PREREGISTRATION_DRAFT.md` — change
   title from "Draft, Not Yet Activated" to "Activated — <ISO timestamp>".
5. Hash the activated preregistration and record it.
6. Trigger the confirmation workflow in production mode.

**No step may be skipped or substituted with a mock.**
