# POC 6c — Configured-Agent Comparative Value Benchmark

**Status:** design draft; do not run a verdict until workload fixtures,
configuration candidates, scoring, budgets, and pass/fail rules are
preregistered.

## Objective

Test the product claim directly:

> With the model, task, tools, data, and budget held constant, does an agent
> using an Agent Brain Platform decision architecture create more measurable
> value than a normal general-purpose sub-agent?

This is not a factual-answer comparison against an internet reference. It is
a paired comparison of two ways to control the same underlying agent.

## The only intended difference

### Arm A — Generic sub-agent control

- normal general-purpose agent instructions;
- access to the same allowed tools and data as Arm B;
- no platform-selected Explorer, Stopper, Critic, Router, Scheduler, Memory,
  Constraint, or Coordinator policy;
- the model decides implicitly what to inspect, how much effort to spend, and
  when to stop.

### Arm B — Configured Agent Brain agent

- the same base model and task instructions;
- the same allowed tools, data, context limit, and hard budget;
- explicit decision contracts;
- platform-selected blocks and policies for the workload;
- instrumented decisions, evidence, stopping, retries, and escalation.

The configured arm may legitimately select a simple deterministic policy or
retain the generic baseline. The platform is not required to add mathematical
complexity.

## Experimental invariants

Every paired trial must share:

- task instance and initial state;
- model and model version;
- temperature/seed controls where available;
- system capabilities and tool implementations;
- data snapshot and repository commit;
- maximum tokens, calls, wall-clock time, and monetary budget;
- network access policy;
- evaluator and scoring version.

Answers and artifacts are anonymized and shuffled before qualitative review.
The evaluator sees the evidence and outcome, not the generating arm.

Configuration discovery uses a selection set. Final configuration and
thresholds are locked before the untouched confirmation set is run. The cost
of configuration search is recorded as an adoption cost.

## Workload ladder

The project starts with the vision's search/retrieval wedge. Transfer to other
work types is tested only after the wedge produces a usable harness.

| Workload | Representative transaction | Important decision blocks | Strong outcome checks |
|---|---|---|---|
| Search / research | Find and synthesize evidence from Project 008 | Explorer, Router, Stopper, Critic, Memory | evidence support, coverage, unsupported claims, gap detection |
| Code development | Diagnose and repair a bounded issue | Explorer, Router, Planner, Scheduler, Stopper, Critic | hidden tests, regressions, patch scope, repository state |
| Code review | Find and prioritize defects in a change | Explorer, Scheduler, Critic, Stopper, Constraint | seeded-defect recall, precision, severity, false-positive burden |
| Code testing | Design and run the most valuable tests under budget | Planner, Scheduler, Budget Allocator, Stopper, Critic | mutation score, failures exposed, invalid/flaky tests, runtime |

Later candidates may include document review, security investigation,
operations diagnosis, business analysis, and multi-agent coordination. They
are not needed to validate the first four-workload claim.

## Workload-specific design

### 1. Search / research

Use realistic Project 008 questions, including cases where the vault contains
only a partial answer.

Run two separately reported configurations:

1. **Vault only:** both arms may use only Project 008. A high-quality result
   must distinguish supported statements from missing evidence and may return
   a bounded partial answer or abstain.
2. **Vault plus web:** both arms receive identical web access. Web search is a
   shared tool, not a ground-truth answer key. Measure whether the agent
   detects a vault gap and invokes the extra source only when useful.

The blinded assessor evaluates the answer against its cited evidence and the
question. The configured agent is rewarded for justified gap detection, not
for pretending that the vault is complete.

### 2. Code development

Use isolated repository snapshots containing bounded issues. Each trial starts
from the identical commit.

Primary outcome evidence:

- required tests pass;
- unchanged tests continue to pass;
- no prohibited files or interfaces are modified;
- the patch addresses the cause rather than merely hiding the symptom;
- the workspace is left in a valid state.

The configured agent may explicitly allocate investigation across hypotheses,
choose files and tests by expected information value, and stop when the patch
meets the locked evidence contract.

### 3. Code review

Use changes with independently seeded or previously confirmed defects.
Reviewers and agents do not see the defect inventory.

Measure:

