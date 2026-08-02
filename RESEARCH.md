# Research & Test Log

**Purpose**: the evidence file. VISION.md holds the thesis; this holds what
is actually *known*. Nothing gets built until the POC that justifies it has
passed a pre-registered criterion.

**Rule**: every POC states its pass/fail condition **before** it runs. A POC
that cannot fail is a demo, not a test.

**Updated**: 2026-07-31

---

## Status

| POC | Question | Status | Outcome |
|---|---|---|---|
| **1** | Can the vocabulary and canvas be expressed at all? | ✅ done | Feasible — but star ratings proved wrong (see POC 2) |
| **2** | Does the best control policy depend on the task? | ⚠️ superseded | Exploratory; branch leakage and an invalid control required POC 2b |
| **2b** | Does regime-dependent viability survive the corrected design? | ✅ done | **PASS — four policies swing between viable and disqualified** |
| **3** | Are POC 2b's findings robust to K, budget, and parameters? | ❌ done | **FAIL — only one fixed policy met the persistence rule; simple-baseline coverage was 4/9** |
| **4** | Can the task regime be *detected* cheaply? | ❌ done | **FAIL — detector was at chance and reduced reward by 2.43%** |
| **5** | Does the pattern hold at a second decision point? | ✅ done | **PASS — four stopping rules swing between viable and disqualified** |
| **6a** | Does simulated selection behavior transfer to the Project 008 corpus? | ❌ done | **FAIL — ranking transferred (ρ=0.943), but no policy swung across corpus strata** |
| **6b** | Can Project 008 supply realistic search tasks and evidence fixtures? | 🟨 reframed | 30-case draft exists; corpus completeness must not be assumed |
| **6c** | Does a configured agent beat a matched generic sub-agent across real work? | 🟨 diagnostic selection complete | Four workload pilots complete; untouched search confirmation is frozen but gated |
| **6** | Does simulation transfer to a live LLM agent? | ⬜ blocked | needs API key + real task |
| **7** | Can config space be searched affordably? | ⬜ | — |

**Build gate**: closed. POC 5 supports a second decision block and POC 6a found
strong simulation-to-corpus rank correlation, but POCs 3, 4, and 6a failed
their full gates. No registry schema, canvas, or general-purpose recommendation
engine is justified. Focused research may continue, but a build requires
reviewed real cases and direct replay/live measurement rather than static or
cheap-probe recommendation. The next product-level test is a matched
generic-agent versus configured-agent comparison, not a factual-answer
comparison against an external internet reference.

---

## Literature — what is already established

The pattern (classical decision algorithms controlling a frozen LLM at
inference) is proven and published. It is *not* systematised. Full citations
in VISION.md § Prior Art; the load-bearing points:

| Established | Source |
|---|---|
| MCTS over LLM trajectories works at inference | LATS, arXiv 2310.04406 |
| Bandits can select retrieval strategy by query complexity | MBA-RAG, arXiv 2412.01572 |
| Sub-query-as-arm budget allocation works — **our exact use case** | arXiv 2510.18633 |
| Reward can come from preliminary reasoning results | MAB-DQA, arXiv 2604.08952 |
| No standardised toolkit exists; evaluation is fragmented; few production-ready tools | Survey, arXiv 2601.12945 |
| No agent spec standard covers decision logic | Open Agent Spec / OAF / OASF |

**Implication**: the techniques are not the risk. The *selection layer* is
unbuilt, and that is what we are testing.

---

## POC 2 — Does technique choice depend on the task?

> **Historical exploratory result.** Review found deterministic placement of
> the rich branch and a "uniform" control in which depletion made allocation
> matter. The pre-registered criterion also did not match the post-hoc linter
> conclusion. POC 2 is retained for auditability but is superseded by POC 2b.

**Ran**: 2026-07-28 · `poc2/` · 5 regimes × 6 policies × 2000 paired trials
**Method**: depleting multi-branch search (K=12), hidden yields, fixed
budget. Common random numbers so comparisons are paired; 10k-resample paired
bootstrap. `Greedy(LLM-proxy)` = sweep each branch once, then commit —
a deliberately *generous* stand-in for an unguided LLM loop.

**Pre-registered criterion**: premise survives if the winning policy differs
by regime.

### Finding 1 — ranking the top of the field is selling noise

Margin between #1 and #2 across all five regimes: **0.6% – 3.6%**. The top
two or three techniques are practically tied everywhere.

