# POC 6c workload fixture integrity

This directory contains provider-independent benchmark infrastructure and
small pilot fixtures. Public task packages are separated from evaluator-only
tests, defect inventories, mutations, and leakage canaries. There is no LLM
provider integration.

## Boundary model

Every `FixtureTask` has two packages:

- `public`: the identical repository snapshot copied to both benchmark arms;
- `private`: evaluator-only checks and ground-truth material that an agent must
  never be able to read.

`snapshot_package()` fingerprints relative paths, sizes, and file bytes with a
stable SHA-256 package digest. Symlinks are rejected so a package cannot reach
outside its declared root.

## Required validation

Before a run:

1. call `validate_fixture_task()` for every task;
2. call `validate_split_isolation()` over pilot, selection, and confirmation
   tasks together;
3. after copying a public package into arm workspaces, call
   `validate_matched_public_copies()`.

The checks reject:

- overlapping public/private roots;
- hidden files and public path/content containing `hidden`, `oracle`, or
  `mutant`;
- reused task IDs, task hashes, public hashes, or private hashes;
- missing, extra, or changed files in either arm's public snapshot;
- leakage canaries missing from private material or present in public material.

After a run, call `detect_canary_leakage()` on the answer, patch, trace, and
captured provider payloads. It returns safe canary IDs, never secret token
values. Any match invalidates the run and indicates a fixture or execution
isolation failure.

Run the tests from `poc6c`:

```text
python -m unittest -v workloads.test_fixture_integrity
```

## Code-review pilot harness

`code_review.py` instruments matched generic/configured reviews without
invoking a provider. Both arms receive fresh byte-identical public packages
and the same six-finding JSON budget. The configured prompt's only substantive
difference is its explicit risk scheduling, evidence ledger, critic, and
value-of-information stopping policy.

For a manual or sub-agent run, use `run_code_review.py` in four phases:

```text
python workloads/run_code_review.py prepare --run-root <fresh-run-root> --manifest-output <manifest.json>
python workloads/run_code_review.py begin --run-root <fresh-run-root> --task-id CRV-P001 --arm generic --boundary-output <boundary.json>
# give only the printed workspace and GENERIC_CODE_REVIEW_AGENT.md to the agent
python workloads/run_code_review.py complete --boundary-input <boundary.json> --report-output <report.json>
python workloads/run_code_review.py summarize --reports-root <reports> --report-output <summary.json>
```

The agent must write `REVIEW_FINDINGS.json`; the completion phase strictly
validates it, scans canaries and guarded roots, and only then invokes the
fixture's private `evaluate_review.py`. Reports retain unavailable provider
token/cost values as `null` and are explicitly diagnostic-only.

## Code-testing pilot harness

`code_testing_harness.py` wraps the five sealed code-testing fixtures in the
same matched boundary. Both arms receive a fresh byte-identical public package,
the same tools, at most eight candidate tests, and a three-second per-execution
limit. The configured prompt alone adds risk/value scheduling, a test-budget
allocator, a test critic, and a marginal-value stopper.

The four manual/sub-agent phases are:

```text
python workloads/run_code_testing.py prepare --run-root <fresh-run-root> --manifest-output <manifest.json>
python workloads/run_code_testing.py begin --run-root <fresh-run-root> --task-id TST-P001 --arm generic --boundary-output <boundary.json>
# give only the printed workspace and GENERIC_CODE_TESTING_AGENT.md to the agent
python workloads/run_code_testing.py complete --boundary-input <boundary.json> --report-output <report.json>
python workloads/run_code_testing.py summarize --reports-root <reports> --report-output <summary.json>
```

The agent may create only `test_candidate.py`. Completion audits the fixture
roots, other arm, paired-run files, workspace changes, and leakage canary before
calling private `score_tests.py`. Reports include validity, distinct fault
exposure, source coupling, baseline stability/flakiness, runtime, and nullable
provider usage. They remain diagnostic until a fresh confirmation sample,
provider telemetry, and OS-level isolation are available.
