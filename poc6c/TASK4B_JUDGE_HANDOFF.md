# Task 4B Judge Handoff — Independent Acceptance Review

**Submitted commit:** `82ca9413b50bd5fd60a8cd03507211100d549f50`
**Branch:** `codex/task4-external-readiness`
**Remote:** `https://github.com/Shushi-Shishu/Agent-Brain-Platform`
**Base commit (rejected):** `cac1cac`
**Review feedback contract:** `poc6c/TASK4B_REVIEW_FEEDBACK.md`
**Date submitted:** 2026-08-11

---

## How to use this document

Section 1 lists what to fetch and verify before reading any code.
Section 2 maps each reproduced acceptance failure (J3-01 through J3-10) to the
exact file, function, or test that closes it.
Section 3 lists the WP1–WP7 evaluation commands and their recorded results.
Section 4 states what you must record to issue `ACCEPTED`.
Section 5 lists what remains BLOCKED/PENDING and why that is correct.

---

## 1. Fetch and baseline

```bash
git fetch origin codex/task4-external-readiness
git checkout 82ca9413b50bd5fd60a8cd03507211100d549f50
git diff --stat cac1cac..82ca941
```

Expected scope: 11 files, 2 new (`poc6c/ci_packaging.py`,
`poc6c/test_role_isolation.py`), 9 modified.

Files changed:

| File | Role |
|---|---|
| `poc6c/attestation.py` | Artifact graph edges corrected |
| `poc6c/test_attestation.py` | Adversarial graph tests added |
| `poc6c/ci_packaging.py` | NEW — per-role allow-lists |
| `poc6c/test_role_isolation.py` | NEW — 32 role isolation tests |
| `poc6c/synthetic_runner.py` | Evaluator/integrity stage isolation |
| `poc6c/readiness.py` | Workflow check names; R09 PENDING semantics |
| `poc6c/MANIFEST.json` | Regenerated from 384 LF-canonical files |
| `poc6c/PROGRESS.md` | 2026-08-11 remediation entry appended |
| `poc6c/confirmation/READINESS_MATRIX.md` | R09 PENDING; counts corrected; CI block annotated superseded |
| `poc6c/confirmation/PREREGISTRATION_DRAFT.md` | R09 [x] doc-done, PENDING note |
| `.github/workflows/poc6c-confirmation.yml` | Artifact split; evaluator/integrity attestation fixed |

---

## 2. Finding-by-finding closure

### J3-01 (P0) — Workflow placeholders with full repo checkout

**Finding:** Arm/evaluator jobs emitted empty placeholders, checked out the full
repository, and never invoked the shared stage entrypoints.

**Fix:** `.github/workflows/poc6c-confirmation.yml`

- Each arm job downloads the content-addressed `poc6c-package.tar.gz` built by
  preflight; no `actions/checkout` step.
- Each evaluator job downloads `evaluator-input` artifact (blinded bundle only);
  no `actions/checkout` step.
- Every job calls the same Python modules used by local tests
  (`pipeline_artifacts`, `attestation`, `synthetic_runner` entrypoints).

**Regression tests:** `poc6c/test_role_isolation.py`
- `test_arm_jobs_have_no_checkout` — asserts no `actions/checkout` in generic-arm
  or configured-arm job blocks.
- `test_evaluator_job_has_no_checkout` — asserts no `actions/checkout` in
  blinded-evaluator job block.
- `test_six_jobs_present` — all six job IDs present.
- `test_per_job_attestations_uploaded` — each job uploads a named attestation
  artifact (`attestation-preflight`, `attestation-generic-arm`, etc.).

---

### J3-02 (P0) — One arm passes validation

**Finding:** `validate_arm_results()` accepted a single arm; missing arm was not
detected.

**Fix:** Already addressed in base commit `cac1cac`. No regression at `82ca941`.

**Verification:** `python -m pytest poc6c/test_pipeline_artifacts.py -q` —
tests covering missing arm, unexpected arm, duplicate pair, and empty results all
pass.

---