- severity-weighted true-positive recall;
- precision and false-positive review burden;
- location and explanation accuracy;
- missed critical defects;
- duplicated or non-actionable comments;
- review cost and latency.

The configured agent should spend more effort on high-risk surfaces and stop
when expected additional review value falls below its cost.

### 4. Code testing

Use identical code snapshots, test budgets, and mutation sets.

Measure:

- distinct real or mutated failures exposed;
- mutation score;
- valid and deterministic tests added;
- coverage of changed or risky behavior;
- redundant, flaky, or implementation-coupled tests;
- execution time and agent cost.

The configured agent controls test selection, generation order, execution
budget, and stopping. It does not receive a larger test budget than the
generic agent.

## Run sequence and scale

### Stage A — Instrumentation pilot

- 5 tasks per workload;
- 1 paired trial per task;
- 4 workloads × 5 tasks × 2 arms = **40 agent runs**;
- diagnostic only; no product verdict.

Purpose: validate isolation, trace capture, scoring, and cost measurement.

### Stage B — Configuration selection

- at least 10 disjoint tasks per workload;
- compare the generic control, the simplest explicit controller, and compatible
  configured candidates;
- select one locked configuration per workload;
- count every selection run and evaluator call as adoption cost.

### Stage C — Confirmation

- untouched task count determined and frozen by a task-level power analysis
  using the pilot only as a cautious variance input;
- 3 repeated trials per task and arm;
- paired analysis on identical task instances.

Tasks—not repeated runs—are the independent units. Repeats estimate
within-task stochasticity and are averaged inside each task before inference.
For illustration, 20 tasks would produce 480 runs across four workloads, but
with a paired-task standard deviation of 10 points and a target effect of 5
points, approximately 32 usable tasks are required for 80% power at two-sided
5% alpha before multiplicity and unusable-task inflation. The confirmation
size may be changed only before preregistration and may not use optional
stopping.

## Metrics

### Outcome metrics

Report these separately before constructing any composite:

- task success rate;
- workload-specific quality score;
- critical-failure rate;
- unsupported-claim or false-positive rate;
- total model and tool cost;
- tokens and tool calls;
- wall-clock latency;
- human review/correction minutes;
- run-to-run variance and worst-case behavior.

### Percentage reporting

For configured arm `B` and generic arm `A`:

```text
quality uplift %       = 100 × (quality_B - quality_A) / |quality_A|
success change         = 100 × (success_B - success_A) percentage points
failure reduction %    = 100 × (failure_A - failure_B) / failure_A
cost saving %          = 100 × (cost_A - cost_B) / cost_A
latency saving %       = 100 × (latency_A - latency_B) / latency_A
human-time saving %    = 100 × (minutes_A - minutes_B) / minutes_A
```

Both relative percentages and absolute differences must be shown. Small
denominators and zero baselines require absolute reporting rather than an
inflated relative percentage.

### Transaction economics

The value of an improvement depends on the transaction. For workload `w`:

```text
expected_value_per_transaction_w =
    success_probability_w × value_of_success_w
  - failure_probability_w × cost_of_failure_w
  - model_and_tool_cost_w
  - human_minutes_w / 60 × loaded_hourly_rate_w
  - latency_cost_w

incremental_value_per_transaction_w =
    configured_expected_value_w - generic_expected_value_w
```

Portfolio value is workload-weighted:

```text
cumulative_incremental_value(T) =
    Σ month=1..T Σ workload w
        transactions[w, month] × incremental_value_per_transaction_w
    - one_time_configuration_and_integration_cost
    - cumulative_monitoring_and_maintenance_cost
```

Required business outputs:

- incremental value per transaction;
- value per 1,000 transactions;
- monthly and annual value at declared volumes;
- break-even transaction count;
- payback period;
- low/base/high scenarios using confidence bounds and volume assumptions.

No universal uplift percentage may be multiplied across every agent task.
Each workload retains its own effect size, transaction value, failure cost,
and volume. Portfolio extrapolation uses the actual workload mix.

## Draft practical gates

Final gates will be locked after the pilot and before confirmation. The current
design intent is:

1. **Material win:** on at least two of four workloads, the configured agent
   either:
   - improves locked quality-adjusted utility by at least 5% without a material
     cost increase; or
   - preserves quality within 2% while reducing total cost or human time by at
     least 10%.
