# Agent Brain Platform — Vision

**Created**: 2026-07-28

**Updated**: 2026-07-31 (v5 — paired agent-value and workload-transfer direction)

**Author**: Shubham

**Status**: Vision / Research-Gated

---

## Origin

This project grew out of **Project 008 — Obsidian Knowledge Files**.

While studying reinforcement learning, Markov decision processes, Minimax,
Monte Carlo tree search, Bayesian inference, bandits, control theory, testing,
and evaluation, a practical question emerged:

> Agent builders use prompts, tools, loops, and workflows—but when an agent
> must choose, explore, plan, allocate effort, update a belief, or stop, are
> we using the mathematical methods created for those decisions?

Usually, the answer is no. The LLM is asked to make the control decision
implicitly:

- Which hypothesis should I investigate?
- Which tool, model, file, source, or agent should act?
- Should I explore another possibility or continue the current one?
- How much time, money, or token budget should this branch receive?
- What does this new evidence imply?
- When is the evidence sufficient to stop?

The relevant knowledge exists across reinforcement learning, decision theory,
game theory, Bayesian statistics, control systems, operations research, search,
and software testing. Few agent builders can be expected to know all of it,
recognize which assumptions apply, implement the methods correctly, and test
them against their workload.

**Project 008 is the knowledge foundation. Agent Brain Platform is the
translation and execution layer that turns that knowledge into working agent
logic.**

---

## One Line

**Agent Brain Platform turns mathematical decision-making methods into
composable, testable, and executable runtime logic for AI agents—without
requiring users to master the underlying mathematics or train a model.**

---

## The Core Insight

An LLM can be excellent at:

- Understanding unstructured information
- Generating hypotheses, plans, queries, and candidate actions
- Explaining and critiquing possible answers
- Translating between natural language and structured representations

An LLM should not automatically be trusted to control:

- Exploration versus exploitation
- Budget allocation
- Search depth
- Tool, model, or agent routing
- Evidence accumulation
- Confidence updates
- Stopping and escalation
- Hard safety constraints

These are not merely prompting problems. They are **decision problems**.

The platform places explicit, inspectable control policies around the LLM.
The LLM remains a generator, interpreter, and sometimes an evaluator. The
agent's allocation and stopping logic can be mathematical, rule-based,
learned, or hybrid—and can be tested independently of the model.

```text
Environment / Task
        ↓ observations
┌──────────────────────────────────────────────┐
│ Agent Decision Architecture                  │
│                                              │
│ State → Belief → Plan → Select → Act         │
│              ↑          ↓                    │
│        Evaluate ← Observe ← Feedback         │
│              ↓                               │
│      Continue / Stop / Escalate              │
└──────────────────────────────────────────────┘
        ↓ candidate generation and interpretation
       LLM + tools + memory + external systems
```

The model is a component inside the decision loop, not the entire loop.

---

## The Problem

Agent creation today is divided between two incomplete approaches.

### Prompt-led agents

The prompt says things such as "reason carefully," "search until confident,"
"choose the best tool," or "verify your work." The model must infer the
control policy from prose on every run.

Common consequences:

- Unbounded or inconsistent execution
- Different effort on identical tasks
- Tunnel vision after an early success
- Arbitrary retry and stopping behavior
- Unexplained tool and model selection
- No explicit cost-quality trade-off
- Weak auditability

### Workflow-led agents

Visual builders and graph frameworks make execution explicit, but most nodes
represent API calls, tools, prompts, agents, or deterministic branches. The
builder still has to invent the decision logic connecting them.

Neither approach answers:

> Given this decision, environment, feedback signal, and cost constraint,
> which control methods are compatible—and which one works on this workload?

---

## The Product

The user describes what the agent must accomplish. The platform:

1. Identifies the agent's **decision points**
2. Converts each decision point into a structured **decision contract**
3. Eliminates techniques whose assumptions do not fit
4. Suggests simple and sophisticated candidate policies
5. Tests candidates using simulation, historical traces, benchmark tasks,
   shadow execution, or controlled live traffic
6. Compares the selected architecture with a matched generic-agent baseline
   on quality, cost, latency, stability, safety, and explainability
7. Rejects dangerous or uneconomic configurations
8. Generates an executable **Agent Decision Architecture**
9. Monitors deployed policies for drift and changed assumptions

