# POC 6c — Configured-Agent Comparative Value Benchmark

## Status

Diagnostic instrumentation and configuration selection are complete. Search
Candidate 1 was rejected by two blind diagnostic evaluators; Candidate 2
received the stronger diagnostic signal. The code-development, code-review,
and code-testing pilots are also complete. These are selection results from
seen pilot tasks, not a confirmed product verdict or uplift claim.

The benchmark compares a generic sub-agent with a configured Agent Brain agent
while holding the task, model, tools, data, context, and budget constant.
Search/research was the first wedge, followed by matched code development,
code review, and code testing. A 32-task untouched search confirmation set is
frozen, but formal execution remains gated by the requirements below.

## Current artifacts

- `PLAN.md` — cross-workload design and transaction economics
- `trace.py` — provider-independent run validation, pair matching, blinded IDs,
  and usage summaries
- `test_trace.py` — trace integrity and experimental-isolation tests

- `pilot/CONFIG_SELECTION.md` — search candidate evidence and selection log
- `pilot/results/` — blinded diagnostic and evaluator-agreement artifacts
- `workloads/` — sealed code fixtures and provider-independent run harnesses
- `RESULTS.md` — consolidated diagnostic outcomes and current selection
  decisions
- `confirmation/` — 32-task frozen set, anchored rubric, validators, and draft
  preregistration/readiness gates

## Important limitation

The workspace currently exposes no external LLM API key. The instrumentation
pilot can use isolated sub-agents, but exact provider token and dollar cost
must remain `null` unless supplied by an auditable runtime. Large repeated
confirmation runs require a callable model runtime with usage telemetry.

Missing values are not estimated or silently replaced with character counts.

## Run validation

```powershell
cd poc6c
python -m unittest -v
```

Latest verified state: 118 tests passed, 2 platform symlink tests skipped,
32 confirmation tasks locked, and 356 POC 6c files content-addressed in
`MANIFEST.json`.