With 2000 paired trials, statistical significance detects differences far
too small to matter — the `uniform` control condition came out "significant"
at a 0.7% effect. A practical-significance floor (2% relative) had to be
added to avoid reporting noise as insight.

> **POC 1's ★★★★★ / ★★★★☆ UI asserts a distinction the data does not
> support.** Star ratings are the wrong abstraction.

### Finding 2 — disqualification is real, large, and goal-dependent

`viable` ≥95% of best · `weak` 80–95% · `DISQUAL` <80%

| Policy | uniform | needle | deceptive | scarce | rich |
|---|---|---|---|---|---|
| RoundRobin | **viable** | **DISQUAL** | weak | weak | **DISQUAL** |
| UCB1 | viable | **DISQUAL** | weak | weak | weak |
| DiscountedThompson | viable | **DISQUAL** | weak | weak | **DISQUAL** |
| ThompsonSampling | viable | **DISQUAL** | viable | viable | viable |
| EpsilonGreedy | weak | viable | viable | viable | viable |
| Greedy (naive) | weak | viable | viable | viable | weak |

Four of six techniques swing from viable to disqualified by task. RoundRobin
is the **best** policy under `uniform` and loses **60% of findings** under
`needle`. Worst-case cost of choosing wrong: **149%**.

> The premise survives **in its negative form**. The valuable signal is not
> "which is best" but **"which will wreck your agent."**

### Finding 3 — sophistication pays 0–11%, sometimes nothing

| Regime | Uplift of best policy over naive loop |
|---|---|
| needle | **+0.0%** — naive already optimal |
| scarce | **+0.0%** — naive already optimal |
| deceptive | +2.8% |
| uniform | +7.9% |
| rich | +11.1% |

In 2 of 5 regimes a principled controller adds nothing. A platform that
always recommends sophistication would be wrong 40% of the time here.

Because the naive baseline is *generous* (systematic sweep before
committing, which a real LLM loop will not do), **0–11% is a floor, not a
ceiling.**

### Design decisions forced by POC 2

| POC 1 assumed | Corrected |
|---|---|
| Rank techniques by goal fit, show ★ | Ranking the top is meaningless — **disqualify** instead |
| Validator confirms "✅ Valid" | Validator's job is "**this will fail, and here is the cost**" |
| More technique = better agent | Must be able to say "**your simple loop is fine**" |
| Scoring engine is the product | **The linter is the product** |

### Limitations

1. Simulated, not LLM-in-the-loop — deliberate, to isolate the control question
2. Regimes hand-designed → Finding 2 is partly by construction; Findings 1 and 3 emerged unbidden
3. One decision point only (branch selection)
4. Single parameterisation, K=12 → **POC 3**
5. No cost asymmetry between policies; tree search with per-node LLM calls would look far worse
6. Oracle is greedy-on-true-yields — strong reference, not provable optimum

---

## POC 2b — Corrected confirmatory policy-viability test

**Ran**: 2026-07-28 · `poc2b/` · 6 regimes × 6 fixed policies  
**Preregistration**: written before first execution in
`poc2b/PREREGISTRATION.md`  
**Method**: randomized semantic branch labels, stationary no-effect control,
finite urns that consume successes and failures, fixed per-branch potential
outcomes shared by every policy, and disjoint selection/confirmation seeds.

### Locked primary conditions

POC 2b passes only when:

1. Every policy pair is equivalent within ±2% in the stationary uniform
   control.
2. At least two policy configurations are viable in one non-control regime and
   disqualified in another.
3. `ExploreThenCommit` is viable in at least one non-control regime.

### Result — PASS

| Condition | Result |
|---|---|
| Valid stationary control | ✅ PASS |
| Regime-dependent viability/disqualification | ✅ PASS — four policies |
| Simple baseline viable somewhere | ✅ PASS |

Policies satisfying the locked swing rule:

- `ExploreThenCommit`
- `UCB1`
- `ThompsonSampling`
- `DiscountedThompson(g=0.9)`

The simple baseline was viable in the stationary needle, depleting needle, and
scarce regimes, but disqualified in the rich depleting regime.

### Material adaptive-policy gains

The locked reference materially exceeded `ExploreThenCommit` beyond the
pre-registered 2% floor in only two regimes:

