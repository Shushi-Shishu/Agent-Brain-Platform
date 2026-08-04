# Task 4 — Confirmation Readiness Matrix

**Status date:** 2026-08-04  
**Overall Task 4 status: BLOCKED** — R01–R05 are externally blocked.  
Task 5 must not start until all nine requirements are SATISFIED.  
All ablation results remain labeled **selection-only**. No confirmation or
product-performance verdict is produced by this work.

The preflight gate in `readiness.py::run_preflight()` enforces this
programmatically: it raises `PreflightFailed` if any requirement is unmet,
preventing any confirmation run from starting.

---

## Requirements R01–R09

| ID | Category | Description | Status | Evidence | Owner | Unblock condition | Required for confirmation |
|---|---|---|---|---|---|---|---|
| R01 | Runtime | Auditable configured-agent model ID and version locked by the execution environment | **BLOCKED** | No provider-supplied model identifier available in current runtime | Infrastructure | Execution environment must return a stable, tamper-evident model ID in every API response (e.g. response header or signed metadata). A convention, env-var, or self-reported prompt value does not satisfy this. | Yes |
| R02 | Runtime | Auditable evaluator model IDs and versions locked by the execution environment for every evaluator call | **BLOCKED** | No provider-supplied evaluator model identifier available | Infrastructure | Same as R01, applied to all evaluator calls. Each evaluator invocation must record a provider-supplied model identifier. | Yes |
| R03 | Runtime | Provider token count and monetary cost captured for every agent and evaluator call; missing values must not be estimated | **BLOCKED** | `model_usage` fields are null in all pilot outputs (`controller.py` `model_usage` block) | Infrastructure | Execution environment must return `input_tokens`, `output_tokens`, and `provider_cost_usd` in the API response. The trace schema already has these fields (currently null). Do not estimate from character counts. | Yes |
| R04 | Isolation | OS-enforced isolated workspaces preventing cross-arm, mapping, evaluator, and out-of-scope file access | **BLOCKED** | Collaboration agents share the host filesystem; no process-boundary isolation exists | Infrastructure | Each arm and the evaluator must run in a separate OS process with filesystem access restricted by OS-level permissions (separate user accounts, containers, or chroot jails). A shared-directory convention or promise-based separation does not satisfy this. | Yes |
| R05 | Custody | Randomization seed and blind-mapping file locked in a custody location inaccessible to agents and evaluators | **BLOCKED** | No neutral custody location exists; mapping lives on the same filesystem accessible to all agents | Human | The randomization seed and arm-assignment mapping must be generated and stored by a human custodian (or a sealed environment) before confirmation runs start, in a location no agent or evaluator process can read. The mapping is revealed to the analyst only after all outputs are collected and locked. An env-var or shared-directory convention does not satisfy this. | Yes |
| R06 | Corpus | Deterministic `FrozenCorpus` / `SearchSession` facade is the only vault access path; direct filesystem reads are blocked | **SATISFIED** | `readiness.check_corpus_facade_enforced()` passes on `corpus.py`: `FrozenCorpus` enforces manifest hash on construction; `SearchSession` enforces budget before every search/read; path traversal raises `CorpusError`; no direct `open()` calls bypass the facade. Verified by `test_readiness.py::TestCorpusFacadeRealFile`. | Local | All vault access in `corpus.py` must flow through `FrozenCorpus` and `SearchSession`. | Yes |
| R07 | Rubric | Anchored 100-point rubric dimensions, score bounds, and canonical hash verified using non-confirmation pilot material only | **SATISFIED** | `rubric.validate_rubric()` passes on `confirmation/EVALUATION_RUBRIC_V1.md`: hash matches preregistration (`3B1913AC…`); all 6 dimensions present with correct maxima; all anchor scores valid; `critical_failure` definition present. Total = 100. Calibration scope: non-confirmation pilot material only. Verified by `test_readiness.py::TestValidateRubricRealFile`. | Local | `EVALUATION_RUBRIC_V1.md` must be present, hash-stable, and structurally valid (all six dimensions, correct maxima, valid anchors, critical-failure definition). | Yes |
| R08 | Hashes | All frozen inputs re-hashed and confirmed against `PREREGISTRATION_DRAFT.md` values | **SATISFIED (local artifacts)** | `readiness.check_hash_reverification()` passes for all 6 local artifacts. `corpus_manifest` and `indexed_body` hashes require Project 008 vault on disk for final verification before activation (using `corpus.manifest_content_commitment()` and `corpus.indexed_content_commitment()`). Verified by `test_readiness.py::TestHashReverification`. | Local (vault hashes: Infrastructure) | All 6 local artifact hashes must match. `corpus_manifest` and `indexed_body` must also be verified once Project 008 vault is present. | Yes |
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

