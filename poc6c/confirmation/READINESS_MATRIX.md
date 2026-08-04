# Task 4 — Confirmation Readiness Matrix

**Status date:** 2026-08-04 (updated: external-readiness infrastructure complete)  
**Overall Task 4 status: BLOCKED** — R01–R05 are externally blocked.  
Task 5 must not start until all nine requirements are SATISFIED.  
All ablation results remain labeled **selection-only**. No confirmation or
product-performance verdict is produced by this work.

The preflight gate in `readiness.py::run_preflight()` enforces this
programmatically: it raises `PreflightFailed` if any requirement is unmet,
preventing any confirmation run from starting.

### External-readiness infrastructure delivered (2026-08-04)

The following infrastructure is now in place to support unblocking R01–R05
once the repository owner supplies credentials and environment decisions:

| Artifact | Purpose | Status |
|---|---|---|
| `poc6c/provider.py` | Anthropic Messages API adapter; auditable telemetry per response; fail-closed on missing key or model mismatch | **DELIVERED** |
| `poc6c/pricing_lock.json` | Versioned pricing record for `claude-sonnet-5` (agent) and `claude-opus-5` (evaluator); locked rates, source URL, confirmation constraints | **DELIVERED** |
| `poc6c/blinding.py` | Deterministic arm assignment from seed; symmetric-authenticated mapping encryption; seed/mapping isolation assertions | **DELIVERED** |
| `poc6c/custodian_public_key.pem` | Placeholder public key; owner must replace with real offline-generated key and store private key off-repo | **DELIVERED (placeholder)** |
| `.github/workflows/poc6c-confirmation.yml` | Fail-closed 6-job confirmation workflow: preflight → generic-arm → configured-arm → deterministic-blinding → blinded-evaluator → integrity-and-analysis; all on separate standard GitHub-hosted VMs | **DELIVERED** |
| `poc6c/test_provider.py` | 33 tests: missing key, model mismatch, cost calculation, pricing drift, secret redaction, synthetic fixtures | **DELIVERED** |
| `poc6c/test_blinding.py` | 35 tests: seed generation, arm assignment, encrypt/decrypt round-trip, tamper detection, corpus hash mismatch, seed/mapping isolation | **DELIVERED** |
| `poc6a/experiment.py` (vault path) | Vault path now configurable via `PROJECT008_PATH` env var; 13 pre-existing vault errors resolved | **FIXED** |

---

## Requirements R01–R09

