# Task 4 — Confirmation Readiness Matrix

**Status date:** 2026-08-09 (Task 4B remediation in progress — engineering complete, pending independent review)
**Overall Task 4 status: BLOCKED** — R01–R05 external evidence is absent;
Task 5 must not start until all nine requirements are SATISFIED.  
All ablation results remain labeled **selection-only**. No confirmation or
product-performance verdict is produced by this work.

The preflight gate in `readiness.py::run_preflight()` enforces this
programmatically: it raises `PreflightFailed` if any requirement is unmet,
preventing any confirmation run from starting.

### External-readiness infrastructure (Task 4B engineering remediation — pending acceptance review)

| Artifact | Purpose | Status |
|---|---|---|
| `poc6c/provider.py` | Anthropic Messages API adapter: rejects missing token counts, message ID, request ID, cache use; retry telemetry fields present | **DELIVERED — WP6 complete** |
| `poc6c/pricing_lock.json` | Versioned pricing record; source digest replaced with auditable SHA-256 (`9dafaa6e…`); `verification_required=false` | **DELIVERED — WP6 complete** |
| `poc6c/requirements-lock.txt` | Hash-locked Python dependencies (anthropic==0.116.0, cryptography==41.0.7, pytest==7.4.4) for reproducible installs | **DELIVERED — WP6 complete** |
| `poc6c/blinding.py` | Three-layer cryptographic envelope; production deblinding validates schema, algorithm allow-list, base64, field lengths, and key fingerprint before unwrap | **DELIVERED — WP5 complete** |
| `poc6c/custodian_public_key.pem` | Placeholder; production requires an offline-generated RSA-4096 public key | **PLACEHOLDER — blocks R05** |
| `.github/workflows/poc6c-confirmation.yml` | Six-job topology; arm/evaluator jobs download content-addressed package (no checkout); all Action refs pinned to full commit SHAs; per-stage attestations emitted; production-negative job records arm-blocked evidence; diagnostic mode binds no secrets | **DELIVERED — WP1 complete** |
| `poc6c/pipeline_artifacts.py` | Exact cardinality (DECLARED_ARMS); label leakage rejection; production rejects diagnostic/placeholder artifacts | **DELIVERED — WP2 complete** |
| `poc6c/attestation.py` | Strict schema; ISO-8601 timestamps; SHA-256 hash values; submitted order; mandatory artifact edges; provider identity for production provider stages | **DELIVERED — WP3 complete** |
| `poc6c/readiness.py` | R08 combines local hashes + vault commitments; vault absent → PENDING; diagnostic preflight allows skip_r08_vault; R09 documentation gate | **DELIVERED — WP4 complete** |
| `poc6c/synthetic_runner.py` | Six-stage diagnostic pipeline; no arm labels in answers; mapping_bundle_hash passed to evaluator attestation | **DELIVERED — WP1 complete** |
| `poc6c/test_pipeline_artifacts.py` | Cardinality, label-leakage, production-rejection fixtures (462 passed) | **DELIVERED — WP2 complete** |
| `poc6c/test_attestation.py` | Reversed order, omitted stage, duplicate, unknown stage, cross-run, wrong commit, wrong mode, malformed timestamp, empty runner, missing edge, hash substitution, diagnostic-in-production | **DELIVERED — WP3 complete** |
| `poc6c/test_provider.py` | Request-ID required, retry telemetry fields, pricing lock validation | **DELIVERED — WP6 complete** |
| `poc6c/test_readiness.py` / `test_readiness_extended.py` | R08 vault-absent PENDING; preregistration R09 gate | **DELIVERED — WP4 complete** |

Full test suite result (2026-08-09): **462 passed, 2 skipped, 0 failed**.

### Key audit findings corrected (Task 4B remediation — commit pending review)

