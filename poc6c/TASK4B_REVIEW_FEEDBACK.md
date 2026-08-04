# Task 4B Re-review Feedback and Remediation Assignment

**Judge decision:** REJECTED

**Rejected commit:** `cac1cac`

**Accepted base for the next remediation diff:** `cac1cac`

**Target branch:** `codex/task4-external-readiness`

**Task 5:** BLOCKED

## Assignment outcome

Deliver one new commit whose actual GitHub Actions diagnostic run executes the
same versioned stage entrypoints and artifact contracts used by local tests,
without live secrets or confirmation material, and whose production path fails
closed before either arm whenever required real evidence is absent, synthetic,
test-only, stale, malformed, unlinked, or mismatched.

The outcome is not “more tests” or “six jobs exist.” It is an executable,
least-privilege pipeline with evidence that every reproduced acceptance failure
below is rejected. Task 4B remains incomplete until an independent reviewer
accepts the exact remediation commit.

## Scope and boundaries

The remediation agent may change pipeline, workflow, readiness, custody,
provider, tests, dependency locks, manifests, and status documentation needed to
close this review. It must not:

- create GitHub environments or secrets;
- generate or install the real custodian key or seed;
- call a live model provider;
- open, execute, score, or deblind untouched confirmation material;
- change frozen tasks, prompts, rubric, schemas, thresholds, repeats,
  missing-data rules, or outcome rules;
- claim R01–R05 are satisfied from synthetic evidence;
- mark Task 4B complete before the required GitHub diagnostic and clean-checkout
  evidence exist.

## Reproduced acceptance failures

| ID | Severity | Reproduction at `cac1cac` | Required outcome |
|---|---|---|---|
| J3-01 | P0 | Workflow arm/evaluator jobs emit empty placeholders, checkout the full repository, and never invoke `pipeline_artifacts.py`, `synthetic_runner.py`, or `attestation.py` | The checked-in workflow uses real shared stage entrypoints, complete synthetic artifacts, minimal packages, and per-stage attestations |
| J3-02 | P0 | One complete arm with the other absent passes `validate_arm_results()` | Exactly two declared arms and exactly one result per expected task/repeat are required; missing, duplicate, unexpected, or empty results fail |
| J3-03 | P0 | Synthetic answers contain literal arm labels and `assert_no_label_leakage()` accepts them | Evaluator packages contain no raw arm labels in keys, values, metadata, filenames, or serialized bytes |
| J3-04 | P0 | A diagnostic bundle/result passes `validate_evaluator_result(..., mode="production")` | Every production consumer rejects diagnostic or test-only artifacts before analysis |
| J3-05 | P0 | `build_requirements_matrix()` reports R08 `satisfied` while `check_vault_hashes_with_actual_vault()` reports `passed=False` | R08 is PENDING unless all six local hashes plus `corpus_manifest` and `indexed_body` match in the same evaluated evidence set |
| J3-06 | P1 | Reversed, entirely unlinked attestations pass chain validation | Submitted order, schema, stage identity, run/commit/mode, timestamps, runner identity, diagnostic marker, and every required artifact edge are validated |
| J3-07 | P1 | Unknown-algorithm and fingerprint-tampered mapping bundles decrypt | Production deblinding strictly validates schema/base64, algorithm, tags, ciphertext, authenticated metadata, and the private/public key fingerprint relationship |
| J3-08 | P1 | Missing provider request ID is accepted; behavior, dependencies, Actions, and pricing source are not immutable | Complete provider telemetry and behavior locks are enforced; dependencies and Actions are immutable; pricing source evidence is verified |
| J3-09 | P1 | A clean canonical archive fails `MANIFEST.json` verification; documentation simultaneously claims complete and incomplete states | Manifest verifies from a fresh checkout and every status document reports the same rejected/open or accepted state |
| J3-10 | P1 | No GitHub Actions run exists for the branch | A successful six-stage diagnostic run URL and artifact/attestation hashes are recorded before re-review |

## Work packages, outcomes, and evaluations

### WP1 — One executable workflow and stage implementation

Outcome:

- Local and GitHub diagnostic execution call the same importable six stage
  entrypoints.
- Arm and evaluator jobs do not checkout the repository. They download only
  content-addressed packages built upstream.
- Diagnostic jobs do not bind `ANTHROPIC_API_KEY`,
  `CONFIRMATION_BLIND_SEED`, a private key, or frozen confirmation material.
- Production without complete real evidence exits before either arm.
- Corpus acquisition verifies a strict 64-hex SHA-256 against downloaded bytes;
  non-hex, wrong-length, missing, and mismatched values fail.

Evaluation:

1. Static workflow test proves arm/evaluator jobs have no checkout step and no
   forbidden secret binding.
2. `actionlint .github/workflows/poc6c-confirmation.yml` exits zero.
3. Local diagnostic produces all six attestations and complete non-empty
   artifacts using the workflow stage entrypoints.
4. Production-negative invocation proves neither arm entrypoint was called.
5. GitHub `workflow_dispatch` diagnostic completes all six jobs without any
   live secret configured; record run URL and runner identities.

### WP2 — Artifact cardinality, blinding, and production rejection

Outcome:

- The task package declares task IDs and repeat IDs.
- Each of exactly `generic` and `configured` emits one non-empty answer and
  complete telemetry for every declared pair.
- Blind IDs are unique and have a one-to-one custody mapping.
- The evaluator receives only blind IDs, answers, and the frozen rubric.
- Production validators reject `is_diagnostic`,
  `diagnostic_synthetic_only`, test-only algorithms, empty values, placeholders,
  extra/missing IDs, duplicates, and cross-run artifacts.