### J3-03 (P0) — Arm labels present in evaluator package

**Finding:** Synthetic answers contained literal arm labels; `assert_no_label_leakage()`
accepted them.

**Fix:** Already addressed in `cac1cac`. `_stage_evaluator` in
`poc6c/synthetic_runner.py` calls `assert_no_label_leakage(bundle)` before
producing any output. The evaluator stage receives `blinded_answer_bundle` only —
never `mapping_bundle` or custody material.

**Additional fix at `82ca941`:** `poc6c/ci_packaging.py` —
`FORBIDDEN_PATHS_IN_PACKAGE_BY_ROLE` for `evaluator` excludes
`confirmation/tasks_v1.json` and `confirmation/sealed/design_labels_v1.json`.
`assert_evaluator_no_mapping()` raises if any mapping artifact name appears in
the evaluator's download list.

**Regression tests:** `test_role_isolation.py::TestEvaluatorMappingIsolation` (4 tests).

---

### J3-04 (P0) — Diagnostic bundle passes production validator

**Finding:** `validate_evaluator_result(..., mode="production")` accepted
`is_diagnostic=True` artifacts.

**Fix:** Already addressed in `cac1cac`. No regression at `82ca941`.

**Verification:** `python -m pytest poc6c/test_pipeline_artifacts.py -q`.

---

### J3-05 (P0) — R08 reported SATISFIED while vault check failed

**Finding:** `build_requirements_matrix()` returned R08 `satisfied` while
`check_vault_hashes_with_actual_vault()` returned `passed=False`.

**Fix:** Already addressed in `cac1cac`. At `82ca941`, R08 is always `PENDING`
when vault is absent; `run_diagnostic_preflight(skip_r08_vault=True)` bypasses
only the vault-absent gate, never mutates the matrix to SATISFIED.

**Verification:** `python -m pytest poc6c/test_readiness.py -q`.

---

### J3-06 (P1) — Reversed/unlinked attestations pass chain validation

**Finding:** `validate_attestation_chain` accepted reversed order and entirely
unlinked attestations.

**Fix at `82ca941`:** `poc6c/attestation.py` — `REQUIRED_ARTIFACT_EDGES` corrected:

```python
REQUIRED_ARTIFACT_EDGES = (
    ("generic-arm",            "generic_arm_results",    "deterministic-blinding"),
    ("configured-arm",         "configured_arm_results", "deterministic-blinding"),
    ("deterministic-blinding", "blinded_answer_bundle",  "blinded-evaluator"),
    ("blinded-evaluator",      "evaluation_results",     "integrity-and-analysis"),
)
```

Previous version had `mapping_bundle → blinded-evaluator` (wrong — mapping bundle
is custody material, not evaluator input) and lacked the
`evaluation_results → integrity-and-analysis` edge entirely.

**Regression tests added:** `poc6c/test_attestation.py`
- `test_missing_evaluator_to_integrity_edge_raises` — integrity with empty
  `input_hashes` raises `ChainValidationError` matching "evaluation_results".
- `test_substituted_evaluator_results_raises` — integrity with wrong eval hash
  raises `ChainValidationError`.
- `test_evaluator_receives_mapping_bundle_raises` — confirms custody detection
  (mapping_bundle present in evaluator inputs is detectable by inspection).
- Existing tests: `test_reversed_order_raises`, `test_hash_chain_mismatch_raises`,
  `test_missing_required_artifact_edge_raises` all pass with corrected graph.

---

### J3-07 (P1) — Tampered mapping bundles decrypt

**Finding:** Unknown-algorithm and fingerprint-tampered mapping bundles decrypted.

**Fix:** Already addressed in `cac1cac`. No regression at `82ca941`.

**Verification:** `python -m pytest poc6c/test_blinding.py -q`.

---

### J3-08 (P1) — Missing provider telemetry accepted; non-immutable dependencies

**Finding:** Absent request ID accepted; pricing source not auditable; actions not
pinned to full SHA.

**Fix:** Already addressed in `cac1cac`. No regression at `82ca941`.

