# Task 4B Execution-Agent Handoff

**Status:** implementation incomplete; commit `cac1cac` rejected; Task 5 remains blocked

**Current re-review assignment:** `poc6c/TASK4B_REVIEW_FEEDBACK.md`. That file
records the reproduced failures at `cac1cac`, the required remediation outcomes,
and the exact acceptance evaluations. It supplements this original contract and
controls wherever it is more specific.

**Target branch:** `codex/task4-external-readiness`

**Reviewed starting commit:** `9ceee299fb1eabb6c5e6103a64a0d3fc690e0bd5`

**Authoritative plan:** `poc6c/PLAN.md`, Task 4B

**Readiness record:** `poc6c/confirmation/READINESS_MATRIX.md`

## Execution-agent assignment

Implement and verify Task 4B end to end. Do not stop after writing another plan,
adding placeholder jobs, or making unit tests pass. The required outcome is an
executable synthetic diagnostic pipeline plus a fail-closed production pipeline
whose readiness claims are supported by runtime evidence.

This task is engineering remediation only. It does not authorize a confirmation
run, preregistration activation, real provider calls, secret creation, deblinding,
scoring of untouched confirmation answers, or changes to frozen experimental
inputs.

## Non-negotiable boundaries

- Do not open, generate, execute, score, or deblind untouched confirmation
  material.
- Do not change frozen tasks, prompts, schemas, rubric, thresholds, repeat
  schedule, missing-data rules, or outcome rules.
- Do not add `ANTHROPIC_API_KEY`, a custody seed, or a private key to any local
  file, test fixture, log, artifact, or commit.
- Do not make R01-R05 pass with mocks, requested model IDs, environment-variable
  presence, shared-directory conventions, or self-reported labels.
- Diagnostic artifacts must be tagged `diagnostic_synthetic_only` and must be
  rejected by every production analysis/deblinding path.
- The encrypted arm-label mapping is a custody artifact. The evaluator must
  receive blinded answers and the rubric, never the mapping, seed, private key,
  raw arm labels, or other-arm traces.
- Preserve all unrelated user changes. Regenerate `poc6c/MANIFEST.json` only
  after the final intended file set is stable.

## Required execution sequence

### T4B-01 - Separate diagnostic and production gates

Implementation:

1. Introduce an explicit mode type with only `diagnostic` and `production` as
   valid values; reject missing, ambiguous, or unknown values.
2. Diagnostic mode must traverse all six logical stages using synthetic tasks,
   providers, answers, scores, and test-only custody material without requiring
   live secrets.
3. Production mode must fail before task execution when any required runtime
   evidence is absent, synthetic, test-only, stale, or mismatched.
4. Remove the deadlock in which the first workflow job calls the deliberately
   permanently failing `run_preflight()`.

Expected outcome:

- A diagnostic workflow reaches final integrity successfully and clearly
  reports `confirmation_ready=false`.
- A production invocation with no secrets/evidence exits non-zero before either
  arm runs.

Evaluation:

- Positive integration test covering all diagnostic stages.
- Negative tests for missing mode, unknown mode, diagnostic artifacts in
  production, and production without attestations.

### T4B-02 - Replace central claims with distributed attestations

Implementation:

1. Define a versioned attestation schema containing stage, mode, run ID, commit,
   input artifact hashes, output artifact hashes, runner identity, timestamps,
   relevant provider response identity, and a diagnostic/test-only marker.
2. Make each job attest only facts it can observe. Do not allow one process to
   receive both the API credential and custody seed.
3. Aggregate attestations only in the final integrity job. Verify run-ID,
   commit, mode, upstream/downstream hash, and stage-chain consistency.
4. Make R01-R05 transition from BLOCKED only from validated real evidence; do
   not hardcode them SATISFIED.
5. Return and report every infrastructure check result. Remove the current
   discarded `_provider_result`, `_workflow_result`, `_custody_result`,
   `_blinding_result`, `_pricing_result`, and `_vault_result` pattern.

Expected outcome:

- No single stage can declare the whole run ready.
- Missing, duplicated, reordered, cross-run, or hash-mismatched attestations
  cause final integrity failure.

Evaluation:

- Schema validation tests and chain-validation tests.
- Negative fixtures for stage omission, wrong run ID, wrong commit, hash
  substitution, mode mismatch, and synthetic evidence in production.

### T4B-03 - Implement the blinded artifact data flow

Implementation:

1. Define versioned schemas for task package, arm result, blinded answer bundle,
   evaluator input, evaluator result, custody mapping, and final integrity
   report.
2. Make both arms consume the same task IDs and invariant package, then emit one
   answer and complete telemetry per expected task/repeat.