The user experiences a guided game of blocks. Under the interface is a
measurement and compilation system, not a catalogue of algorithm names.

---

## Decision Blocks

A block represents a question the agent must answer. A mathematical technique
is one possible implementation of that block.

| Decision block | Question | Candidate implementations |
|---|---|---|
| **State** | What information must be carried forward? | Markov state, belief state, structured summary, finite-state model |
| **Belief updater** | How should new evidence change confidence? | Bayesian update, likelihood aggregation, confidence calibration |
| **Router** | Which model, tool, source, or agent should act? | Rules, classifier, contextual bandit, cost-aware routing |
| **Explorer** | Which possibility should be investigated next? | Round-robin, ε-greedy, UCB, Thompson Sampling, value of information |
| **Planner** | Which action sequence or branch should be expanded? | Checklist, beam search, A*, MDP policy, MCTS, Minimax |
| **Budget allocator** | Where should time, calls, and tokens be spent? | Fixed allocation, knapsack/optimization, bandit allocation, adaptive budget |
| **Critic / evaluator** | How good is this state, plan, or result? | Tests, rules, heuristic value, LLM judge, learned critic, multi-objective score |
| **Stopper** | Continue, retry, answer, escalate, or abandon? | Fixed limit, threshold, sequential test, marginal value, optimal stopping |
| **Scheduler** | Which task should execute next? | Priority rule, queueing policy, utility scheduling, hierarchical controller |
| **Memory policy** | What should be stored, recalled, compressed, or forgotten? | Recency, relevance, episodic policy, information-value policy |
| **Constraint** | Which actions are forbidden or require approval? | Hard rules, constrained optimization, policy engine, human gate |
| **Coordinator** | How do multiple agents share work and resolve conflict? | Central planner, auction, voting, Minimax/game model, hierarchical policy |

Not every agent needs every block. Not every block needs an advanced
algorithm. A valid result is:

> Your existing deterministic rule is simpler, cheaper, and statistically
> indistinguishable from the sophisticated alternatives.

---

## The Decision Contract

Every decision point is described in a standard form before techniques are
suggested:

| Field | Meaning |
|---|---|
| **State/context** | Information available when the decision is made |
| **Actions** | The choices the controller may select |
| **Outcome** | What happens after an action |
| **Feedback/reward** | How success, information gain, or cost is observed |
| **Dynamics** | Stationary, depleting, drifting, stateful, or adversarial |
| **Horizon** | One-shot, episodic, or continuous |
| **Observability** | Full, partial, delayed, noisy, or absent feedback |
| **Constraints** | Safety, cost, latency, fairness, and approval limits |
| **Objective** | Quality, utility, risk, cost, or a multi-objective trade-off |
| **Baseline** | The current or simplest acceptable implementation |

This prevents fashionable but invalid recommendations:

- MDPs require meaningful state, actions, transitions, and objectives.
- Bandits require repeated choices and observable feedback.
- Minimax requires a genuinely adversarial or worst-case structure.
- Bayesian updates require defensible likelihoods or calibrated evidence.
- MCTS requires a generative transition model and a value or reward signal.
- Optimal stopping requires a measurable value of continuing versus stopping.

The platform should explain why a technique is eligible or ineligible in plain
language.

---

## A Block Is an Executable Contract

A visual node is not enough. Every registered block contains:

- A typed input and output interface
- The decision assumptions it requires
- Compatible and incompatible neighboring blocks
- A simple reference baseline
- One or more executable policy implementations
- A cost model
- Required feedback and observability
- Unit, simulation, replay, and live-test adapters
- Metrics and failure conditions
- Evidence supporting its use
- Export adapters for supported runtimes

Illustrative output:

```yaml
decision_point: next_investigation
question: "Which hypothesis should the agent investigate next?"

state:
  evidence: Evidence[]
  hypotheses: Hypothesis[]
  remaining_budget: integer

actions:
  - inspect_source
  - run_test
  - search_reference
  - request_clarification

candidates:
  - policy: explore_then_commit
  - policy: thompson_sampling
    reward: information_gain
  - policy: contextual_ucb
    context: [confidence, estimated_cost, reversibility]

stop:
  when_expected_information_value_below: 0.05
  hard_budget: 20

constraints:
  - no_production_writes
  - require_approval_for_irreversible_action

selected_after_test:
  policy: explore_then_commit
  reason: "No material quality gain from bandit policies at this budget."
```

