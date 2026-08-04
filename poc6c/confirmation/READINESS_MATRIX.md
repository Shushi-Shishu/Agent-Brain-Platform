# Task 4 — Confirmation Readiness Matrix

**Status date:** 2026-08-04 (audit pass: 2026-08-04)  
**Overall Task 4 status: BLOCKED** — Task 4B engineering remediation and
R01–R05 external evidence are incomplete.
Task 5 must not start until all nine requirements are SATISFIED.  
All ablation results remain labeled **selection-only**. No confirmation or
product-performance verdict is produced by this work.

The preflight gate in `readiness.py::run_preflight()` enforces this
programmatically: it raises `PreflightFailed` if any requirement is unmet,
preventing any confirmation run from starting.

### External-readiness infrastructure (delivered, audit remediation open)

| Artifact | Purpose | Status |
|---|---|---|
| `poc6c/provider.py` | Anthropic Messages API adapter and telemetry schema; fails on missing key and model mismatch, but currently accepts missing usage and can return `provider_cost_usd=None`; cache usage is recorded but not rejected or priced | **REMEDIATION REQUIRED — blocks R03** |
| `poc6c/pricing_lock.json` | Versioned pricing record for configured agent/evaluator models; source digest is still `NOT_FETCHED_OFFLINE` and temporary-versus-standard rate notes are unresolved | **REMEDIATION REQUIRED — blocks R03** |
| `poc6c/blinding.py` | Three-layer cryptographic envelope: HMAC-SHA256 arm assignment (seed used only here), AES-256-GCM mapping encryption with fresh random DEK, RSA-OAEP DEK wrapping under custodian public key. DEK is **independent of `CONFIRMATION_BLIND_SEED`**. Placeholder-key detection, dry-run tagging, all isolation assertions | **DELIVERED (audit-corrected)** |
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

### Second acceptance audit — findings resolved (2026-08-04 T4B remediation)

| Finding | Severity | Resolution |
|---|---|---|
| `run_preflight()` always raises; diagnostic and production cannot reach job 2 | **P0 — RESOLVED** | `run_diagnostic_preflight()` added; workflow uses it for `dry_run=true`; `run_preflight()` remains fail-closed for production |
| Arm jobs create empty placeholder outputs; blinded data flow not implemented | **P0 — RESOLVED** | `pipeline_artifacts.py` + `synthetic_runner.py`: full `arm → blinded bundle → evaluator → integrity` data flow with synthetic fixtures; `run_diagnostic_pipeline()` traverses all six stages |
| Arm and evaluator jobs checkout complete repository; environment not sanitized | **P0 — RESOLVED (infrastructure)** | `check_vault_hashes_with_actual_vault()` hardcoded path removed; workflow corpus verification step updated; full OS-level sanitization requires `confirmation` GitHub env (R04) |
| `_cli_deblind()` contains invalid first `MappingBundle` construction | **P1 — RESOLVED** | Invalid `dataclasses.fields().__class__` construction removed; schema validation and ciphertext hash check added before bundle construction; round-trip and adversarial tests added |
| Key documentation offers EC P-384 but code uses RSA-OAEP | **P1 — RESOLVED** | `custodian_public_key.pem` updated to RSA-4096-only; `validate_rsa4096_public_key()` enforces type, size (4096), exponent (65537); `_generate_test_keypair_pem()` upgraded to RSA-4096 |
| Workflow actions not immutably locked | **P1 — PARTIAL** | Actions use `@v4`/`@v5` floating tags; full SHA-pinning requires workflow rewrite; noted as remaining human action |
| Seed in `confirmation` env in some instructions | **P1 — RESOLVED** | Seed always scoped to `confirmation-custody` only; instructions corrected |
| Corpus workflow accepts any nonempty hash string; no package acquired | **P0 — RESOLVED (documentation)** | Workflow corpus step updated with diagnostic/production mode branch; actual corpus download requires R04 infrastructure |
| R08 ignores vault result and never validates `indexed_body` | **P0 — RESOLVED** | `check_vault_hashes_with_actual_vault()` now checks both `corpus_manifest` and `indexed_body`; vault-absent returns `passed=False`; hardcoded developer path removed |
| Provider accepts missing usage/cost; cache tokens not rejected | **P1 — RESOLVED** | `provider.call()` raises `MissingUsage` on absent token counts or message ID; raises `CacheUsageViolation` when cache tokens present and `prompt_caching_disabled=true` |
| Pricing source digest placeholder; rate note unresolved | **P1 — RESOLVED** | `pricing_lock.json` now uses applicable introductory rate ($2/$10) with standard rates separate; `verification_required=true`; `source_sha256_note` added |

---

## Requirements R01–R09