3. Make the custody stage read both arm-result artifacts, assign randomized blind
   output IDs, produce a blinded-answer bundle, and separately encrypt the
   blind-ID-to-arm mapping.
4. Pass only the blinded-answer bundle and frozen rubric to the evaluator.
5. Make the evaluator emit complete schema-valid scores for every blind output;
   empty scores or `pending_r01_r05` must be fatal in production.
6. Keep raw labeled arm artifacts and the encrypted mapping out of evaluator
   inputs. Keep raw labels out of pre-deblinding analysis.

Expected outcome:

`task package -> two complete arm results -> blinded answers -> complete blinded
scores -> integrity report`, with the encrypted mapping on a separate custody
path.

Evaluation:

- Deterministic synthetic golden-path test.
- Cardinality, duplicate-ID, missing-pair, cross-arm leakage, label-leakage,
  empty-output, and cross-run substitution tests.

### T4B-04 - Enforce least-privilege packages and corpus commitments

Implementation:

1. Stop checking out the complete repository in arm and evaluator jobs. Build
   explicit content-addressed packages upstream and download only each job's
   allow-listed inputs.
2. Disable persisted checkout credentials wherever checkout remains necessary.
3. Launch agent/evaluator code with a genuinely sanitized environment, not just
   step-level comments or selected `env` additions.
4. Implement actual corpus-package acquisition and SHA-256 verification. Reject
   non-hex, wrong-length, missing, or mismatched commitments.
5. Make R08 require all six local frozen hashes plus the actual
   `corpus_manifest` and `indexed_body` commitments. A computed but discarded
   vault check is not evidence.
6. Remove developer-specific default vault paths. Require an explicit path or a
   documented portable resolver.

Expected outcome:

- Each stage can enumerate its permitted inputs, and attempts to access another
  stage's files or secrets fail.
- R08 cannot report SATISFIED until both vault commitments match.

Evaluation:

- Denied-path and denied-environment integration tests.
- Wrong corpus hash, malformed hash, missing package, manifest mismatch, and
  indexed-body mismatch tests.

### T4B-05 - Repair offline deblinding

Implementation:

1. Remove the invalid `dataclasses.fields(...).__class__` construction from
   `_cli_deblind()` and validate bundle schema before construction.
2. Verify ciphertext hash, algorithm allow-list, bundle tags, custodian-key
   fingerprint, and authenticated decryption before returning a mapping.
3. Reject dry-run/test-only bundles through the production CLI and analysis
   entrypoints.
4. Keep deblinding offline and outside all agent/evaluator workflow jobs.

Expected outcome:

- A custodian can deblind an accepted production-format fixture only with the
  matching private key after evaluation artifacts are locked.

Evaluation:

- CLI and library round-trip tests plus wrong-key, corrupt base64, tampered
  ciphertext/tag/metadata, unknown algorithm, and premature-deblind tests.

### T4B-06 - Enforce custody-key compatibility

Implementation:

1. Lock the current design to RSA-4096 with exponent 65537 and RSA-OAEP SHA-256,
   unless a separately specified and reviewed EC hybrid scheme is implemented.
2. Parse and validate public-key type and size during preflight and encryption.
3. Validate that the recorded public-key fingerprint matches the decrypting
   private key.
4. Correct `custodian_public_key.pem` instructions: remove EC-P384 and the stale
   claim that the seed encrypts the mapping.
5. Retain the separation: seed for HMAC assignment only; fresh DEK for AES-GCM;
   RSA public key for DEK wrapping.

Expected outcome:

- Placeholder, malformed, EC, RSA-2048, fingerprint-mismatched, or otherwise
  incompatible keys fail before production execution.

Evaluation:

- Key-type, key-size, fingerprint, placeholder, malformed-PEM, and correct
  RSA-4096 round-trip tests.

### T4B-07 - Make provider telemetry and runtime reproducible

Implementation:

1. Raise `MissingUsage` when input/output token counts, response model, message
   ID, request ID, or other required confirmation telemetry is absent.
2. Reject cache usage when caching is disabled, or explicitly lock and apply
   cache pricing. Never silently undercount cost.
3. Make the pricing lock auditable: replace `NOT_FETCHED_OFFLINE`, resolve the
   introductory-versus-standard rate ambiguity, record retrieval date and source
   digest, and verify the lock at runtime.
4. Lock temperature, timeout, retry, service tier, max-token, and other relevant
   provider behavior; record any provider retry attempts included in a call.
5. Exactly pin Python dependencies with hashes. Quote shell expressions and pin
   GitHub Actions by immutable commit SHA.