| Regime | Locked reference | Raw uplift |
|---|---|---:|
| deceptive depleting | UCB1 | **+13.44%** |
| rich depleting | ThompsonSampling | **+44.45%** |

No material gain was confirmed in stationary needle, depleting needle, or
scarce stationary. This is the desired falsifiable product behavior: sometimes
an adaptive controller matters greatly, and sometimes the simple policy is
sufficient.

### What is now supported

Within the corrected simulation and these fixed configurations, task structure
can make a policy viable in one regime and disqualified in another. Continuing
research into a policy-testing, rejection, and explanation layer is justified.

### What remains unsupported

- Natural-language goal → correct policy recommendation
- Automatic detection of the workload regime
- Transfer to a live LLM or retrieval agent
- Generalization beyond the exploration decision block
- Robustness across `K`, budget, policy parameters, and workload mixtures
- Economic value after controller and evaluator cost

Full method and tables: `poc2b/README.md`. Machine-readable output:
`poc2b/results.json`.

---

## POC 3 — Size, budget, workload, and parameter sensitivity

**Ran**: 2026-07-28 · `poc3/` · 45 primary cells plus a 12-cell parameter
study  
**Preregistration**: written before first execution in
`poc3/PREREGISTRATION.md`  
**Method**: inherited POC 2b's corrected potential-outcome design; swept
`K ∈ {5, 12, 30}`, `budget/K ∈ {1, 4, 16}`, one stationary control, four
non-control workload shapes, six fixed primary policies, and reasonable
parameters for four adaptive-policy families. Each cell used 250 selection
trials and 750 disjoint confirmation trials.

### Result — FAIL

| Locked condition | Required | Result |
|---|---:|---:|
| Fair stationary controls | 9/9 pass | **9/9 PASS**; worst gap 1.45% |
| Fixed policies that swing in at least three settings | ≥2 | **1 FAIL** — UCB only |
| Settings where `ExploreThenCommit` is viable somewhere | ≥6/9 | **4/9 FAIL** |
| Parameter-robust adaptive families | ≥2 | **4 PASS** |

Because two of four locked conditions failed, the POC failed. Thresholds were
not changed after seeing the result.

### What failed

Only `UCB1(c=2.0)` changed between viable and disqualified workload shapes in
at least three of the nine size-budget settings. Other fixed configurations
showed the same behavior in only one or two settings:

| Fixed policy | Settings with a viability/disqualification swing |
|---|---:|
| UCB1(c=2.0) | **4** |
| ThompsonSampling(prior=1.0) | 2 |
| DiscountedThompson(g=0.9) | 2 |
| RoundRobin | 1 |
| ExploreThenCommit | 1 |
| EpsilonGreedy(e=0.1) | 1 |

The simple `ExploreThenCommit` baseline was viable in at least one workload
shape in only four settings: all three `budget/K = 4` settings and
`K=30, budget/K=16`. It did not meet the preregistered six-setting coverage
rule.

### What survived

- All nine no-effect controls passed, with a worst policy-mean gap of 1.45%.
- Every tested adaptive family had at least two parameter configurations that
  were viable somewhere and disqualified elsewhere.
- Across the 36 non-control cells, the locked reference materially exceeded
  `ExploreThenCommit` beyond the 2% floor in 25 cells.
- The largest raw improvement over `ExploreThenCommit` was 111.31% in the
  `K=5`, `budget/K=16`, deceptive-depleting cell. This is a simulated extreme,
  not a production forecast.

### Interpretation

POC 2b remains valid for its exact tested configurations, but its fixed-policy
generalization is not established across size and budget. The result supports
a narrower product idea:

> Test and calibrate both the policy family and its parameters against the
> actual workload contract; do not issue a static recommendation from the
> technique name alone.

That favors an evidence and measurement service over a catalogue that assigns
universal technique ratings. It also raises the importance of POC 4: if the
workload cannot be identified or sampled cheaply, the observed sensitivity
cannot be converted into an actionable recommendation.

Full method and tables: `poc3/README.md`. Machine-readable output:
`poc3/results.json`.

---

## POC 4 — Cheap workload identification