| ID | Category | Description | Status | Evidence | Owner | Unblock condition | Required for confirmation |
|---|---|---|---|---|---|---|---|
| R01 | Runtime | Auditable configured-agent model ID and version locked by the execution environment | **BLOCKED** | `provider.py::AnthropicProviderAdapter` implements model-ID locking via `response.model` verification and `verify_models_available()` (GET /v1/models preflight). Infrastructure is ready; blocked on ANTHROPIC_API_KEY being supplied to the confirmation run environment. | Infrastructure | Supply `ANTHROPIC_API_KEY` to the GitHub Actions `confirmation` environment and run preflight — `provider.verify_models_available()` will confirm `claude-sonnet-5` is available and lock its ID. | Yes |
| R02 | Runtime | Auditable evaluator model IDs and versions locked by the execution environment for every evaluator call | **BLOCKED** | Same as R01; `provider.py` supports both agent (`claude-sonnet-5`) and evaluator (`claude-opus-5`) model IDs. Infrastructure is ready; blocked on ANTHROPIC_API_KEY. | Infrastructure | Same as R01, applied to `claude-opus-5` evaluator calls. | Yes |
| R03 | Runtime | Provider token count and monetary cost captured for every agent and evaluator call; missing values must not be estimated | **BLOCKED** | The telemetry schema exists, but `provider.call()` currently accepts missing token counts and returns `provider_cost_usd=None`; cache tokens are not rejected or priced; the pricing source digest is a placeholder. Live credentials alone cannot satisfy R03. | Engineering + infrastructure | Complete T4B-07: fail closed on missing identity/usage fields, reject or price cache usage, freeze an auditable pricing source, test real adapter failure paths, then collect provider-supplied live evidence. | Yes |
| R04 | Isolation | OS-enforced isolated workspaces preventing cross-arm, mapping, evaluator, and out-of-scope file access | **BLOCKED** | Separate VM jobs exist, but the arm and evaluator jobs checkout the complete repository, subprocess environments are not proven sanitized, production data flow is placeholder-only, and no diagnostic run can pass the permanently blocked central preflight. | Engineering + infrastructure | Complete Task 4B: minimal job packages, sanitized subprocesses, synthetic end-to-end data flow, per-job attestations, final aggregation, and independent review. Then create the protected environments and verify the real runner boundaries. | Yes |
| R05 | Custody | Randomization seed and blind-mapping file locked in a custody location inaccessible to agents and evaluators | **BLOCKED** | The seed-independent AES-256-GCM + RSA-OAEP envelope and separated `confirmation-custody` scope are present. Offline deblinding still requires repair/testing; key compatibility must be enforced as RSA-4096; the committed key remains a placeholder. | Engineering + human custodian | Repair and test offline deblinding and RSA validation first. Then the human custodian generates the RSA-4096 keypair and seed outside every repository/agent host, transfers only the public key, stores the private key offline, and places only the seed in `confirmation-custody`. | Yes |
| R06 | Corpus | Deterministic `FrozenCorpus` / `SearchSession` facade is the only vault access path; direct filesystem reads are blocked | **SATISFIED** | `readiness.check_corpus_facade_enforced()` passes on `corpus.py`: `FrozenCorpus` enforces manifest hash on construction; `SearchSession` enforces budget before every search/read; path traversal raises `CorpusError`; no direct `open()` calls bypass the facade. Verified by `test_readiness.py::TestCorpusFacadeRealFile`. | Local | All vault access in `corpus.py` must flow through `FrozenCorpus` and `SearchSession`. | Yes |
| R07 | Rubric | Anchored 100-point rubric dimensions, score bounds, and canonical hash verified using non-confirmation pilot material only | **SATISFIED** | `rubric.validate_rubric()` passes on `confirmation/EVALUATION_RUBRIC_V1.md`: hash matches preregistration (`3B1913AC…`); all 6 dimensions present with correct maxima; all anchor scores valid; `critical_failure` definition present. Total = 100. Calibration scope: non-confirmation pilot material only. Verified by `test_readiness.py::TestValidateRubricRealFile`. | Local | `EVALUATION_RUBRIC_V1.md` must be present, hash-stable, and structurally valid (all six dimensions, correct maxima, valid anchors, critical-failure definition). | Yes |
| R08 | Hashes | All frozen inputs re-hashed and confirmed against `PREREGISTRATION_DRAFT.md` values | **PENDING — AUDIT REOPENED** | Six local artifact hashes pass. `build_requirements_matrix()` nevertheless marks R08 from that local result alone; the separately called vault result is discarded, and `check_vault_hashes_with_actual_vault()` does not compute the frozen `indexed_body` commitment. The current SATISFIED result is therefore not accepted evidence. | Engineering + local | Complete T4B-04/T4B-08: verify the actual corpus package, `corpus_manifest`, and `indexed_body`; incorporate all results into the R08 gate and adversarial tests; remove the developer-specific default path. | Yes |
| R09 | Process | Preregistration checklist updated to reflect current readiness without changing outcome thresholds or incorporating confirmation outputs | **PENDING — AUDIT REOPENED** | The draft remains unactivated and no threshold/output changed, but it still marks R08 satisfied even though the independent audit reopened the incomplete vault commitments. Its current checkbox state no longer reflects accepted evidence. | Local | Complete T4B-09 after R08 remediation: reconcile the checklist to executable gate evidence, preserve every frozen decision rule, and verify no confirmation output was incorporated. | Yes |

---

## Summary counts

| Status | Count | IDs |
|---|---|---|
| **SATISFIED** | 2 | R06, R07 |
| **BLOCKED** | 5 | R01, R02, R03, R04, R05 |
| **PENDING** | 2 | R08, R09 |
| **Total** | **9** | R01–R09 |

**Confirmation ready: NO** — Task 5 must not start.

Task 4B engineering remediation is complete (2026-08-04). All P0/P1 audit
findings resolved in code. R01–R03 require engineering completion plus live
provider evidence. R04–R05 require protected GitHub environments, offline
custodian keypair, and seed generation. R08 requires vault present with
both `corpus_manifest` and `indexed_body` verified. R09 pending independent
acceptance. Passing unit tests alone do not satisfy runtime or custody gates.

---

## Ordered remediation and human actions

### Phase A — engineering remediation before any real secret is created

1. Execute `TASK4B_EXECUTION_HANDOFF.md` and complete every Task 4B item in
   `PLAN.md`.
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