6. Parse/lint the workflow and prevent automatic triggers.

Expected outcome:

- Every accepted live call has provider-supplied identity, complete usage, and a
  reproducible cost from a verified pricing record.
- Recreating the diagnostic environment installs the same dependencies/actions.

Evaluation:

- Mocked response-path tests that actually call the adapter for model mismatch,
  missing usage, cache use, missing request/message IDs, and pricing drift.
- Dependency-lock verification, YAML parse, and `actionlint` or equivalent.

### T4B-08 - Add boundary and workflow integration evaluations

The evaluation suite must include all of the following:

1. Unit tests for schemas, provider failure paths, RSA-4096 validation,
   encryption/decryption, and readiness transitions.
2. A local synthetic runner exercising the same stage entrypoints and artifact
   contracts as GitHub Actions.
3. A GitHub diagnostic run proving all six stages execute with no live API key,
   custody seed, private key, or frozen confirmation material.
4. Production-negative tests proving no arm starts when gates are missing and no
   diagnostic artifact reaches production analysis.
5. Isolation tests proving each stage can access only declared files and
   environment variables.
6. Integrity tests proving complete cardinality, hash chaining, run/commit
   consistency, and absence of raw arm labels in evaluator inputs.

Minimum commands/evidence:

```text
python -m pytest poc6c -q
python poc6c/artifact_manifest.py verify --manifest poc6c/MANIFEST.json
git diff --check <accepted-base>..HEAD
actionlint .github/workflows/poc6c-confirmation.yml
```

Record exact counts, skips, tool versions, diagnostic workflow URL, artifact
hashes, and any platform limitations. Do not call the subset that ignores
`poc6c/workloads` the "full suite" unless the exclusion is explicitly stated.

### T4B-09 - Reconcile documentation and obtain independent acceptance

Implementation:

1. Update `PLAN.md`, `PROGRESS.md`, `READINESS_MATRIX.md`, and the preregistration
   checklist so their statuses match executable evidence.
2. Remove stale claims that provider usage fails closed, that R08 verifies both
   vault commitments, or that infrastructure checks are reported when they are
   discarded.
3. Regenerate and verify `MANIFEST.json` after all changes.
4. Request an independent review of the final remediation commit. Resolve every
   P0/P1 finding or document a justified rejection accepted by the owner.
5. Record the accepted commit SHA. Keep Task 5 blocked until R01-R09 have real
   evidence and preregistration is activated prospectively.

Expected outcome:

- Documentation, code, tests, workflow, and recorded gate states agree.
- Independent decision is explicitly `ACCEPTED` or `REJECTED`; passing unit
  tests alone is not acceptance.

## Definition of done

Task 4B is complete only when all statements below are true:

- [ ] Diagnostic mode completes all six stages with synthetic fixtures and no
  live secrets or confirmation material.
- [ ] Production mode fails closed before arm execution without complete real
  attestations.
- [ ] Both arm outputs are complete, blinded, evaluated, and hash-chained in the
  synthetic integration run.
- [ ] Evaluator inputs contain no mapping, seed, private key, raw labels, or
  out-of-scope files.
- [ ] R03 rejects missing or unpriced usage; the pricing lock is auditable.
- [ ] R08 validates local hashes, `corpus_manifest`, and `indexed_body`.
- [ ] RSA-4096 compatibility and offline deblinding pass positive and adversarial
  tests.
- [ ] Dependencies/actions are immutable and the workflow passes static
  validation.
- [ ] The isolated POC6c suite, local synthetic integration suite, manifest
  verification, diff check, and GitHub diagnostic run all pass.
- [ ] No frozen input or preregistered decision rule changed.
- [ ] An independent reviewer accepts the exact remediation commit.

## Required final report from the execution agent

Return one evidence-backed report containing:

1. branch, base SHA, final commit SHA, and remote/PR URL;
2. files changed and why;
3. T4B-01 through T4B-09 status with subtask-level evidence;
4. artifact schemas and stage-by-stage input/output boundaries;
5. test commands, counts, skips, and workflow/static-analysis results;
6. diagnostic run URL and every stage/artifact hash;
7. R01-R09 matrix, clearly separating infrastructure from real runtime evidence;
8. security findings and their resolution;
9. explicit confirmation that no untouched answer was generated, scored, or
   deblinded and no frozen rule changed;
10. remaining human actions, listed only after independent acceptance.

If any required evaluation fails, report `Task 4B INCOMPLETE`, preserve Task 5 as
blocked, and identify the exact failing command, artifact, or attestation. Do not
paper over failures with placeholders or documentation-only status changes.