**Ran**: 2026-07-28 · `poc4/` · 2,000 selection worlds and 6,000 untouched
confirmation worlds  
**Preregistration**: written before first execution in
`poc4/PREREGISTRATION.md`  
**Method**: at `K=12` and budget `48`, draw equally from four hidden workload
shapes. Spend 5%, 10%, or 15% of the task budget on a fixed diagnostic probe,
classify the workload with a standardized 31-nearest-neighbor detector, and
continue with the policy locked for the predicted workload. Probe rewards
counted toward the same fixed budget. The selected probe size was chosen by
five-fold out-of-fold selection and evaluated once on confirmation worlds.

### Result — FAIL

| Locked condition | Result |
|---|---|
| Free oracle materially beats best fixed | **PASS — +2.22%** |
| Oracle value survives the probe | **PASS — +2.11%** |
| Detector beats the same-probe fixed-policy control | **FAIL — −2.36%** |
| Detector beats best fixed from the first pull | **FAIL — −2.43%** |

The selection stage locked the 3-pull probe. On confirmation, its exact
workload accuracy was 25.15%, effectively the 25% chance rate. Its
policy-selection accuracy was 71.93%. Because three of four workloads mapped
to `ExploreThenCommit`, simply always using the best fixed policy had an
implicit 75% policy-selection accuracy.

### Why it failed

The useful exception was the deceptive-depleting workload, which mapped to
`UCB1(c=2.0)`; the other three mapped to `ExploreThenCommit`. The detector
correctly recognized only 53 of 1,500 deceptive confirmation worlds. Its false
UCB selections on the other workloads cost more than its few correct
detections gained.

The failure was not rescued by the secondary probe sizes:

| Probe | Exact workload accuracy | Policy accuracy | Versus same-probe fixed | Versus fixed from start |
|---:|---:|---:|---:|---:|
| 3 pulls | 25.15% | 71.93% | −2.36% | −2.43% |
| 5 pulls | 26.60% | 74.80% | −0.15% | −0.63% |
| 8 pulls | 27.40% | 75.00% | 0.00% | −1.33% |

Only the 3-pull result controls the locked verdict, but none of the secondary
fractions created positive detection value.

### Interpretation

There was a real but small policy-selection opportunity: a true-regime oracle
could gain 2.22%. A cheap single-task probe could not identify the exception
reliably enough to capture it. This rejects the current automatic workflow:

`small probe → infer workload type → recommend controller`

It does not reject measurement using richer evidence. The surviving direction
is more conservative:

- test policies directly on historical or representative workload episodes;
- use shadow or controlled live evaluation when history is insufficient;
- keep a strong fixed policy unless evidence for switching clears the expected
  misclassification cost;
- treat natural-language workload declarations as hypotheses, not facts.

Full method and tables: `poc4/README.md`. Machine-readable output:
`poc4/results.json`.

---

## POC 5 — Stopping-rule generality

**Ran**: 2026-07-28 · `poc5/` · 2,500 selection trajectories and 7,500
untouched confirmation trajectories  
**Preregistration**: written before first execution in
`poc5/PREREGISTRATION.md`  
**Method**: fix Thompson Sampling as the branch-selection controller, generate
one 192-pull reward trajectory per world, and evaluate six stopping rules on
prefixes of that identical trajectory. Net utility was
`findings - 0.20 × pulls`, so the test measured both useful output and
continuation cost.

### Result — PASS

| Locked condition | Result |
|---|---|
| Zero-cost shared-prefix sanity | **PASS** |
| Every reference has positive confirmation utility | **PASS** |
| At least one rule swings across workloads | **PASS — four rules** |
| Full-budget continuation viable somewhere | **PASS** |
| Efficient adaptive stopping viable somewhere | **PASS** |

Rules satisfying the locked viability/disqualification swing:

- `FixedBudget`
- `FixedHalf`
- `ConfidenceMarginal(24,z=1.28)`
- `TrendMarginal(12+12)`

### Different workloads required different stopping behavior

| Workload | Locked rule | Mean utility | Mean pulls |
|---|---|---:|---:|
| stationary uniform | FixedBudget | 28.96 | 192.0 |
| stationary needle | FixedBudget | 74.05 | 192.0 |
| depleting needle | FixedHalf | 26.12 | 96.0 |
| deceptive depleting | TrendMarginal | 3.08 | 31.8 |
| heterogeneous depleting | ConfidenceMarginal | 38.18 | 158.1 |

This is not a generic preference for stopping early:

- In stationary needle, stopping at half budget produced 26.09 utility versus
  74.05 from continuing.
- In depleting needle, half budget produced 26.12 versus 17.11 from using the
  full budget.