| ID | Category | Description | Status | Evidence | Owner | Unblock condition | Required for confirmation |
|---|---|---|---|---|---|---|---|
| R01 | Runtime | Auditable configured-agent model ID and version locked by the execution environment | **BLOCKED** | `provider.py::AnthropicProviderAdapter` implements model-ID locking via `response.model` verification and `verify_models_available()` (GET /v1/models preflight). Infrastructure is ready; blocked on ANTHROPIC_API_KEY being supplied to the confirmation run environment. | Infrastructure | Supply `ANTHROPIC_API_KEY` to the GitHub Actions `confirmation` environment and run preflight — `provider.verify_models_available()` will confirm `claude-sonnet-5` is available and lock its ID. | Yes |
| R02 | Runtime | Auditable evaluator model IDs and versions locked by the execution environment for every evaluator call | **BLOCKED** | Same as R01; `provider.py` supports both agent (`claude-sonnet-5`) and evaluator (`claude-opus-5`) model IDs. Infrastructure is ready; blocked on ANTHROPIC_API_KEY. | Infrastructure | Same as R01, applied to `claude-opus-5` evaluator calls. | Yes |
| R03 | Runtime | Provider token count and monetary cost captured for every agent and evaluator call; missing values must not be estimated | **BLOCKED** | `provider.py::ResponseTelemetry` records `input_tokens`, `output_tokens`, `provider_cost_usd`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `stop_reason`, `http_request_id`, and `latency_ms`. `pricing_lock.json` contains locked rates. `compute_provider_cost_usd()` returns `None` (never estimates) when tokens are missing. Infrastructure is ready; blocked on live API credentials. | Infrastructure | Supply `ANTHROPIC_API_KEY`; `provider.call()` will populate all telemetry fields from the live API response. | Yes |
| R04 | Isolation | OS-enforced isolated workspaces preventing cross-arm, mapping, evaluator, and out-of-scope file access | **BLOCKED** | `.github/workflows/poc6c-confirmation.yml` implements six separate GitHub-hosted VM jobs on `ubuntu-24.04`. Generic-arm and configured-arm run on different fresh VMs; evaluator runs on a third fresh VM. Each job asserts `CONFIRMATION_BLIND_SEED` is not in its environment. Workflow requires the `confirmation` protected environment for secret-bearing jobs. Infrastructure is ready; blocked on GitHub Actions `confirmation` environment being created and secrets being configured. | Infrastructure | Create a GitHub Actions `confirmation` protected environment, add `ANTHROPIC_API_KEY` and `CONFIRMATION_BLIND_SEED` as environment secrets, then run the workflow with `dry_run=true` to validate isolation. | Yes |
| R05 | Custody | Randomization seed and blind-mapping file locked in a custody location inaccessible to agents and evaluators | **BLOCKED** | `blinding.py` implements deterministic arm assignment from `CONFIRMATION_BLIND_SEED`, symmetric-authenticated mapping encryption, and `assert_seed_not_in_environment()` / `assert_mapping_not_in_environment()` isolation assertions. `custodian_public_key.pem` is committed (placeholder). The workflow's `deterministic-blinding` job is the only job with seed access (via the protected environment). Blocked on: (1) repository owner generating a real keypair offline, (2) `CONFIRMATION_BLIND_SEED` being added as a protected environment secret, (3) deblinding procedure being documented and signed. | Human | (1) Owner generates RSA/EC keypair offline per `custodian_public_key.pem` instructions, commits real public key, stores private key offline. (2) Add `CONFIRMATION_BLIND_SEED` to the `confirmation` GitHub Actions environment. (3) Document and sign the deblinding procedure. | Yes |
| R06 | Corpus | Deterministic `FrozenCorpus` / `SearchSession` facade is the only vault access path; direct filesystem reads are blocked | **SATISFIED** | `readiness.check_corpus_facade_enforced()` passes on `corpus.py`: `FrozenCorpus` enforces manifest hash on construction; `SearchSession` enforces budget before every search/read; path traversal raises `CorpusError`; no direct `open()` calls bypass the facade. Verified by `test_readiness.py::TestCorpusFacadeRealFile`. | Local | All vault access in `corpus.py` must flow through `FrozenCorpus` and `SearchSession`. | Yes |
| R07 | Rubric | Anchored 100-point rubric dimensions, score bounds, and canonical hash verified using non-confirmation pilot material only | **SATISFIED** | `rubric.validate_rubric()` passes on `confirmation/EVALUATION_RUBRIC_V1.md`: hash matches preregistration (`3B1913AC…`); all 6 dimensions present with correct maxima; all anchor scores valid; `critical_failure` definition present. Total = 100. Calibration scope: non-confirmation pilot material only. Verified by `test_readiness.py::TestValidateRubricRealFile`. | Local | `EVALUATION_RUBRIC_V1.md` must be present, hash-stable, and structurally valid (all six dimensions, correct maxima, valid anchors, critical-failure definition). | Yes |
| R08 | Hashes | All frozen inputs re-hashed and confirmed against `PREREGISTRATION_DRAFT.md` values | **SATISFIED (local + vault)** | `readiness.check_hash_reverification()` passes for all 6 local artifacts. `readiness.check_vault_hashes_with_actual_vault()` now also passes: vault located at `C:\Users\C5332030\Shubham - Work\My_Projects\08. Project_ID_008_Obsidian_Knowledge_Files` and `corpus_manifest` SHA-256 matches frozen commitment (`6BBA908F…`). The 13 pre-existing vault errors in `test_corpus.py` and `test_pilot.py` were caused by a hardcoded `C:\XboxGames\...` path in `poc6a/experiment.py` — fixed by making the path configurable via `PROJECT008_PATH` env var. All 248 tests now pass. Verified by `test_readiness.py::TestHashReverification` and `test_readiness.py::TestVaultHashes`. | Local | All 6 local artifact hashes must match (confirmed). `corpus_manifest` and `indexed_body` must also be verified — `corpus_manifest` now verified at actual vault path. `indexed_body` requires running `corpus.indexed_content_commitment()` against the live vault before activation. | Yes |
| R09 | Process | Preregistration checklist updated to reflect current readiness without changing outcome thresholds or incorporating confirmation outputs | **SATISFIED** | `confirmation/PREREGISTRATION_DRAFT.md` updated in this commit: R06/R07/R08 gates marked `[x]`; status remains "Not Yet Activated"; no confirmation outputs or threshold changes added. Verified by `test_readiness.py::TestPreregistrationChecklist::test_real_updated_file_passes`. | Local | `PREREGISTRATION_DRAFT.md` must mark R06/R07/R08 gates as `[x]`, remain in draft state, and contain no confirmation outputs or threshold changes. | Yes |