The selected architecture is evidence-backed and executable. It is not a star
rating or a decorative blueprint.

---

## Worked Example — Coding Agent

A bug-fixing agent contains multiple decisions currently hidden inside its
prompt:

| Agent moment | Decision block | Possible method |
|---|---|---|
| Several bug hypotheses exist | Explorer / belief updater | Bayesian belief + value of information |
| Many files may contain the cause | Router | Contextual bandit or relevance-cost rule |
| Several repair paths are possible | Planner | Beam search or MCTS |
| Tests vary in cost and diagnostic value | Scheduler | Risk- and information-aware ordering |
| Candidate patches need comparison | Critic | Tests + static analysis + rubric evaluator |
| More investigation may not be worth it | Stopper | Expected marginal value below cost |
| A patch could be destructive | Constraint | Hard approval and rollback rules |

The LLM reads code, generates hypotheses, explains failures, and writes
patches. The decision architecture controls which hypothesis receives effort,
which test runs next, when evidence is sufficient, and what actions require
approval.

The same block vocabulary can describe research, security, relationship
discovery, business analysis, document review, operations, evaluation, and
multi-agent systems.

---

## User Experience

### 1. Describe

The user states the agent goal, current workflow, available actions, observable
outcomes, and constraints.

### 2. Discover decisions

The platform proposes decision points such as routing, planning, belief update,
budget allocation, evaluation, and stopping. The user confirms or edits them.

### 3. Complete missing assumptions

Instead of asking "Do you want UCB or Thompson Sampling?", the platform asks:

- Does the same choice occur repeatedly?
- Is feedback available after each choice?
- Can rewards change or deplete over time?
- Is the environment adversarial?
- What is the maximum cost and latency?
- What constitutes success or useful information?
- Can historical executions be replayed?

### 4. Assemble candidates

The platform creates a candidate set containing:

- The current implementation
- The simplest reasonable baseline
- Compatible mathematical policies
- A safe fallback

### 5. Test

Candidates run through the strongest available evidence mode:

```text
Static validation
      ↓
Simulation
      ↓
Historical replay
      ↓
Benchmark tasks
      ↓
Shadow execution
      ↓
Controlled live experiment
```

Higher modes provide stronger evidence. The platform must display which mode
supports each conclusion.

### 6. Compare and reject

Results report:

- Task success and quality
- Total LLM/tool cost
- Latency
- Variance and reproducibility
- Safety violations
- Explanation quality
- Sensitivity to workload changes

The platform emphasizes disqualification and material improvement, not false
precision between nearly tied techniques.

### 7. Export and monitor

The decision architecture is generated as config and code for an existing
runtime. Production traces feed back into evaluation, recalibration, and drift
detection.

---

## Platform Architecture

### Layer 1 — Knowledge Foundation

Project 008-derived knowledge represented as structured technique records:

- Decision served
- Mathematical assumptions
- Required signals
- Strengths and failure modes
- Cost and complexity
- Compatibility
- Evidence and references
- Reference implementation

### Layer 2 — Decision Mapper

Converts an agent goal or existing implementation into explicit decision
contracts. Human confirmation remains required where the environment cannot be
inferred safely.

### Layer 3 — Block Registry and Compatibility Engine

Provides typed decision blocks and candidate implementations. It rejects
invalid combinations and missing prerequisites before execution.

### Layer 4 — Evidence Engine

Runs baselines and candidate policies through simulation, replay, benchmarks,
shadow traffic, or live experiments. It measures quality-cost-latency trade-offs
and uncertainty.

### Layer 5 — Decision Architecture Compiler

Generates a portable policy specification plus runnable adapters for existing
agent frameworks. Existing standards should be extended or targeted where
possible rather than replaced.

### Layer 6 — Runtime Observation

Captures decisions, context, selected actions, outcomes, costs, and policy
versions. Detects drift and identifies when the original recommendation no
longer applies.

### Layer 7 — Visual Workbench

The game-of-blocks interface for assembling, explaining, testing, and comparing
decision architectures. It is an interface over the evidence engine—not the
first product milestone.

---

## What It Is Not