- In deceptive depletion, trend stopping changed mean utility from −3.16 at
  full budget to +3.08 while using 83.4% fewer pulls.
- In heterogeneous depletion, confidence stopping produced 38.18 versus 35.34
  at full budget while using 17.7% fewer pulls.

The candidates also contained useful rejections. `WindowMarginal(24)` was
disqualified in all five workloads, and the informal `PatienceStop(8)` proxy
was never viable.

### Interpretation

Within this simulation, the project is not merely a branch-selection library.
Stopping is a second decision block where workload structure and cost change
which logic is acceptable. The supported product behavior is again negative
and evidence-led:

> Test stopping rules against the workload and cost contract; reject rules
> that stop valuable work too early or continue after marginal value has
> disappeared.

POC 5 does not reopen the build gate. POC 3 still rejected broad fixed-policy
generalization and POC 4 rejected cheap single-task workload detection.
Therefore, this stopping result supports a direct measurement/replay
workbench, not an automatic recommendation from task text.

Full method and tables: `poc5/README.md`. Machine-readable output:
`poc5/results.json`.

---

## POC 6a — Historical Project 008 corpus transfer

**Ran**: 2026-07-31 · `poc6a/` · 95 selection queries and 145 untouched
confirmation queries  
**Preregistration**: written before first execution in
`poc6a/PREREGISTRATION.md`  
**Method**: use the locked Project 008 vault as a 12-arm retrieval corpus.
Existing tag metadata supplied weak relevance labels but was removed from
searchable text. BM25 ranked notes inside each arm; the six POC 3 policies
allocated a 48-document retrieval budget. Tag queries were split by stable
hash and evaluated as concentrated or diffuse according to where relevant
notes existed.

### Result — FAIL

| Locked condition | Result |
|---|---|
| Snapshot and benchmark integrity | **PASS** |
| Positive relevance signal | **PASS** |
| Simulation ranking correlation >0.60 | **PASS — ρ=0.943** |
| At least one policy swings across strata | **FAIL — none** |
| `ExploreThenCommit` viable somewhere | **PASS** |

The failure is specific: policy ordering transferred, but the stronger
simulation claim that a policy becomes acceptable in one workload type and
harmful in another did not transfer across these two corpus strata.

### Ranking transfer was strong

Simulation ranking at `K=12`, `budget=48`:

1. ExploreThenCommit
2. Epsilon Greedy
3. Thompson Sampling
4. UCB
5. Discounted Thompson
6. Round Robin

Historical aggregate ranking:

1. Epsilon Greedy
2. ExploreThenCommit
3. Thompson Sampling
4. UCB
5. Discounted Thompson
6. Round Robin

Only the top two exchanged places, producing Spearman correlation `0.943`.
This is useful transfer evidence even though the binary POC failed.

### Concentrated queries had one clear rejection

| Policy | Status | Mean findings | Relative to reference |
|---|---|---:|---:|
| Epsilon Greedy | viable | 5.278 | 100.0% |
| ExploreThenCommit | viable | 5.153 | 97.6% |
| Thompson Sampling | uncertain | 4.847 | 91.8% |
| Discounted Thompson | uncertain | 4.347 | 82.4% |
| UCB | uncertain | 4.306 | 81.6% |
| Round Robin | **disqualified** | 3.194 | 60.5% |

Epsilon Greedy exceeded ExploreThenCommit by 2.43%; the paired difference
interval was `[0.009, 0.241]` findings.

### Diffuse queries did not separate reliably

The locked selection reference was Thompson Sampling. On confirmation,
Epsilon Greedy had the highest raw mean, while Thompson remained viable and
all other policies were uncertain. No policy was disqualified. The locked
reference's raw 4.71% advantage over ExploreThenCommit had a wide paired
interval crossing zero.

Because Round Robin was disqualified only for concentrated queries and merely
uncertain—not viable—for diffuse queries, it did not satisfy the locked swing
definition.

### Interpretation

POC 6a supports:

- the simulation's broad policy ordering has predictive value on this corpus;
- Round Robin can be rejected for concentrated retrieval;
- a simple adaptive baseline remains competitive;
- the historical replay harness can expose effect size and uncertainty.

It does not support:

- selecting a different policy from concentration alone;
- transferring the simulation's viability/disqualification swing;
- live-LLM performance;
- production relevance feedback.