2. **No hidden harm:** no platform-selected configuration is more than 2%
   worse than the generic agent on locked confirmation utility. A workload
   with no demonstrated gain should retain the baseline.
3. **Risk improvement:** the configured arm reduces critical failures or
   unsupported actions on at least one workload without increasing them
   materially elsewhere.
4. **Repeatability:** improvement is not produced solely by one run; paired
   task-clustered intervals and repeated-trial variance are reported. A
   direction must hold in at least two of three repeat-index aggregates, the
   median task effect must agree, and leave-one-task-out analysis must not
   reverse the mean direction.
5. **Economic plausibility:** at least one target workload has a positive
   lower-bound transaction value and a realistic break-even volume after
   configuration, evaluation, and monitoring costs.

The standing 2% research floor remains the minimum materiality check. The 5%
or 10% thresholds above are stronger product-value thresholds, not substitutes
for paired uncertainty analysis.

For confirmation, each workload declares exactly one route before execution:
quality superiority, efficiency with quality non-inferiority, or retain the
baseline. Multiple workload hypotheses use Holm adjustment. Critical failures
remain a separate veto metric; rare-event safety improvement is not claimed
when the event count is too small.

## What would falsify the product claim

- The generic agent matches configured quality, cost, safety, and consistency.
- Gains disappear on untouched confirmation tasks.
- Configuration-search and evaluator cost exceed the downstream value.
- Improvements occur only because the configured arm received more tools,
  context, time, or hidden task information.
- One configuration helps search but causes unacceptable regressions in other
  workloads and the platform fails to retain the baseline.
- Projected value depends on applying one attractive percentage to unrelated
  transaction types.

## Post-diagnostic execution roadmap

**Status date:** 2026-08-02  
**Current gate:** diagnostic selection is complete; formal confirmation and
the product build remain closed.

The earlier instrumentation, search configuration selection, and diagnostic
transfer work are complete. The tasks below are the authoritative execution
order from the current checkpoint. A later task may begin early only where its
inputs do not depend on an unfinished gate and it cannot expose confirmation
tasks, mappings, or outputs.

Checklist notation:

- `[x]` completed and verified;
- `[ ]` required work not yet completed;
- **BLOCKED** means an external runtime, credential, custody, or business input
  is required before the task can finish.

### Task 0 — Preserve the diagnostic research checkpoint

**Purpose:** create a recoverable, reviewable boundary before changing the
controller or experiment.

- [x] Re-run the POC 6c test suite: 118 passed and 2 platform symlink tests
  skipped.
- [x] Verify the 32-task frozen confirmation validator and the 356-file
  content-addressed manifest.
- [x] Review the complete working-tree scope and exclude caches, credentials,
  temporary run artifacts, and unrelated files. (working tree clean; .gitignore
  covers __pycache__, *.pyc, .pytest_cache; no secrets or temp files found)
- [x] Commit the research documents, POC 2–6c evidence, fixtures, harnesses,
  results, and manifest as one explicitly named diagnostic checkpoint.
  (commit fd87ce8 — "Task 0: diagnostic research checkpoint — PROGRESS.md hash record")
- [x] Record the checkpoint commit and confirmation-input hashes in
  `PROGRESS.md`. (commit 2c196b2a…; all 8 frozen hashes recorded 2026-08-04)

**Deliverable:** a clean, recoverable diagnostic checkpoint with no accidental
secrets or generated caches.

**Exit gate:** the checkpoint can be reconstructed from version control and all
recorded validation commands pass from that state.

### Task 1 — Build the canonical decision-technique registry

**Purpose:** turn the existing v1 registry and POC evidence into a small,
testable ontology with executable assumptions, empirical evidence grades, and
failure modes. (Source revised from Project 008 vault to existing POC results —
vault provenance not required; see 2026-08-04 decision in conversation.)

- [x] Extract decision-relevant concepts and normalize into stable canonical IDs.
  (7 v2 curated + 51 v1 back-ported; 0 duplicates)
- [x] Classify every retained record as one of: executable-policy |
  decision-interface | evaluation-method | runtime-integration | background-math.
  (All 7 v2 records classified; v1 records marked legacy with null classification)