- **Not a model-training platform.** Inference-time control is the initial
  focus; model-weight training is optional future scope.
- **Not an RL gym.** Simulation is used to test policies, not as the entire
  product.
- **Not merely a workflow canvas.** Workflow nodes execute work; decision
  blocks determine how choices are made.
- **Not a prompt builder.** Prompts may implement parts of a block, but they
  are not the architecture.
- **Not a universal claim that advanced mathematics is always better.**
- **Not a replacement for LangGraph, AutoGen, n8n, DSPy, or agent runtimes.**
  It supplies tested decision logic that they can execute.
- **Not an algorithm encyclopaedia.** Project 008 may contain broad knowledge;
  the product exposes only techniques with implementable contracts and
  evidence.

---

## Market Landscape — July 2026

The market is active. The opportunity is not based on claiming that nobody
uses mathematical control around agents. Many teams do—but the capabilities
are fragmented.

### 1. Workflow and visual agent builders

n8n, LangGraph, AutoGen, Flowise, Langflow, Camunda, and similar products
compose tools, prompts, agents, process steps, rules, and APIs. Camunda, for
example, offers composable deterministic decision and human-task blocks.

**Overlap:** visual composition, rules, runtime execution.

**Difference:** they do not provide a cross-disciplinary catalogue of agent
decision contracts, select compatible mathematical controllers, and
empirically compare those controllers against the user's workload.

### 2. Agent program optimization