The corpus is also highly imbalanced: 491 indexed notes are in `AI & SDLC`,
254 in `raw`, and 102 in `Learning`, while several arms are tiny and
`Synthesis` contributes no tagged indexed documents. This differs materially
from the balanced simulation and may explain why one robust adaptive policy
performed well across both strata.

Full method and tables: `poc6a/README.md`. Machine-readable output:
`poc6a/results.json`.

---

## POC 6b preparation — Real search-task and evidence fixtures

**Prepared**: 2026-07-31 · `poc6b/`  
**Status**: **reframed; draft fixtures only**

POC 6a's tag labels were useful weak supervision but not reviewed relevance
judgments. A deterministic review package now reduces the cost of creating the
missing gold set:

- 25 proposed answerable questions across agent engineering, mathematics,
  retrieval, software, finance, science, and productivity;
- 5 proposed abstention questions outside the vault's demonstrated coverage;
- 3 metadata-supported candidate notes per answer case;
- 2 high-ranking hard negatives per answer case;
- 5 lexical challenge results per abstention case;
- evidence excerpts, relevance checkboxes, required-answer fields, unsupported
  claim fields, and case approval controls;
- one complete worksheet plus three ten-case review batches.

All proposed labels remain blank. Metadata positives, lexical negatives, and
excerpts are candidates—not ground truth. More importantly, Project 008 is an
agent knowledge environment, not a complete answer key. A realistic question
may be only partially supported by the vault.

The package therefore supplies candidate tasks and evidence for a paired-agent
test. In vault-only mode, both a generic sub-agent and configured agent must
distinguish supported claims from missing evidence. In a separately reported
vault-plus-web mode, both arms may receive identical web access; the web is a
shared tool, not the reference answer. The comparison measures answer support,
coverage, gap detection, unsupported claims, cost, latency, and stopping
behavior.

Review entry point: `poc6b/GOLD_SET_REVIEW.md`. Machine-readable draft:
`poc6b/cases.draft.json`.

---

## POC 6c design — Configured-agent comparative value benchmark

**Designed**: 2026-07-31 · `poc6c/`  
**Status**: **diagnostic selection complete; confirmation not activated**

POC 6c directly tests the product claim. Each paired trial holds the task,
model, tools, data, context, and hard budget constant:

- **Arm A:** a normal general-purpose sub-agent whose control choices remain
  implicit in its instructions;
- **Arm B:** the same underlying agent with explicit decision contracts and
  platform-selected control blocks.

The workload ladder follows the vision:

1. search/research over Project 008;
2. code development;
3. code review;
4. code testing.

Each workload has outcome checks appropriate to the work. Search is assessed
against cited evidence and justified gap detection. Code development uses
tests and repository invariants. Code review uses severity-weighted seeded
defect recall and false-positive burden. Code testing uses failures exposed,
mutation score, test validity, flakiness, runtime, and cost.

Results report both absolute and relative effects:

- task success and quality;
- critical failures and unsupported claims;
- model/tool cost, tokens, and calls;
- latency and human correction time;
- repeated-run variance.

Confirmed effects are converted into incremental expected value per
transaction. Monthly and annual projections are workload-volume weighted and
include one-time configuration/integration plus ongoing evaluation and
monitoring costs. No single uplift percentage is extrapolated across unrelated
task types.

Design entry point: `poc6c/PLAN.md`.

The first 10-case vault-only instrumentation run is complete. Both arms passed
strict evidence validation. Two independent blind evaluators rejected the
first configured controller: its paired mean quality differences versus the
strong generic control were -8.1 and -6.6 points, with 90% agreement on which
anonymous answer in each pair was better. The controller read fewer notes but
failed to protect evidence coverage and gap disclosure. Candidate 1 is
therefore rejected, and a revised quality-protected Candidate 2 is being
tested on the selection-only batch. These seen tasks cannot support an efficacy
claim.

The revised Candidate 2 reversed the selection-set direction under two fresh
blind evaluators: paired means were +6.0 and +4.8 points, with 90% agreement on
pair preference. It used every allowed search call, so this is a quality
selection signal rather than an efficiency result. Candidate 2 is
provisionally frozen; confirmation remains gated on anchored scoring, fixed
auditable model/usage telemetry, stronger isolation, and untouched powered
tasks.