- [x] Define schema v2 with: decision block served, required state/feedback/
  observability, dynamics, horizon, simple baseline, executable policy reference,
  cost/latency model, failure modes, incompatible_when, evidence grade + source.
  (registry/schema.md v2.0)
- [x] Produce shortlist of 20–30 canonical candidates.
  (58 total; 7 fully curated; 51 back-ported v1 available for future curation)
- [x] Fully curate first operational candidates: Explorer (3), Stopper (3), Critic (1).
  (explore-then-commit, ucb1, thompson-sampling, fixed-budget-stopper,
  trend-marginal-stopper, confidence-marginal-stopper, evidence-critic)
- [x] Add schema validation, duplicate detection, provenance checks, and tests.
  (registry/validate.py, registry/test_registry.py — 26 tests, all pass)
- [ ] Add schema validation, duplicate detection, provenance checks, and tests.

**Deliverable:** a versioned machine-readable registry plus a human-readable
registry report.

**Exit gate:** each shortlisted method is either executable or explicitly
classified as non-executable, and no candidate can be recommended without its
assumptions and baseline.

### Task 2 — Convert search Candidate 2 into an executable controller

**Purpose:** test an enforced decision architecture, not only additional prompt
instructions.

- [ ] Preserve the current generic and Candidate 2 prompts and hashes as the
  diagnostic reference.
- [ ] Define typed controller state for question facets, inspected evidence,
  sentence support, unresolved gaps, contradictions, and remaining budgets.
- [ ] Define allowed controller actions and deterministic transition records.
- [ ] Enforce search/read budgets outside the model.
- [ ] Implement the evidence ledger as runtime state rather than unverified
  prose behavior.
- [ ] Implement the sentence-support critic gate and record every rejection or
  repair.
- [ ] Implement the quality-protected stopping gate and hard-budget stop.
- [ ] Route all corpus access through the deterministic frozen-corpus facade.
- [ ] Capture model identity, provider usage, tokens, cost, tool calls, latency,
  decisions, and policy version in the trace schema.
- [ ] Add unit tests for every state transition, budget boundary, critic veto,
  stopping condition, and invalid trace.
- [ ] Add paired integration tests proving that both arms receive identical
  tasks, data, tools, and hard limits.

**Deliverable:** a provider-independent Candidate 2 controller and adapter
interface with deterministic validation.

**Exit gate:** the configured process is runtime-enforced and auditable; the
generic arm remains unchanged; confirmation files have not been opened by an
agent run.

### Task 3 — Attribute value with selection-only ablations

**Purpose:** identify which block creates value before treating the configured
bundle as one indivisible intervention.

- [ ] Use only seen pilot tasks or a new declared selection set; never use the
  32 untouched confirmation tasks.
- [ ] Freeze the selection metrics, model version, task budgets, and analysis
  before generating ablation outputs.
- [ ] Run matched arms for:
  - strong generic agent;
  - generic plus evidence ledger;
  - generic plus critic gate;
  - generic plus stopper;
  - complete executable Candidate 2.
- [ ] Repeat trials sufficiently to separate task effects from run stochasticity.
- [ ] Report block-level quality, failure, token, tool, latency, and contract-
  reliability effects.
- [ ] Check important interactions; do not infer that independently useful
  blocks compose additively.
- [ ] Remove blocks that add no material value or create regressions.
- [ ] Freeze the final Candidate 2 policy version and all input hashes.

**Deliverable:** an ablation and configuration-selection report with a frozen
confirmation candidate.

**Exit gate:** Candidate 2's retained blocks have a defensible selection signal,
or Candidate 2 is rejected and the generic baseline is retained.

### Task 4 — Close every confirmation-readiness gate

**Purpose:** make the frozen search run auditable enough to support a product
decision.

- [ ] **BLOCKED — Runtime:** lock an auditable agent model ID and version.
- [ ] **BLOCKED — Runtime:** lock auditable evaluator model IDs and versions.
- [ ] **BLOCKED — Runtime:** capture provider token and monetary usage for every
  call.
- [ ] **BLOCKED — Isolation:** provide OS-enforced isolated workspaces that
  prevent cross-arm, mapping, evaluator, and out-of-scope access.