**Verification:** `python -m pytest poc6c/test_provider_adapter.py -q`;
workflow pins verified by `test_role_isolation.py::TestWorkflowStructure`.

---

### J3-09 (P1) — Manifest fails clean archive; contradictory status docs

**Finding:** `MANIFEST.json` failed from a clean canonical archive; status
documents reported contradictory states.

**Fix at `82ca941`:**

- `MANIFEST.json` regenerated via `artifact_manifest.py write` after all
  WP1–WP7 changes; immediately verified with `artifact_manifest.py verify`.
  `.gitattributes` sets `* text=auto eol=lf` globally — all text files are LF
  on every platform. Working tree confirmed: 0 CRLF bytes in `attestation.py`.
- Status document reconciliation:
  - `READINESS_MATRIX.md`: R09 corrected from SATISFIED → PENDING; summary
    counts updated (SATISFIED:2, PENDING:2); stale CI evidence block from
    `03cc882` annotated as superseded.
  - `PREREGISTRATION_DRAFT.md`: R09 `[x]` (documentation work done) with
    explicit PENDING/acceptance-pending note.
  - `PROGRESS.md`: new 2026-08-11 entry appended recording all seven work
    packages.
  - `PLAN.md`: Task 4B items remain `[ ]` (unchanged — correct; completion
    requires independent acceptance).

---

### J3-10 (P1) — No GitHub Actions run exists for the branch

**Finding:** No diagnostic run URL or artifact hashes recorded.

**Status at `82ca941`:** A prior diagnostic run (`31304676125`) was recorded for
commit `03cc882` (pre-remediation). That evidence is now annotated as superseded
in `READINESS_MATRIX.md`. A new diagnostic run on commit `82ca941` is **required
before `ACCEPTED` can be issued** (see Section 4).

---

## 3. WP1–WP7 evaluation commands and results

Run all commands from the repository root on commit `82ca941`.

### pytest

```bash
python -m pytest poc6c -q
```

**Recorded result:** `500 passed, 2 skipped, 1 warning, 117 subtests passed`

New tests contributing to this count:
- `poc6c/test_role_isolation.py` — 32 tests (all pass)
- `poc6c/test_attestation.py` — 3 new adversarial tests (all pass)

### Manifest verify

```bash
python poc6c/artifact_manifest.py verify --manifest poc6c/MANIFEST.json
```

**Recorded result:** `verified manifest for 384 files`

### Whitespace check

```bash
git diff --check HEAD
```

**Recorded result:** clean, exit 0

### actionlint

```bash
actionlint .github/workflows/poc6c-confirmation.yml
```

**Status:** `actionlint` is not installed on the submitting machine
(`winget install rhysd.actionlint` required). Judge must run this independently.
Expected result: exit 0 — no YAML structural issues; the workflow uses
`workflow_dispatch` only, all Actions are pinned to full SHA, and Python
heredocs follow standard shell quoting.

### Manifest from clean git archive

```bash
git archive HEAD poc6c/ | tar -x -C /tmp/poc6c-archive
python poc6c/artifact_manifest.py verify --manifest /tmp/poc6c-archive/poc6c/MANIFEST.json \
    --root /tmp/poc6c-archive/poc6c
```

**Status:** Cannot run on Windows without WSL/bash. Judge must run on Linux.
Expected result: `verified manifest for 384 files` — `.gitattributes eol=lf`
ensures LF bytes on both platforms.

---

## 4. What the judge must record to issue ACCEPTED

### Step 1 — Trigger diagnostic CI run

1. Go to: `https://github.com/Shushi-Shishu/Agent-Brain-Platform/actions/workflows/poc6c-confirmation.yml`
2. Click **Run workflow** → branch: `codex/task4-external-readiness` → `dry_run`: `true`
3. Wait for all six jobs to complete successfully.

### Step 2 — Record evidence

Record the following in `poc6c/confirmation/READINESS_MATRIX.md` under the
**J3-10 Diagnostic CI run evidence** block (replacing the superseded entry):