Evaluation fixtures must include:

- no arms, one arm, unexpected arm, missing pair, duplicate pair, duplicate
  blind ID, empty answer, empty score, extra score, and `pending_r01_r05`;
- arm labels in keys, answer text, nested metadata, filenames, and serialized
  evaluator-package bytes;
- diagnostic bundle, diagnostic evaluator result, and test-only custody bundle
  presented to every production consumer.

Every fixture above must raise a typed fail-closed exception. The positive
fixture must have complete two-arm cardinality and no raw label leakage.

### WP3 — Attestation schema and mandatory graph

Outcome:

- Use one strict versioned schema; reject missing and unknown fields.
- Validate ISO-8601 timestamp, allowed stage, submitted order, run ID, commit,
  mode, runner identity, provider identity where applicable, and diagnostic tag.
- Define the required artifact graph explicitly, including both parallel arm
  outputs entering blinding and evaluator output entering integrity.
- Every edge is mandatory and content hashes are strict SHA-256 values.
- The final integrity stage alone aggregates the chain.

Evaluation fixtures must include reversed order, omitted stage, duplicated stage,
unknown stage, cross-run, wrong commit, wrong mode, malformed timestamp, empty
runner, missing edge, extra edge, hash substitution, diagnostic-in-production,
and absent provider identity for a production provider stage. Each must fail.

### WP4 — R08 and readiness transitions

Outcome:

- One R08 result combines the six local hashes and both vault commitments.
- Vault absent, path absent, either file absent, or either mismatch produces
  `RequirementStatus.PENDING` and makes production preflight fail.
- Diagnostic execution may proceed with R08 pending only through an explicit
  diagnostic policy; it must not mutate the matrix to `SATISFIED`.
- Infrastructure check failures are consumed by readiness decisions, not merely
  attached for display.

Evaluation:

- Assert `build_requirements_matrix()` never returns R08 satisfied when the
  vault check is false.
- Test all combinations of local pass/fail, manifest pass/fail, indexed-body
  pass/fail, and absent vault.
- Prove production stops before arm invocation for every non-passing combination.

### WP5 — Offline deblinding and custody metadata

Outcome:

- Production CLI and library paths accept only the locked
  `AES-256-GCM+RSA-OAEP-SHA256-v1` algorithm.
- Base64 decoding is strict; exact field set, field types, lengths, and SHA-256
  syntax are validated.
- Algorithm, fingerprint, schema version, and security tags are authenticated or
  cryptographically bound to the ciphertext.
- The decrypting private key's public fingerprint must equal the bundle record
  before unwrap.
- `_test_only_unwrap` cannot bypass production algorithm validation.

Evaluation fixtures must include correct round trip, unknown algorithm, altered
fingerprint, invalid base64 characters/padding, missing/extra fields, wrong field
types, altered nonce/tag/wrapped key/ciphertext/hash, wrong key, RSA-2048, EC,
dry-run, test-only, and premature deblind. Only the correct round trip passes.

### WP6 — Provider and runtime reproducibility

Outcome:

- Reject absent response model, message ID, request ID, input/output usage, or
  any locked billable category.
- Reject cache usage while caching is disabled.
- Lock and record temperature, max tokens, timeout, retry policy/attempts,
  service tier, streaming/batch/cache choices, model IDs, and per-call budgets.
- Replace `NOT_FETCHED_OFFLINE` with an auditable pricing-source digest and make
  expiry/verification failure stop production.
- Install Python dependencies from an exact hash-locked file; pin every GitHub
  Action to a full commit SHA.

Evaluation:

- Adapter-path tests exercise every missing identity/usage field, cache tokens,
  retry telemetry, pricing expiry/digest drift, and response-model mismatch.
- Dependency-lock verification and hash-enforced installation pass from a clean
  environment.
- Static tests reject floating Action refs and non-exact dependency specs.

### WP7 — Evidence, manifest, and status reconciliation

Outcome:

- `PLAN.md`, `PROGRESS.md`, `READINESS_MATRIX.md`, preregistration checklist,
  workflow behavior, and test evidence agree.
- `MANIFEST.json` is generated from canonical repository bytes after all changes
  and verifies in the working tree and a fresh detached checkout/archive.
- The final report includes exact base/final SHAs, remote/PR URL, commands,
  dependency/tool versions, counts/skips, stage hashes, artifact hashes,
  diagnostic run URL, and R01–R09 status.

Evaluation commands:

```text
python -m pytest poc6c -q
python poc6c/artifact_manifest.py verify --manifest poc6c/MANIFEST.json
git diff --check cac1cac..HEAD
actionlint .github/workflows/poc6c-confirmation.yml
```

Repeat manifest verification from a clean checkout or `git archive` of `HEAD`.
The GitHub diagnostic is a separate required evaluation; local success does not
substitute for it.

## Acceptance decision rule

The next independent reviewer returns `ACCEPTED` only if all conditions hold:

- J3-01 through J3-10 have code fixes and adversarial regression tests;
- every WP1–WP7 evaluation passes;
- the GitHub diagnostic run and its six stage attestations are inspectable;
- no P0/P1 finding remains open or is relabeled as a human action;
- R01–R05 remain blocked without real runtime/custody evidence;
- R08 remains pending until both real vault commitments pass;
- R09 remains pending until independent acceptance is recorded;
- Task 5 remains blocked and preregistration remains unactivated.

If any condition fails, report `Task 4B INCOMPLETE`, preserve the failed command
or artifact as evidence, and do not proceed to human configuration.