[DSPy](https://dspy.ai/) compiles and optimizes LM programs against metrics.
[Microsoft Foundry Agent Optimizer](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/optimize-agent-targets)
optimizes instructions, skills, tools, and model selection. [Amazon Bedrock
AgentCore optimization](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/optimization.html)
uses recommendations and A/B tests to improve agent configurations.

**Overlap:** measurement-driven improvement and configuration search.

**Difference:** these systems primarily optimize prompts, examples, tools,
models, or existing agent configurations. Agent Brain Platform begins by
formalizing the decision itself, mapping it to named mathematical policy
families, validating assumptions, and generating explicit controller logic.

### 3. Automated agent architecture search

[Automated Design of Agentic Systems
(ADAS)](https://arxiv.org/abs/2408.08435) treats agent design as a search
problem and uses a meta-agent to invent and combine agent programs.
Subsequent agent-architecture-search research expands this direction.

**Overlap:** discovering better agent designs through evaluation.

**Difference:** ADAS searches open-ended code architectures. This platform is
practitioner-guided, assumption-aware, explainable, and grounded in reusable
decision blocks from decision theory, RL, game theory, statistics, control, and
operations research. ADAS is a possible future search backend, not proof that
the practitioner layer already exists.

### 4. Technique-specific frameworks

- [LiTS](https://pypi.org/project/lits-llm/) provides modular LLM inference
  through tree search.
- [Meta Pearl](https://github.com/facebookresearch/Pearl) provides
  production-oriented reinforcement-learning and contextual-bandit components.
- [LLMRouter](https://github.com/ulab-uiuc/LLMRouter) provides many model
  routing methods, evaluation, production serving, and a visual routing UI.
- [AB-RAG](https://arxiv.org/abs/2606.29090) and related adaptive-retrieval
  work implement confidence-aware retrieval budgets and stopping.

**Overlap:** real mathematical controllers at inference time.

**Difference:** each focuses on a technique family or decision point. The
proposed platform operates one level above: identify the decision, select and
test compatible families, combine them into an architecture, and export to
specialized runtimes where appropriate.

### 5. Evaluation, governance, and runtime policy

[Microsoft ASSERT and Agent Control
Specification](https://devblogs.microsoft.com/foundry/build-2026-open-trust-stack-ai-agents/)
connect policy-driven evaluation with portable runtime controls. Products such
as Runplane and traditional policy engines enforce allow/block/approval
decisions at action boundaries.

**Overlap:** evaluation, portable controls, runtime enforcement, and evidence.
**Difference:** the primary focus is governance, safety, compliance, and
authorization. Those become the Constraint block here; the broader platform
also covers exploration, planning, belief, routing, allocation, evaluation,
memory, scheduling, and stopping.

### 6. Agent representation standards

[Oracle Open Agent
Specification](https://oracle.github.io/agent-spec/development/) represents
agents, potentially cyclic flows, state, branching, components, and executable
behavior. [Open Agent Format](https://openagentformat.com/spec.html) packages
agent instructions and composition.

**Overlap:** portable representation and runtime interoperability.

**Difference:** these are candidate output targets. They do not themselves
provide the full decision-discovery, mathematical selection, compatibility,
testing, and evidence loop.

### Market conclusion

The reviewed market contains every major ingredient, and several adjacent
platforms are moving toward optimization and runtime control. Therefore:

- **This is not an empty market.**
- **The underlying inference-control pattern is already validated.**
- **Point solutions will continue to become stronger.**
- **The exact integrated practitioner workflow has not been found in the
  reviewed products:** decision discovery → formal decision contract →
  mathematical block selection → compatibility checking → empirical comparison
  → executable architecture → production drift monitoring.

That integration is the opportunity. It is also the claim that must be
continually re-checked as the market changes.

---

## Differentiation and Moat

Algorithms such as UCB, Thompson Sampling, MCTS, Minimax, and Bayesian updating
are public knowledge. A visual canvas is reproducible. Neither is a moat.

Potential defensibility comes from:

1. **Decision ontology** — a precise mapping from real agent problems to
   executable decision contracts
2. **Compatibility knowledge** — machine-checkable assumptions, requirements,
   conflicts, and failure conditions
3. **Empirical evidence** — performance distributions across real workloads,
   budgets, models, and environments
4. **Baselines and benchmarks** — trusted comparisons that include simple
   policies and total cost
5. **Runtime integrations** — deployable adapters across agent frameworks
6. **Production feedback** — data showing transfer, drift, and when a policy
   stops being appropriate
7. **Explanations** — defensible reasons for selection and rejection that an
   engineer or auditor can inspect

The long-term asset is the evidence connecting workload characteristics to
policy outcomes.

---

## Initial Wedge

Do not begin by implementing every block.

Start with **budgeted investigation and retrieval**, because it contains
several visible decisions:

- Which branch or hypothesis to inspect next
- Which source or tool to use
- How much budget to allocate
- When to stop

Initial target:

> An SDK and evaluation workbench that instruments an existing search,
> research, debugging, or retrieval agent; compares its current loop with
> alternative selection and stopping policies; and generates the best
> evidence-supported controller.

This wedge tests the entire product thesis while keeping the technique and
integration surface manageable.

The first real proof is a paired agent comparison, not an answer-key exercise.
A normal general-purpose sub-agent and a configured agent receive the same
model, task, tools, data, and budget. The configured arm differs only through
explicit decision contracts and selected control blocks. Project 008 is an
available knowledge environment, not presumed complete ground truth. When its
evidence is incomplete, correct behavior may be a bounded partial answer,
abstention, escalation, or—if both arms are allowed—the selective use of an
external search tool.

---

## Execution Plan

### Phase 0 — Correct the evidence

- **POC 2b completed — PASS under locked rules.** It used randomized branch
  labels, a valid stationary control, pre-registered analysis, and an honestly
  named baseline. See [`poc2b/README.md`](./poc2b/README.md).
- **POC 3 completed — FAIL under locked rules.** Controls and parameter-family
  sensitivity survived, but only one fixed policy met the persistence rule and
  the simple baseline was viable in 4/9 settings rather than the required 6/9.
  Broad fixed-policy robustness is therefore unsupported. See
  [`poc3/README.md`](./poc3/README.md).
- **POC 4 completed — FAIL under locked rules.** A true-regime oracle had a
  small material advantage, but a cheap detector operated at chance and
  reduced reward by 2.43% versus the strong fixed default. See
  [`poc4/README.md`](./poc4/README.md).
- **POC 5 completed — PASS under locked rules.** Stopping is a second decision
  block with workload-dependent viability: four fixed rules moved between
  viable and disqualified, while full continuation, half budget, trend
  stopping, and confidence stopping were appropriate in different workloads.
  See [`poc5/README.md`](./poc5/README.md).
- **POC 6a completed — FAIL under locked rules, with partial transfer.** The
  six-policy ranking transferred from simulation to the historical Project 008
  corpus with Spearman correlation 0.943, and Round Robin was disqualified for
  concentrated retrieval. No policy swung across concentrated and diffuse
  strata, so workload-stratum recommendation was not supported. See
  [`poc6a/README.md`](./poc6a/README.md).
- **POC 6b search-task fixture preparation completed and reframed.** A 30-case
  draft contains realistic questions, candidate evidence, hard negatives, and
  deliberate coverage gaps. Project 008 is not presumed complete ground truth;
  the cases now feed the paired search-agent instrumentation and blinded
  evidence assessment. See [`poc6b/README.md`](./poc6b/README.md).
- **POC 6c diagnostic comparative benchmark completed.** It directly compares a normal
  sub-agent with a configured Agent Brain agent under matched tasks, tools,
  data, models, and budgets. Search/research is the first workload; code
  development, code review, and code testing form the transfer ladder. Effects
  are reported per workload and converted into transaction economics rather
  than advertised as one universal uplift percentage. See
  [`poc6c/PLAN.md`](./poc6c/PLAN.md).
- The first search controller was rejected by two blind diagnostic evaluators:
  it saved reads but lost evidence coverage. A quality-protected replacement
  received the stronger search signal; code development and code testing also
  favored their configured candidates, while code review retained the generic
  baseline. No confirmation or product uplift is claimed from these seen pilots.
- Keep the product build gate closed. The untouched search confirmation set,
  rubric, and draft preregistration now exist; activate them only after every
  recorded readiness gate is satisfied. Use that evidence—not the diagnostic
  pilots—to decide whether the narrowed "measure and calibrate" thesis clears
  a product build gate.
- Treat original POC 2 as historical exploratory evidence superseded by POC 2b

### Phase 1 — Decision Contract and Three Blocks

Implement:

- Explorer
- Stopper
- Critic/reward

Deliver:

- Typed schemas
- Compatibility validation
- Simple baselines
- Reference policies
- Simulation and replay interfaces

### Phase 2 — One Paired Real-Agent Wedge

Instrument a real search/research agent first. Compare:

- a normal general-purpose sub-agent; and
- the same model and harness with an Agent Brain decision architecture.

Hold the task, tools, data, context, and budget constant. Demonstrate one of
two honest outcomes on untouched confirmation tasks:

- the configured controller materially improves quality, cost, latency,
  safety, or stability; or
- the platform correctly concludes that the normal/simple loop is preferable.

Both validate the evaluation product. Neither alone validates a universal
recommender.

### Phase 2b — Workload Transfer and Transaction Economics

After the search wedge produces a credible paired harness, test the same
decision-contract method on:

- code development;
- code review;
- code testing.

Each workload receives its own fixtures, outcome checks, selected
configuration, and effect size. Report quality uplift, success change, failure
reduction, cost, latency, human correction time, and variance. Convert only
confirmed workload-specific effects into incremental value per transaction,
break-even volume, payback period, and low/base/high monthly or annual
scenarios. Portfolio value is the sum across the actual workload mix; one
headline percentage must not be extrapolated across unrelated task types.

### Phase 3 — Evidence Engine

- Historical replay
- Paired candidate comparison
- Cost and latency accounting
- Confidence intervals and practical-effect thresholds
- Shadow execution
- Policy/version tracking

### Phase 4 — Architecture Compiler

Generate:

- Portable decision-policy config
- Python reference implementation
- Adapter for one established agent runtime
- Trace schema for decisions and outcomes

### Phase 5 — Guided Workbench

Build the dropdown/block experience only after the block contracts, tests, and
compiler work. Every UI recommendation must link to its assumptions and
evidence.

### Phase 6 — Expand the Registry

Add routing, planning, belief update, scheduling, memory, constraints, and
multi-agent coordination based on demonstrated user demand and measurable
workloads.

---

## Research and Build Gates

The project proceeds only if the following survive testing:

1. **Decision identifiability** — can a real agent's important decisions be
   represented without forcing every problem into an MDP or bandit?
2. **Observable value** — can success, information gain, or cost be measured
   well enough to compare policies?
3. **Transfer** — do simulation and replay results predict live behavior?
4. **Material effect** — do policy choices cause practically meaningful
   differences after total cost is included?
5. **Second-decision generality** — does the method work beyond branch
   selection?
6. **Integration cost** — is instrumentation cheaper than manually solving the
   decision?
7. **User comprehension** — can non-specialists understand and correctly act
   on the platform's explanation?
8. **Matched-baseline advantage** — with the model, task, tools, data, and
   budget fixed, does the configured agent improve a meaningful outcome or
   correctly retain the generic baseline?
9. **Economic scaling** — do confirmed per-transaction effects survive
   configuration, evaluation, monitoring, and human-review costs at realistic
   workload volumes?

If recommendations require live measurement for every workload, the product
becomes a measurement and optimization service rather than a static
recommender. That is an acceptable pivot and may be the stronger business.

---

## Principal Risks

1. **Reward ambiguity**

   Many knowledge-work agents lack immediate ground truth. LLM judges may
   introduce bias into the policy they evaluate.

2. **Hidden environment structure**

   The user may not know whether rewards are stationary, depleting, delayed, or
   adversarial. Goal text alone cannot safely infer this.

3. **Combinatorial architecture space**

   Blocks interact. Independent local choices may produce a poor global agent.

4. **Evaluation cost**

   Testing several architectures may cost more than the expected improvement.

5. **Runtime overhead**

   A mathematically elegant controller can lose economically if it adds too
   many LLM calls or too much latency.

6. **Point-solution competition**

   Routing, retrieval, search, governance, and optimizer products may expand
   into adjacent decisions faster than a horizontal platform can mature.

7. **Improving model control**

   Better models may reduce the value of external policies for simple tasks.
   The remaining value would be cost control, auditability, smaller-model
   performance, and high-stakes reproducibility.

8. **Abstraction without evidence**

   A registry and canvas can look complete while providing no trustworthy
   recommendation. The evidence engine must precede the broad UI.

---

## Product Principles

1. **Decision first, algorithm second**
2. **Assumptions are explicit and machine-checkable**
3. **Every advanced policy competes against a simple baseline**
4. **Total cost and latency count as outcomes**
5. **Disqualify harmful choices before ranking close alternatives**
6. **No false precision**
7. **Evidence strength is visible**
8. **The platform may recommend no change**
9. **Exports target existing runtimes**
10. **Production behavior feeds back into the recommendation**
11. **Agent comparisons hold model, task, tools, data, and budget constant**
12. **Economic extrapolation is workload-specific and volume-weighted**

---

## North Star

> An engineer describes what an agent must decide. The platform turns that
> problem into explicit decision contracts, proposes compatible mathematical
> control blocks, tests them against the real workload, and generates bounded,
> reproducible, explainable agent logic—without requiring the engineer to
> master every underlying field.

---

## References

### Agent architecture and automated design

- [CoALA: Cognitive Architectures for Language
  Agents](https://arxiv.org/abs/2309.02427)
- [Automated Design of Agentic
  Systems](https://arxiv.org/abs/2408.08435)
- [AI Agent Systems: Architectures, Applications, and
  Evaluation](https://arxiv.org/abs/2601.01743)

### Control techniques around LLMs

- [Language Agent Tree Search](https://arxiv.org/abs/2310.04406)
- [LiTS: A Modular Framework for LLM Tree
  Search](https://arxiv.org/abs/2603.00631)
- [Query Decomposition for RAG: Balancing
  Exploration–Exploitation](https://arxiv.org/abs/2510.18633)
- [MAB-DQA](https://arxiv.org/abs/2604.08952)
- [AB-RAG: Adaptive Budgeted
  Retrieval-Augmented Generation](https://arxiv.org/abs/2606.29090)
- [A Component-Based Survey of LLM and Multi-Armed Bandit
  Interactions](https://arxiv.org/abs/2601.12945)

### Adjacent products and frameworks

- [DSPy](https://dspy.ai/)
- [Microsoft Foundry Agent
  Optimizer](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/optimize-agent-targets)
- [Amazon Bedrock AgentCore
  Optimization](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/optimization.html)
- [Meta Pearl](https://github.com/facebookresearch/Pearl)
- [LLMRouter](https://github.com/ulab-uiuc/LLMRouter)
- [Microsoft ASSERT and Agent Control
  Specification](https://devblogs.microsoft.com/foundry/build-2026-open-trust-stack-ai-agents/)

### Representation and interoperability

- [Oracle Open Agent Specification](https://oracle.github.io/agent-spec/development/)
- [Open Agent Format](https://openagentformat.com/spec.html)