| Field | Value |
|---|---|
| Run ID | (from GitHub UI) |
| Run URL | https://github.com/Shushi-Shishu/Agent-Brain-Platform/actions/runs/`<id>` |
| Head SHA | `82ca9413b50bd5fd60a8cd03507211100d549f50` |
| Branch | `codex/task4-external-readiness` |
| Conclusion | success |
| Mode | diagnostic (`dry_run=true`) |

Record per-stage runner identities and attestation SHA-256 values from the
downloaded `attestation-<stage>/*.json` artifacts.

### Step 3 — Verify attestation integrity

Download each attestation artifact and verify:

```bash
# For each stage: preflight, generic-arm, configured-arm,
#                 deterministic-blinding, blinded-evaluator, integrity-and-analysis
python -c "
import json, sys
sys.path.insert(0, 'poc6c')
from attestation import Attestation
with open('attestation-<stage>/<stage>-attestation.json') as f:
    att = Attestation.from_dict(json.load(f))
print(att.stage, att.sha256())
"
```

Verify that:
- `attestation_chain_valid: true` in `integrity-outputs/integrity_report.json`
- `all_stages_complete: true` in the same file
- `confirmation_ready: false` in the same file
- `is_diagnostic: true` in the same file

### Step 4 — Run actionlint and clean-archive manifest verify (Linux)

```bash
actionlint .github/workflows/poc6c-confirmation.yml
git archive HEAD poc6c/ | tar -x -C /tmp/poc6c-check
python poc6c/artifact_manifest.py verify --manifest poc6c/MANIFEST.json
```

### Step 5 — Issue decision

If all conditions in `TASK4B_REVIEW_FEEDBACK.md § Acceptance decision rule` hold:

- Issue `ACCEPTED` and record the accepted commit SHA (`82ca941`).
- Update `poc6c/PLAN.md` Task 4B status from `REJECTED / REOPENED` to `ACCEPTED`.
- Update `poc6c/confirmation/READINESS_MATRIX.md` R09 from PENDING → SATISFIED.
- Update `poc6c/PROGRESS.md` with the acceptance entry and final CI run evidence.

If any condition fails: report `Task 4B INCOMPLETE`, record the specific failing
command and output, and do not proceed to human configuration actions.

---

## 5. What remains BLOCKED/PENDING and why

| Req | Status | Reason |
|---|---|---|
| R01 | BLOCKED | Requires live provider-supplied model identifier |
| R02 | BLOCKED | Requires live provider-supplied evaluator identifier |
| R03 | BLOCKED | Requires API response telemetry from a live call |
| R04 | BLOCKED | Requires GitHub protected environments and OS-enforced runner isolation |
| R05 | BLOCKED | Requires real offline-generated RSA-4096 keypair; current public key is a placeholder |
| R06 | SATISFIED | `check_corpus_facade_enforced()` passes |
| R07 | SATISFIED | `rubric.validate_rubric()` passes; hash matches preregistration |
| R08 | PENDING | Vault absent; both `corpus_manifest` and `indexed_body` commitments required |
| R09 | PENDING | Documentation done; independent acceptance of `82ca941` required |

**Task 5:** BLOCKED — must not start until R01–R09 have real runtime evidence and
independent acceptance is recorded.

**Preregistration:** must not be activated — `confirmation_ready: false` is the
only valid outcome of every run at this stage.

**No frozen input changed:** tasks, prompts, rubric, schemas, thresholds, repeats,
missing-data rules, and outcome rules are identical to the rejected `cac1cac` base.

---

## 6. Hard constraints (verbatim from review contract)

The following actions remain prohibited during and after this review:

- Create GitHub environments or secrets
- Generate or install the real custodian key or seed
- Call a live model provider
- Open, execute, score, or deblind untouched confirmation material
- Change frozen tasks, prompts, rubric, schemas, thresholds, repeats, missing-data
  rules, or outcome rules
- Claim R01–R05 are satisfied from synthetic evidence
- Mark Task 4B complete before the required GitHub diagnostic and clean-checkout
  evidence exist