The five-task code-development instrumentation pilot also completed. All ten
arm runs passed boundary and leakage checks. The configured arm passed all
five evaluator-only task suites; the generic arm passed four. The sole
difference was a whitespace-only CSV record that the configured test-critic
step explicitly challenged. This is evidence that the decision architecture
can change a real coding trajectory, but five seen pilot tasks cannot estimate
a transferable uplift.

Code review did not transfer. After repairing a scorer bug that required an
undisclosed exact category label, the three valid matched pairs were ties at
perfect severity-weighted recall and precision. After harness repair, all five
generic outputs were valid (one false positive total), while two of five
configured outputs violated the JSON contract. The correct platform choice is
therefore to retain the generic baseline for review, not to claim value from
added structure.

Code testing produced a second small transfer signal. All ten runs were valid,
deterministic, and free of implementation-coupled tests. Four task pairs tied;
on one numerical-weighting task the configured tester exposed all three seeded
faults while generic exposed two. Mean distinct exposure was 2.8 versus 2.6 of
three faults per task. As with code development, this is selection evidence,
not a transferable effect estimate.

---

## Open questions ranked by how badly they could kill the project

### 1. Can richer evidence identify the actionable workload difference?
*(POC 4 cheap-probe version failed)*

The locked 5% probe was at chance, and even the secondary 15% probe created no
selection value. A static Goal Encoder or tiny single-task probe is therefore
unsupported. The remaining question is whether historical replay, repeated
tasks, shadow traffic, or a detector optimized for the decision boundary
rather than the exact regime can create value cheaply enough.

### 2. Where does the reward signal come from?
Bandits need feedback. One-shot agent tasks often have no ground truth.
Literature's answer is LLM-as-evaluator, which imports model bias directly
into the control policy. Unresolved.

### 3. Does second-decision evidence transfer? *(POC 5 simulation passed)*
Stopping rules also moved between viable and disqualified, so the concept is
not limited to branch selection in simulation. It remains unknown whether
stopping logic creates material value on real agent trajectories with answer
quality, latency, evaluator cost, and delayed outcomes.

### 4. Does simulation predict live-agent behavior?
*(POC 6a corpus ranking transferred; POC 6 remains blocked)*

Simulation predicted the six-policy ordering on historical lexical retrieval
with `ρ=0.943`, but regime-dependent disqualification did not transfer. This
is encouraging for prioritizing candidates, not sufficient for deployment.
Reviewed real queries, evaluator behavior, answer quality, and live costs
remain untested.

### 5. Does it survive better models?
If frontier models become competent controllers, value shifts to the
cheap-model tier. Viable position, different pitch.

---

## POC queue

Each states the question, the method, and the condition under which we
**abandon** the direction.

### POC 3 — Sensitivity
**Status**: completed — **FAIL**.  
**Question**: does POC 2b's regime-dependent viability persist across branch
count, budget, workload shape, and reasonable policy parameters?  
**Method actually run**: `K ∈ {5, 12, 30}`,
`budget/K ∈ {1, 4, 16}`, five workload shapes, six fixed policies, and four
parameter-family sweeps.  
**Result**: one fixed policy met the persistence rule and
`ExploreThenCommit` was viable in 4/9 settings; all controls and all four
parameter-family checks passed. Broad fixed-policy robustness is unsupported.

### POC 4 — Regime identification ⚠️ highest risk
**Status**: completed — **FAIL**.  
**Question**: can a 5%, 10%, or 15% single-task probe identify enough hidden
workload structure to select a better policy net of probe cost?  
**Result**: the locked 5% detector achieved 25.15% exact accuracy and reduced
reward by 2.43% versus the best fixed policy. The 10% and 15% secondary probes
also failed to create positive detection value. Cheap single-task automatic
selection is unsupported.

### POC 5 — Second decision point
**Status**: completed — **PASS**.  
**Question**: does the disqualification pattern generalize beyond branch
selection?  
**Method**: shared Thompson-generated reward trajectories; six fixed stopping
rules; net utility includes a 0.20 cost per pull.  
**Result**: four rules swung between viable and disqualified. Full budget was
best for stationary workloads, while half-budget, trend, and
confidence-marginal rules were best for different depleting workloads.

### POC 6 — LLM transfer 🔒 blocked
**Question**: does the simulation predict live-agent behaviour?
**Method**: port the harness to a real relationship-search task; run the top
3 and bottom 1 policy from POC 2; compare policy ordering against
simulation prediction.
**PASS**: rank correlation with simulated ordering > 0.6.
**FAIL**: simulation is decorative; recommendations require live measurement
per task.
**Needs from Shubham**: ① the real task — entity domain, what counts as a
relevant relationship, realistic per-query budget; ② whether branches
deplete in practice; ③ Anthropic API key.