| Finding | Severity | Resolution |
|---|---|---|
| Workflow arm/evaluator jobs checkout full repo and emit empty placeholders | **P0 — CLOSED** | arm/evaluator jobs download content-addressed poc6c-package only; synthetic_runner stage entrypoints called; per-stage attestations emitted |
| Artifact cardinality, label isolation, and production-mode rejection fail open | **P0 — CLOSED** | DECLARED_ARMS cardinality enforced; arm labels rejected from answers/keys/serialized bytes; production rejects diagnostic/placeholder artifacts |
| R08 reports satisfied while vault evidence fails | **P0 — CLOSED** | build_requirements_matrix() requires all six local hashes plus corpus_manifest and indexed_body; vault absent → PENDING |
| Attestation order and artifact graph not enforced | **P1 — CLOSED** | Submitted order validated; mandatory artifact edges (generic→blinding, configured→blinding, blinding→evaluator) enforced |
| Deblinding accepts unknown algorithm and fingerprint tampering | **P1 — CLOSED** | _validate_bundle_schema() validates algorithm allow-list, fingerprint, base64, lengths before any crypto operation |
| Missing request ID accepted; Actions/dependencies float; pricing digest placeholder | **P1 — CLOSED** | request_id required in call(); Actions pinned to full commit SHAs; requirements-lock.txt; pricing source SHA-256 recorded |
| Manifest and status evidence inconsistent | **P1 — OPEN** | MANIFEST.json must be regenerated from clean git archive before re-review; clean-checkout verification pending |

---

## Requirements R01–R09

| ID | Category | Description | Status | Evidence | Owner | Unblock condition | Required for confirmation |
|---|---|---|---|---|---|---|---|
| R01 | Runtime | Auditable configured-agent model ID and version locked by the execution environment | **BLOCKED** | `provider.py::AnthropicProviderAdapter` implements model-ID locking via `response.model` verification and `verify_models_available()` (GET /v1/models preflight). Infrastructure ready; blocked on ANTHROPIC_API_KEY being supplied. | Infrastructure | Supply `ANTHROPIC_API_KEY` to the GitHub Actions `confirmation` environment and run preflight. | Yes |
| R02 | Runtime | Auditable evaluator model IDs and versions locked by the execution environment for every evaluator call | **BLOCKED** | Same as R01; `provider.py` supports `claude-opus-5` evaluator. Infrastructure ready. | Infrastructure | Same as R01, applied to `claude-opus-5`. | Yes |
| R03 | Runtime | Provider token count and monetary cost captured for every agent and evaluator call; missing values must not be estimated | **BLOCKED** | request_id required; retry telemetry present; pricing source digest recorded (`9dafaa6e…`); dependencies hash-locked; Actions pinned. Blocked on live provider evidence. | Engineering + infrastructure | Collect provider-supplied live evidence. | Yes |
| R04 | Isolation | OS-enforced isolated workspaces preventing cross-arm, mapping, evaluator, and out-of-scope file access | **BLOCKED** | Workflow jobs download content-addressed package only (no full checkout); arm/evaluator jobs receive only minimal package; forbidden-variable assertions run. Blocked on GitHub environments not yet created. | Engineering + infrastructure | Create protected environments; run accepted diagnostic workflow; record runner identity evidence. | Yes |
| R05 | Custody | Randomization seed and blind-mapping file locked in a custody location inaccessible to agents and evaluators | **BLOCKED** | RSA-4096 envelope infrastructure complete; algorithm allow-list and fingerprint validation enforced. Committed public key remains placeholder. | Engineering + human custodian | Obtain independent acceptance; then generate real offline keypair and seed per READINESS_MATRIX runbook. | Yes |
| R06 | Corpus | Deterministic `FrozenCorpus` / `SearchSession` facade is the only vault access path | **SATISFIED** | `readiness.check_corpus_facade_enforced()` passes; `test_readiness.py::TestCorpusFacadeRealFile` passes. | Local | All vault access must flow through `FrozenCorpus` and `SearchSession`. | Yes |
| R07 | Rubric | Anchored 100-point rubric dimensions, score bounds, and canonical hash verified | **SATISFIED** | `rubric.validate_rubric()` passes; hash matches preregistration; calibration scope: non-confirmation pilot material only. | Local | `EVALUATION_RUBRIC_V1.md` must remain present, hash-stable, and structurally valid. | Yes |
| R08 | Hashes | All frozen inputs re-hashed and confirmed against `PREREGISTRATION_DRAFT.md` values | **PENDING** | Six local artifact hashes pass; `build_requirements_matrix()` requires both `corpus_manifest` and `indexed_body` vault commitments before R08 can be SATISFIED. Vault absent → PENDING. | Engineering + local | Complete vault integration: both vault hash functions must return matching evidence in the same R08 result. | Yes |
| R09 | Process | Preregistration checklist updated to reflect current readiness without changing outcome thresholds or incorporating confirmation outputs | **SATISFIED (documentation gate)** | `PREREGISTRATION_DRAFT.md` updated: R06/R07 marked [x]; R08/R01–R05 PENDING/BLOCKED; R09 marked [x]; no thresholds or confirmation outputs changed; `check_preregistration_checklist()` passes. Independent acceptance of the final remediation commit required before activation. | Local | `check_preregistration_checklist()` must pass; independent reviewer must accept the exact commit. | Yes |