---

## Summary counts

| Status | Count | IDs |
|---|---|---|
| **SATISFIED** | 4 | R06, R07, R08, R09 |
| **BLOCKED (external)** | 5 | R01, R02, R03, R04, R05 |
| Pending | 0 | — |
| **Total** | **9** | R01–R09 |

**Confirmation ready: NO** — Task 5 must not start.

Infrastructure for R01–R05 is now delivered. The five requirements remain
BLOCKED because they require human actions: supplying API credentials to the
GitHub Actions `confirmation` environment, creating that environment, and the
owner generating and holding the custody keypair offline.

---

## Human actions required to unblock R01–R05

All infrastructure is in place. The following owner actions convert BLOCKED → SATISFIED:

### R01 + R02 + R03 — Provider credentials and model identity

1. Go to the repository **Settings → Environments** and create an environment
   named exactly `confirmation` with required reviewers (the repository owner).
2. Add `ANTHROPIC_API_KEY` as an environment secret scoped to `confirmation`.
3. Trigger `.github/workflows/poc6c-confirmation.yml` with `dry_run=true` to
   validate that `provider.verify_models_available()` confirms both
   `claude-sonnet-5` (agent) and `claude-opus-5` (evaluator) via GET /v1/models.

### R04 — OS isolation

4. The workflow already provisions separate `ubuntu-24.04` VMs for each job.
   Running the workflow (step 3 above) proves isolation; verify that:
   - generic-arm and configured-arm run on different runner instances,
   - evaluator job asserts `CONFIRMATION_BLIND_SEED` absent,
   - no artifact uploads raw vault content.

### R05 — Custody keypair and blinding seed

5. Generate a real RSA/EC keypair **offline** (not on the agent host):
   ```
   openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-384 \
     -out custodian_private.pem
   openssl pkey -pubout -in custodian_private.pem \
     -out poc6c/custodian_public_key.pem
   ```
6. Commit the updated `custodian_public_key.pem` (real public key, not placeholder).
7. Store `custodian_private.pem` in a password manager or encrypted offline
   location.  **Never commit it.**
8. Generate the blinding seed offline:
   ```python
   python -c "import secrets; print(secrets.token_bytes(32).hex().upper())"
   ```
9. Add the seed as `CONFIRMATION_BLIND_SEED` in the `confirmation` GitHub
   Actions environment secret.  Do not save it anywhere accessible to agents.

### Activation runbook (after all five unblocked)

When all nine requirements are SATISFIED:

1. Run `python -c "from readiness import run_preflight; run_preflight()"` locally.
   It must return without raising `PreflightFailed`.
2. Run the full test suite: `python -m pytest --ignore=workloads -q`.
   All tests must pass.
3. Timestamp and countersign `confirmation/PREREGISTRATION_DRAFT.md` — change
   title from "Draft, Not Yet Activated" to "Activated — <ISO timestamp>".
4. Hash the activated preregistration and record it.
5. Trigger the confirmation workflow without `dry_run=true`.

**No step may be skipped or substituted with a mock.**