---

## Infrastructure decisions required from the user

The following decisions are required before R01–R05 can be unblocked. Each
has a specific technical interface requirement; no documentation claim,
convention, or mock substitutes.

### R01 + R02 — Model identity (Runtime)

**Decision needed:** Choose a provider or runtime that surfaces a stable,
tamper-evident model identifier per API call.

Options include:
- An Anthropic API key with `model` field in request + `model` echoed in
  response (e.g. `claude-sonnet-5-20251001`). The identifier must be logged
  from the actual API response, not the request, to prevent spoofing.
- A versioned endpoint that guarantees the same model for the duration of the
  run (e.g. a pinned deployment).

**Interface:** every agent trace must record `model_id` from the API response.
The `model_usage` block in `controller.py` already has a null `model_id` field
ready for this value.

### R03 — Token and cost telemetry (Runtime)

**Decision needed:** Choose a provider or SDK version that returns
`usage.input_tokens`, `usage.output_tokens`, and cost in the API response.

The Anthropic Messages API returns a `usage` object in every response. With
direct SDK access the values are available as `response.usage.input_tokens`
and `response.usage.output_tokens`. Monetary cost can be derived from the
published per-token pricing once the model ID is locked (R01).

**Interface:** populate the three currently-null fields in `model_usage`
(`input_tokens`, `output_tokens`, `provider_cost_usd`) from the live API
response for every call. Do not estimate or omit.

### R04 — Process isolation (Isolation)

**Decision needed:** Choose an isolation mechanism that provides OS-level
process separation between the two arms and the evaluator.

Minimum viable options:
- Run each arm as a separate OS process with a distinct working directory
  and no shared writable path to the other arm's output files.
- Use Docker containers with separate volume mounts per arm.
- Use separate user accounts with filesystem ACLs on Windows.

**Interface:** before each confirmation run, the run harness must verify that
the configured arm's output directory is unreadable by the generic arm's
process and vice versa.

### R05 — Blind-mapping custody (Custody + Human)

**Decision needed:** Designate a human custodian and a custody procedure for
the randomization seed and arm-assignment mapping.

Minimum viable procedure:
1. Before any confirmation run starts, generate the randomization seed
   offline (not on the agent host).
2. Store the seed and mapping in a location the agent and evaluator processes
   cannot access (e.g. an encrypted file on the analyst's machine, a password
   manager, or a sealed physical envelope).
3. Record the hash of the mapping file before runs start.
4. Reveal the mapping only after all agent outputs are collected, locked, and
   hashed.

**Interface:** the mapping file path must be outside the poc6c working tree
during runs. The sealed designer-label file (`confirmation/sealed/`) is
already in the correct pattern — the arm-assignment mapping must follow the
same model.

---

## Preflight runbook for future activation

When R01–R05 are unblocked, the following sequence activates the preregistration:

1. Verify R01–R05 are satisfied with real infrastructure evidence.
2. Run `python -c "from readiness import run_preflight; run_preflight()"` —
   must return without raising `PreflightFailed`.
3. Run the full test suite: `python -m pytest --ignore=workloads -q`.
   All tests must pass (vault-dependent errors are acceptable only if the
   vault is absent; with the vault present, those must also pass).
4. Re-verify `corpus_manifest` and `indexed_body` hashes using
   `corpus.manifest_content_commitment()` and
   `corpus.indexed_content_commitment()`.
5. Timestamp and countersign `confirmation/PREREGISTRATION_DRAFT.md`,
   changing its title from "Draft, Not Yet Activated" to "Activated —
   \<ISO timestamp\>".
6. Hash the activated preregistration file and record it.
7. Proceed to Task 5.

**No step in this runbook may be skipped or substituted with a mock.**