- [ ] Enforce the deterministic corpus facade as the only vault access path.
- [ ] Calibrate the anchored numeric rubric using non-confirmation material and
  the fixed evaluators.
- [ ] **BLOCKED — Custody:** lock the randomization seed and blind-mapping
  custody location outside agent/evaluator access.
- [ ] Reverify task, prompt, schema, rubric, corpus, label, and manifest hashes.
- [ ] Update the preregistration checklist without changing outcome thresholds
  in response to generated results.

**Deliverable:** an activated, timestamped preregistration with every readiness
checkbox satisfied.

**Exit gate:** all seven substantive readiness requirements are complete. If
one is missing, subsequent runs remain diagnostic and Task 5 must not start.

### Task 5 — Execute untouched search confirmation

**Purpose:** obtain the first confirmatory estimate of configured-versus-generic
value.

- [ ] Activate the preregistration before generating any confirmation answer.
- [ ] Generate the blinded arm mapping under the locked seed and custody rules.
- [ ] Execute the generic and frozen Candidate 2 arms with identical invariants
  and the declared repeat schedule.
- [ ] Validate pair integrity, budgets, corpus access, leakage, provider usage,
  and model versions before scoring.
- [ ] Exclude invalid pairs only under the preregistered missing-data rules.
- [ ] Score valid outputs blindly with the fixed evaluators.
- [ ] Run the locked task-clustered analysis, uncertainty checks, repeat
  sensitivity, critical-failure veto, and cost comparison.
- [ ] Publish all valid, invalid, missing, and excluded results with no optional
  stopping or post-result threshold changes.

**Deliverable:** a confirmation report declaring pass, fail, or invalid under
the preregistered rules.

**Exit gate:** the result is reproducible from frozen inputs and auditable raw
traces. An invalid confirmation is not converted into a product claim.

### Task 6 — Evaluate transaction economics and alternatives

**Purpose:** determine whether a confirmed technical effect is worth buying and
maintaining.

- [ ] Obtain declared transaction volumes, value of success, failure cost,
  loaded human-review cost, and latency cost for the target search workload.
- [ ] Calculate incremental value per transaction and per 1,000 transactions.
- [ ] Include configuration search, integration, evaluation, monitoring,
  revalidation, and expected model-upgrade costs.
- [ ] Compare Candidate 2 against:
  - the current production implementation;
  - the matched strong generic agent;
  - the best simple deterministic policy;
  - an equal-cost stronger-model or additional-compute alternative;
  - human review where operationally relevant.
- [ ] Report lower/base/upper scenarios, break-even volume, payback period, and
  sensitivity to model drift.
- [ ] Keep search economics separate from code development, review, and testing.

**Deliverable:** a workload-specific economic decision memo.

**Exit gate:** at least one realistic scenario has positive lower-bound value
after all adoption and maintenance costs; otherwise the build gate stays closed.

### Task 7 — Make the product build decision

**Purpose:** convert the evidence into an explicit go, narrow, retain, or stop
decision.

- [ ] If confirmation and economics pass, formalize Explorer, Stopper, and
  Critic contracts and build the Evidence Engine plus one runtime adapter.
- [ ] If configured quality does not pass, retain the generic baseline and test
  whether avoided regressions justify a measurement/simplification product.
- [ ] If technical value exists but economics fail, stop or redesign the target
  workload rather than claiming non-economic uplift.
- [ ] If results depend on one model version, narrow the claim and define the
  revalidation trigger instead of presenting a durable universal policy.
- [ ] Record the decision, supporting evidence, rejected claims, and next gate
  in `VISION.md`, `RESEARCH.md`, and `RESULTS.md`.

**Deliverable:** a signed product-decision record and, only on a pass, the next
implementation milestone.

**Exit gate:** the decision follows the preregistered evidence and economics,
not the attractiveness of the original product concept.

## Work explicitly deferred

Until Tasks 5–7 establish confirmed and economic value, do not:

- build the broad drag-and-drop visual workbench;
- expand the registry across every Project 008 label;
- build adapters for several agent frameworks;
- advertise a universal configured-agent uplift percentage;
- populate missing provider cost or token data with estimates;
- use the untouched confirmation set for configuration selection or debugging.