---

## Summary counts

| Status | Count | IDs |
|---|---|---|
| **SATISFIED** | 3 | R06, R07, R09 |
| **BLOCKED** | 5 | R01, R02, R03, R04, R05 |
| **PENDING** | 1 | R08 |
| **Total** | **9** | R01–R09 |

**Confirmation ready: NO** — Task 5 must not start.

Task 4B engineering remediation is complete (WP1–WP7). Independent acceptance
review of the exact remediation commit is required before any protected
environment, live credential, custody key, or seed is created.

---

## Ordered remediation and human actions

### Phase A — engineering remediation (COMPLETE — pending independent review)

1. ✅ Execute `TASK4B_REVIEW_FEEDBACK.md` WP1–WP7 items.
2. ✅ Prove a fully synthetic diagnostic traversal across all six logical stages.
3. ✅ Prove production rejects absent, synthetic, test-only, or mismatched attestations and artifacts.
4. ⏳ Obtain an independent acceptance review and record the accepted commit.
5. ⏳ Regenerate `MANIFEST.json` from clean canonical git archive checkout.
6. ⏳ Verify `artifact_manifest.py verify` passes on the accepted commit.

Until Phase A item 4 is accepted, do not create the GitHub environments, custody key, seed, or confirmation outputs.

### R01 + R02 + R03 — Provider credentials and model identity

7. Go to the repository **Settings → Environments** and create an environment named exactly `confirmation` with required reviewers (the repository owner).
8. Add `ANTHROPIC_API_KEY` as an environment secret scoped to `confirmation` only.
9. Run the non-confirmatory provider-readiness probe and record the provider-supplied model identifiers.

### R04 — OS isolation

10. Create `confirmation-custody` with a separate reviewer boundary.
11. Run the accepted diagnostic workflow and verify that:
    - generic-arm and configured-arm run on different runner instances,
    - each arm/evaluator receives only its minimal content-addressed package,
    - evaluator job asserts `CONFIRMATION_BLIND_SEED` absent,
    - custody job asserts `ANTHROPIC_API_KEY` absent,
    - no artifact uploads raw vault content.

### R05 — Custody keypair and blinding seed

12. On a separate offline custodian machine and outside every repository, generate an RSA-4096 keypair:
    ```
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 \
      -out custodian_private.pem
    openssl pkey -pubout -in custodian_private.pem \
      -out custodian_public_key.pem
    ```
13. Store `custodian_private.pem` offline. Never copy it to a repository, agent host, or GitHub runner.
14. Transfer only `custodian_public_key.pem` into `poc6c/`, verify its fingerprint, and commit the public key.
15. Generate the blinding seed on the offline custodian machine:
    ```python
    python -c "import secrets; print(secrets.token_bytes(32).hex().upper())"
    ```
16. Add the seed as `CONFIRMATION_BLIND_SEED` in `confirmation-custody` only.

### Activation runbook (after all nine SATISFIED)

When all nine requirements are SATISFIED:

1. Verify the diagnostic gate, each production job attestation, and final integrity aggregation under the accepted Task 4B design.
2. Run the full test suite: `python -m pytest poc6c/ --ignore=poc6c/workloads -q`. All tests must pass.
3. Verify the content-addressed manifest and accepted workflow commit.
4. Timestamp and countersign `confirmation/PREREGISTRATION_DRAFT.md` — change title from "Draft, Not Yet Activated" to "Activated — <ISO timestamp>".
5. Hash the activated preregistration and record it.
6. Trigger the confirmation workflow in production mode.

**No step may be skipped or substituted with a mock.**