### POC 6a — Historical corpus transfer
**Status**: completed — **FAIL**.  
**Question**: does the exact POC 3 `K=12`, `budget=48` selection behavior
transfer to metadata-labeled retrieval over the Project 008 vault?  
**Result**: policy ranking transferred strongly (`ρ=0.943`) and Round Robin
was disqualified on concentrated queries, but no policy swung between viable
and disqualified across concentrated and diffuse strata. This is partial
transfer evidence, not live-agent validation.

### POC 6b — Reviewed real-case transfer
**Status**: reframed as search-task and evidence-fixture preparation.  
**Question**: can the draft cases expose differences in evidence search,
stopping, gap detection, unsupported claims, quality, and cost between two
matched agents?  
**Next action**: use Batch 1 for instrumentation calibration. Do not treat
Project 008 or an internet answer as universal ground truth.

### POC 6c — Configured-agent comparative value benchmark
**Status**: diagnostic selection complete; confirmation not activated.  
**Question**: with model, task, tools, data, and budget held constant, does a
platform-configured agent create more value than a normal sub-agent?  
**Method**: paired, blinded comparison on search first, followed by code
development, code review, and code testing. Use disjoint selection and
confirmation tasks, repeat trials, task-specific outcome checks, full cost
accounting, and workload-specific transaction economics.  
**Draft product gate**: a material quality/value win on at least two
workloads, or preserved quality with material cost/human-time savings; no
hidden confirmed regression where the platform should have retained the
baseline; economically plausible break-even on at least one target workload.  
**Plan**: `poc6c/PLAN.md`.

### POC 7 — Config-space search
**Question**: can the platform search its own configuration space affordably?
**Method**: successive halving / UCB over configurations vs exhaustive grid.
**PASS**: finds a top-decile config at <20% of exhaustive cost.
**FAIL**: combinatorics are prohibitive → platform must ship strong priors
rather than search.
**Needs**: nothing, but only worth running if 3–5 pass.

---

## Standing methodology rules

Learned from POC 2; binding on every POC that follows.

1. **Pre-register the pass/fail criterion.** Written into the runner's
   docstring before execution.
2. **Practical floor alongside statistical significance.** ≥2% relative, or
   it is not a finding. Large N makes trivia significant.
3. **Common random numbers.** Paired trials; every policy faces an identical
   environment per trial.
4. **Include a control condition** where no effect is predicted. If it shows
   an effect, the method is suspect — not the world.
5. **Make the naive baseline generous.** Beating a strawman proves nothing;
   a floor measured against a strong baseline is trustworthy.
6. **Report stakes, not just winners.** Best-vs-worst spread is what tells a
   practitioner whether the decision deserves their attention.
7. **Write the limitations before the summary.** Any number quoted outward
   travels with its caveats.
8. **Use matched agent arms.** Model, task, tools, data, context, and budget
   remain identical; only the decision architecture changes.
9. **Separate selection and confirmation.** Configuration search cannot share
   tasks with the final verdict.
10. **Keep workload effects separate.** Report per-transaction effects by
    workload before applying the real transaction mix and volumes.
11. **Count adoption cost.** Configuration search, integration, evaluators,
    monitoring, and human review are included in break-even calculations.

---

## Reproducing

```bash
cd poc2b
python -m unittest -v
python experiment.py               # ~106s on reference Windows workspace

cd ../poc3
python -m unittest -v
python experiment.py               # ~571s on reference Windows workspace;
                                   # exit 2 is the preregistered FAIL verdict

cd ../poc4
python -m unittest -v
python experiment.py               # ~53s on reference Windows workspace;
                                   # exit 2 is the preregistered FAIL verdict

cd ../poc5
python -m unittest -v
python experiment.py               # ~59s on reference Windows workspace

cd ../poc6a
python -m unittest -v
python experiment.py               # ~7s on locked Project 008 snapshot;
                                   # exit 2 is the preregistered FAIL verdict
```
Full outputs are in each POC directory's `results.json`; locked rules are in
each `PREREGISTRATION.md`. Original POC 2 artifacts remain in `poc2/`.
