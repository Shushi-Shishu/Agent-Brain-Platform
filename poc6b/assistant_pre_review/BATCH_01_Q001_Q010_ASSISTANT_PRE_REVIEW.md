# POC 6b — Batch 1 Assistant Pre-Review

> **This is not human approval and not ground truth.**
>
> This file is a separate evidence-based recommendation for Q001–Q010. It
> does not change `cases.draft.json`, the human review worksheet, candidate
> labels, required-answer fields, or approval checkboxes. A human reviewer
> must verify the source passages and make the final decisions.

## Summary

| Case | Question | Behavior | Candidate set | Main issue |
|---|---|---|---|---|
| Q001 | Production agent architecture | Answer | Incomplete | Two hard negatives are useful evidence; key production-design notes are missing |
| Q002 | Demo-to-production gap | Answer | Nearly complete | One hard negative is relevant; Gibbs sampling is correctly irrelevant |
| Q003 | RL with LLMs and agents | Answer | Incomplete | Strong RL-for-LLM evidence is missing |
| Q004 | Evaluation before and after launch | Answer | Nearly complete | Post-launch note is a strong positive, not a hard negative |
| Q005 | Context management | Answer | Incomplete | Durable-memory evidence should be added |
| Q006 | Multi-agent versus single-agent | Answer | Incomplete | Two proposed positives are irrelevant and the best candidate is marked negative |
| Q007 | MCP purpose, design, and security | Answer | Nearly complete | Container security is only adjacent; a production security note should be added |
| Q008 | Maintainable agent architecture | Answer | Incomplete | `build-systems-not-code` is the strongest positive but is marked negative |
| Q009 | Agent tracing and measurement | Answer | Incomplete | The best observability notes were not retrieved |
| Q010 | Human approval and escalation | Answer | Complete enough after relabeling | The ETL escalation note is a strong positive, not a hard negative |

All ten questions appear realistic and should have `answer` behavior. None is
ready for human approval without completing the required answer points,
unsupported claims, candidate corrections, and passage verification below.

## Q001 — Production agent architecture

**Assistant recommendation:** realistic; expected behavior `answer`.

| Draft role | Candidate | Suggested relevance | Evidence quality | Reason |
|---|---|---|---|---|
| Positive | `AI & SDLC/2026-07-20 - Tokyo Executive Forum 2026 - A Leaders Guide to Cloud-Native Application Modernization.md` | Relevant | Usable | Supports observability, identity, governance, and the POC-to-production transition |
| Positive | `AI & SDLC/2026-06-29 - frontier-results-on-device-rl-nabors-arize.md` | Partially relevant | Usable | Supports cost-aware model sizing and deploying smaller specialized models, but not the complete architecture |
| Positive | `raw/2026-07-25 - why-agentic-systems-need-ontologies.md` | Partially relevant | Weak | Ontologies may help structure domain knowledge, but they are not a general reliability requirement |
| Hard negative | `AI & SDLC/2026-05-22 - lobster-trap-openclaw-in-containers.md` | Relevant | Strong | Direct support for isolation, reproducibility, portability, secrets, and secure deployment |
| Hard negative | `raw/2026-07-17 - learn-ai-engineering-in-2026.md` | Partially relevant | Usable | Supports reusable skills, project rules, approval workflows, and retrieval, but does not cover the full production stack |

**Candidate set:** incomplete. Add and passage-check:

- `AI & SDLC/2026-07-15 - ai-system-design-from-idea-to-production.md`
- `AI & SDLC/2026-07-21 - Build Evals That Actually Matter - Nick Ung Lyft.md`
- `AI & SDLC/2026-07-05 - the-missing-layer-after-launch.md`

**Proposed required answer points:**

1. Define explicit tool contracts, permissions, workflow states, stopping
   conditions, retry behavior, and error paths.
2. Isolate execution; manage identities and secrets; apply least privilege to
   every tool and data source.
3. Make runs observable and auditable, with pre-release evaluations and
   production feedback tied to real outcomes.
4. Separate volatile prompts/models from durable execution and state so
   components can change without rewriting the entire system.
5. Control latency and cost through routing, caching, and appropriately sized
   models; require human authority for high-impact actions.

**Unsupported claims to forbid:**

- One framework, prompt, or ontology makes a system production-ready.
- Containers alone solve agent security.
- Larger models automatically produce more reliable systems.
- Passing an offline benchmark proves production reliability.

## Q002 — Demo-to-production gap

**Assistant recommendation:** realistic; expected behavior `answer`.

| Draft role | Candidate | Suggested relevance | Evidence quality | Reason |
|---|---|---|---|---|
| Positive | `raw/2026-06-17 - ai-engineering-in-41-minutes-from-demo-to-production.md` | Relevant | Strong | Directly addresses the transition from a working demo to an engineered production system |
| Positive | `AI & SDLC/2026-07-15 - ai-system-design-from-idea-to-production.md` | Relevant | Strong | Covers requirements, architecture, safety, evaluation, and deployment concerns |
| Positive | `AI & SDLC/2026-05-14 - the-complete-guide-to-hybrid-search-in-rag.md` | Partially relevant | Usable | A useful production retrieval example, but not a general demo-to-production answer |
| Hard negative | `AI & SDLC/2026-07-16 - this-completely-changes-the-way-we-build-production-ai-agents-vercel-eve.md` | Relevant | Usable | Provides concrete production primitives: durable sessions, sandboxing, approval, and evaluation gates |
| Hard negative | `Mathematics/2022-05-31 - markov-networks-2-gibbs-sampling-stanford-cs221.md` | Irrelevant | Strong as negative | Mathematical sampling content does not answer the engineering question |

**Candidate set:** nearly complete. The current sources can support a gold
answer, though `AI & SDLC/2026-07-05 - the-missing-layer-after-launch.md`
would strengthen post-launch coverage.

**Proposed required answer points:**

1. Convert the demo goal into explicit user outcomes, requirements, failure
   modes, and acceptance tests.
2. Engineer reliable data/retrieval pipelines, schemas, state, retries,
   security boundaries, and fallbacks.
3. Establish representative evaluations and launch gates rather than relying
   on a few successful demonstrations.
4. Instrument production behavior, user corrections, latency, cost, and
   failures; feed those observations back into the evaluation set.
5. Plan for scale, model/provider changes, and operational ownership.

**Unsupported claims to forbid:**

- A successful demo or high benchmark score is evidence of production
  readiness.
- A framework removes the need for reliability, security, and operations.
- Retrieval accuracy alone defines total system quality.

## Q003 — Reinforcement learning with LLMs and agents

**Assistant recommendation:** realistic; expected behavior `answer`.

| Draft role | Candidate | Suggested relevance | Evidence quality | Reason |
|---|---|---|---|---|
| Positive | `AI & SDLC/2015-05-13 - rl-course-by-david-silver-lecture-1-introduction-to-reinforcement-learning.md` | Relevant | Strong foundation | Supports states, actions, rewards, policies, returns, and the agent-environment loop, but predates LLM applications |
| Positive | `AI & SDLC/2026-07-18-natural-language-autoencoders-llm-activations.md` | Partially relevant | Weak | Contains a narrow RL optimization use, not a general explanation of RL for agents |
| Positive | `AI & SDLC/2026-07-17 - special-topics-in-kernels-rl-reward-hacking-in-agents.md` | Relevant | Strong | Direct evidence for reward hacking, evaluator gaming, and misaligned optimization |
| Hard negative | `raw/2026-07-18 - using-large-language-models.md` | Partially relevant | Weak | LLM background may provide context but does not supply the required RL treatment |
| Hard negative | `AI & SDLC/2026-07-21 - Build Evals That Actually Matter - Nick Ung Lyft.md` | Partially relevant | Usable | Useful for reward/evaluator design and business-aligned feedback, but is not primarily an RL note |

**Candidate set:** incomplete. Add and passage-check:

- `raw/2026-07-18 - reinforcement-learning-build-your-own-llm-workshop-22.md`

The added note should provide direct LLM-training evidence so the answer does
not incorrectly generalize from classical RL or a narrow activation experiment.

**Proposed required answer points:**

1. Explain the MDP/RL abstraction: state or observation, action, reward,
   transition, policy, and long-term return.
2. Distinguish training-time uses such as preference/reward optimization from
   inference-time agent orchestration and tool selection.
3. Explain where feedback can come from: humans, verifiable outcomes,
   simulators, rules, or learned reward models.
4. Cover limitations: reward hacking, evaluator bias, sparse or delayed
   feedback, sample cost, non-stationarity, and simulation-to-reality gaps.
5. State that deterministic workflows, search, planning, bandits, and RL are
   different tools even when a product loosely calls all of them “learning.”

**Unsupported claims to forbid:**

- RL automatically makes an agent aligned, reliable, or autonomous.
- A simulator or reward model perfectly represents human intent.
- Every adaptive routing or selection mechanism is full RL.
- Reward improvement alone proves real-world task improvement.

## Q004 — Evaluation before and after production

**Assistant recommendation:** realistic; expected behavior `answer`.

| Draft role | Candidate | Suggested relevance | Evidence quality | Reason |
|---|---|---|---|---|
| Positive | `AI & SDLC/2026-07-15 - ai-system-design-from-idea-to-production.md` | Relevant | Strong | Supports system-level evaluation, safety, and production gates |
| Positive | `AI & SDLC/2026-07-15 - teaching-coding-agents-to-do-spreadsheets.md` | Relevant | Strong case study | Shows baseline creation, benchmark construction, and evaluation infrastructure in a concrete domain |
| Positive | `AI & SDLC/2026-07-21 - Build Evals That Actually Matter - Nick Ung Lyft.md` | Relevant | Strong | Directly supports outcome-based eval design and representative cases |
| Hard negative | `AI & SDLC/2026-07-11 - stop-ai-agent-hallucinations-5-techniques.md` | Partially relevant | Usable | Useful for one failure category, but too narrow for the whole evaluation lifecycle |
| Hard negative | `AI & SDLC/2026-07-05 - the-missing-layer-after-launch.md` | Relevant | Strong | Direct post-launch evidence; should not remain a negative |

**Candidate set:** complete enough after relabeling.

**Proposed required answer points:**

1. Define target user/business outcomes and a failure taxonomy before choosing
   metrics.
2. Build representative offline cases, including happy paths, edge cases,
   adversarial cases, and examples derived from real user behavior.
3. Record a baseline, component metrics, end-to-end quality, and explicit
   launch thresholds.
4. After launch, trace real runs and measure task success, corrections,
   frustration, safety, latency, cost, and drift.
5. Turn production failures into regression cases and calibrate model-based
   judges against human or deterministic checks.

**Unsupported claims to forbid:**

- One aggregate score is sufficient for every product.
- Synthetic tests alone represent production behavior.
- Evaluation ends at launch.
- An LLM judge is ground truth or needs no calibration.

## Q005 — Context management

**Assistant recommendation:** realistic; expected behavior `answer`.

| Draft role | Candidate | Suggested relevance | Evidence quality | Reason |
|---|---|---|---|---|
| Positive | `AI & SDLC/2026-05-06 - full-walkthrough-writing-using-skills.md` | Relevant | Usable | Supports progressive disclosure and avoiding bloated global instructions |
| Positive | `raw/how-to-never-hit-your-claude-session-limit-again.md` | Relevant | Strong | Directly covers context limits, compaction/context rot, clearing, and delegation |
| Positive | `AI & SDLC/2026-05-01 - build-and-sell-claude-code-operating-systems.md` | Partially relevant | Weak | Provides workspace organization ideas but limited direct evidence for context management |
| Hard negative | `raw/2026-04-05-andrej-karpathy-10x-claude-code.md` | Partially relevant | Usable | Persistent structured notes are relevant, though the evidence is not a full memory design |
| Hard negative | `AI & SDLC/2026-07-10 - i-rebuilt-hermess-best-feature-in-claude-code.md` | Relevant | Strong | Directly distinguishes short-term and permanent memory and discusses bounded memory injection |

**Candidate set:** incomplete. Add and passage-check:

- `AI & SDLC/2026-05-09 - how-to-architect-agentic-memory-systems.md`

**Proposed required answer points:**

1. Separate immediate working context from durable memory and the complete
   external event/history store.
2. Retrieve and inject only task-relevant information; use progressive
   disclosure rather than loading every rule and note on every turn.
3. Summarize or compact old context with provenance and retain the full source
   outside the model window for later recovery.
4. Clear, fork, or delegate work when accumulated context begins to degrade
   instruction following.
5. Measure retrieval quality, stale-memory errors, token cost, and the effect
   of compaction on downstream behavior.

**Unsupported claims to forbid:**

- More context or unlimited memory always improves performance.
- Compaction is lossless.
- A fixed character or token cap is universally optimal.
- Saving every interaction necessarily improves the agent.

## Q006 — Multi-agent versus single-agent design

**Assistant recommendation:** realistic; expected behavior `answer`.

| Draft role | Candidate | Suggested relevance | Evidence quality | Reason |
|---|---|---|---|---|
| Positive | `AI & SDLC/2026-04-19 - the-future-of-mcp.md` | Irrelevant | Strong as negative | Primarily about MCP protocol evolution, discovery, transports, and enterprise identity |
| Positive | `AI & SDLC/2026-07-15 - the-factory-that-dreams-39-ai-agents-no-framework.md` | Relevant | Usable case study | Demonstrates role boundaries and a large multi-agent deployment, but does not establish general selection criteria |
| Positive | `AI & SDLC/2026-07-08 - running-a-chess-youtube-channel-entirely-by-ai.md` | Irrelevant | Strong as negative | A content-automation case does not provide enough architecture evidence to decide single versus multi-agent |
| Hard negative | `AI & SDLC/2026-05-14 - i-built-a-yc-pitch-deck-in-5-minutes-with-one-claude-command.md` | Irrelevant | Strong as negative | One-command slide generation is not evidence for multi-agent architecture selection |
| Hard negative | `AI & SDLC/2026-07-17 - l8-principals-agentic-engineering-setup.md` | Relevant | Strong | Direct evidence about coordinator/delegation patterns and the cognitive and token costs of parallel sessions |

**Candidate set:** incomplete. Add and passage-check:

- `AI & SDLC/2026-07-18-the-multi-agent-architecture-that-actually-ships.md`
- `AI & SDLC/building-distributed-multi-agent-systems-notes.md`

**Proposed required answer points:**

1. Prefer one agent when a single context, tool set, and control loop can solve
   the task; it minimizes coordination, latency, cost, and failure surfaces.
2. Multi-agent design is justified when responsibilities require distinct
   expertise or permissions, independent scaling, genuine parallel work, or
   adversarial review.
3. Split work only across clear boundaries with typed handoffs, shared state,
   role limits, and an orchestrator or explicit workflow.
4. Account for coordination overhead, context loss, conflicting decisions,
   duplicate work, cascading failure, and increased evaluation complexity.
5. Compare the multi-agent system with a strong single-agent baseline using
   quality, cost, latency, reliability, and human attention.

**Unsupported claims to forbid:**

- More agents automatically improve quality or speed.
- Named personas alone create useful specialization.
- Parallel execution is always appropriate.
- A multi-agent case study establishes a universal architecture.

## Q007 — Model Context Protocol

**Assistant recommendation:** realistic; expected behavior `answer`.

| Draft role | Candidate | Suggested relevance | Evidence quality | Reason |
|---|---|---|---|---|
| Positive | `AI & SDLC/2026-07-01 - what-is-an-ai-agent-how-i-automated-my-daily-task-with-ai.md` | Relevant | Strong | Clearly describes MCP as a standard connector and covers granular read/write permissions |
| Positive | `AI & SDLC/2026-06-01 - this-will-save-you-16-hours-all-18-courses-ranked.md` | Relevant | Usable | Supports tools, resources, prompts, servers/clients, enterprise databases, transports, and IAM limitations |
| Positive | `AI & SDLC/2026-07-05 - mcp-apps-primitives-discovery-and-the-future-of-software.md` | Relevant | Strong | Supports discovery, sandboxed UI, capability negotiation, data redaction, and compatibility concerns |
| Hard negative | `AI & SDLC/2026-05-22 - lobster-trap-openclaw-in-containers.md` | Partially relevant | Usable | Adjacent evidence for isolation, secrets, and approved MCP baselines, but not MCP protocol design itself |
| Hard negative | `AI & SDLC/AI_Images_Videos_Welch_Labs.md` | Irrelevant | Strong as negative | Diffusion and multimodal model content does not answer the MCP question |

**Candidate set:** nearly complete. Add and passage-check:

- `AI & SDLC/2026-07-15 - agentic-ai-system-design-complete-roadmap.md`

**Proposed required answer points:**

1. MCP standardizes how model applications discover and interact with external
   tools, resources, prompts, and data through client/server interfaces.
2. Tool schemas should be task-oriented, bounded, typed, and understandable to
   models; a one-to-one wrapper around every REST endpoint can create tool and
   context bloat.
3. Use capability negotiation, progressive discovery, timeouts, structured
   errors, and transport designs suitable for scale.
4. Treat servers, returned data, and tool descriptions as crossing trust
   boundaries; defend against prompt injection, data exfiltration, and
   malicious or over-broad tools.
5. Apply authentication, authorization, least privilege, read/write separation,
   consent/approval for side effects, secret isolation, audit logs, and data
   minimization/redaction.

**Unsupported claims to forbid:**

- MCP makes any connected tool safe.
- MCP itself determines business permissions or correct tool behavior.
- Every API should be exposed directly as an MCP tool.
- An installed MCP server should automatically receive full user authority.

## Q008 — Maintainable agent-system architecture

**Assistant recommendation:** realistic; expected behavior `answer`.

| Draft role | Candidate | Suggested relevance | Evidence quality | Reason |
|---|---|---|---|---|
| Positive | `AI & SDLC/2026-06-25 - the-log-is-the-agent.md` | Relevant | Strong | Supports durable event logs, disposable runtimes, recoverability, portability, and auditability |
| Positive | `raw/2026-07-18 - tdd-ddd-ground-up.md` | Relevant | Strong | Supports incremental design, tests, refactoring, vertical slices, and domain boundaries |
| Positive | `raw/2026-07-18 - Master-Software-Architecture-From-Simplicity-to-Complexity.md` | Relevant | Strong | Supports evolutionary architecture, delaying complexity, and context-dependent tradeoffs |
| Hard negative | `AI & SDLC/2026-06-25 - build-systems-not-code.md` | Relevant | Strong | The strongest direct answer: separation of concerns, deterministic code versus model judgment, schemas, idempotency, permissions, and documentation |
| Hard negative | `AI & SDLC/2026-06-24 - how-to-build-a-company-os-in-claude-code.md` | Partially relevant | Weak | Task ontologies and repository transparency help organization, but it is not primarily a software architecture source |

**Candidate set:** incomplete. Add and passage-check:

- `AI & SDLC/2026-07-21 - your-agent-architecture-has-a-half-life-of-six-months.md`

**Proposed required answer points:**

1. Separate deterministic calculations and policy checks from probabilistic
   model judgment.
2. Decompose the system by responsibility and domain; use small interfaces,
   typed contracts, and explicit tool/permission boundaries.
3. Keep execution state and event history durable, observable, resumable, and
   independent of an ephemeral model runtime.
4. Decouple fast-changing prompts, models, and tool adapters from stable
   orchestration and business logic.
5. Evolve complexity only when real architectural drivers justify it; use
   tests, refactoring, documentation, and idempotent side effects.

**Unsupported claims to forbid:**

- Microservices or multi-agent designs are inherently more maintainable.
- An append-only log captures or reverses every external side effect.
- Typed JSON proves semantic correctness.
- A perfect architecture can be selected before requirements and usage are
  known.

## Q009 — Tracing and measuring inconsistent agents

**Assistant recommendation:** realistic; expected behavior `answer`.

| Draft role | Candidate | Suggested relevance | Evidence quality | Reason |
|---|---|---|---|---|
| Positive | `AI & SDLC/2026-05-22 - lobster-trap-openclaw-in-containers.md` | Irrelevant | Strong as negative | The supplied passage concerns container overhead, not tracing inconsistent behavior |
| Positive | `AI & SDLC/2026-07-21 - your-agent-architecture-has-a-half-life-of-six-months.md` | Relevant | Strong | Directly calls for end-to-end traces of triggers, model calls, tools, database errors, permissions, and outcomes |
| Positive | `raw/2026-05-20-build-a-proactive-agent-workflow-with-claude-code.md` | Partially relevant | Usable | Supports visibility, steerability, and resumability, but supplies limited metric detail |
| Hard negative | `raw/2026-04-21 - quicksilver-alchemy-and-faradays-motor-part-1.md` | Irrelevant | Strong as negative | The word “agent” is incidental; the note is unrelated |
| Hard negative | `AI & SDLC/2026-07-14 - dont-ship-skills-without-evals.md` | Partially relevant | Usable | Relevant to nondeterminism, regressions, token cost, and skill triggering, but not a complete observability source |

**Candidate set:** incomplete. Add and passage-check:

- `AI & SDLC/2026-05-07 - Everything-You-Need-To-Know-About-Agent-Observability.md`
- `AI & SDLC/2026-07-14 - product-launch-agent-observability-optimization-devcon-6.md`
- `AI & SDLC/2026-06-30 - how-to-build-a-continuous-evaluation-pipeline-for-multi-agent-systems-with-gemini.md`

**Proposed required answer points:**

1. Capture a correlated end-to-end run trace: trigger/user input, retrieved
   context, prompt and configuration versions, model calls, tool inputs and
   outputs, state transitions, retries, errors, permissions, and final outcome.
2. Record model/tool/provider versions, sampling settings, timestamps, run
   identifiers, and provenance so inconsistent runs can be compared.
3. Measure task success and business outcomes alongside error rate, latency,
   token/cost use, tool success, retry/loop rates, and human interventions.
4. Add semantic signals such as frustration, hallucination, refusal, unsafe
   behavior, and repeated self-correction; do not rely only on infrastructure
   metrics.
5. Compare successful and failed trajectories, reproduce against versioned
   cases, and turn production incidents into regression tests.

**Unsupported claims to forbid:**

- Raw chain-of-thought is required or should be stored as the debugging source
  of truth.
- Logs alone establish causality.
- Self-reported agent success is reliable without external outcome checks.
- Average latency or error rate alone explains behavioral inconsistency.

## Q010 — Human approval, correction, and escalation

**Assistant recommendation:** realistic; expected behavior `answer`.

| Draft role | Candidate | Suggested relevance | Evidence quality | Reason |
|---|---|---|---|---|
| Positive | `AI & SDLC/2026-07-16 - this-completely-changes-the-way-we-build-production-ai-agents-vercel-eve.md` | Relevant | Strong | Direct support for approval gates around risky database operations |
| Positive | `AI & SDLC/2026-07-11 - from-writing-code-to-designing-systems-how-the-developer-role-is-changing.md` | Relevant | Strong | Supports guardrails and final human review while warning about review fatigue |
| Positive | `AI & SDLC/2026-07-14 - product-launch-agent-infrastructure-layer-orchestrator.md` | Relevant | Strong | Supports durable waiting, resumable approvals, state tracking, and side-effect safety |
| Hard negative | `AI & SDLC/2026-07-16 - simon-willison-in-conversation-with-cat-wu-thariq-shihipar-anthropic.md` | Partially relevant | Usable | Supports reducing human review for proven low-risk outer loops while retaining ownership of critical core areas |
| Hard negative | `AI & SDLC/2026-06-29 - using-rl-agent-to-detect-and-remediate-etl-pipeline-failures.md` | Relevant | Strong | Directly treats escalation as a successful action when confidence or authority bounds are exceeded |

**Candidate set:** complete enough after relabeling. The following note could
strengthen the gold answer but is not essential:

- `AI & SDLC/2026-07-15 - agentic-ai-system-design-complete-roadmap.md`

**Proposed required answer points:**

1. Gate irreversible, expensive, external, safety-critical, privacy-sensitive,
   legal, financial, or high-blast-radius actions before execution.
2. Use a proposal → deterministic policy/business-rule check → human
   authorization sequence for high-risk writes.
3. Treat uncertainty, low confidence, policy conflict, missing information,
   repeated failure, and exceeded authority as valid escalation outcomes.
4. Insert correction points at useful intermediate artifacts and before final
   publication or commitment, not after hidden side effects have occurred.
5. Make approval risk-tiered; automate proven low-risk work to prevent review
   fatigue, while logging decisions and durably suspending/resuming workflows.

**Unsupported claims to forbid:**

- Every agent step needs manual approval.
- Evals make approval unnecessary for high-impact actions.
- Human-in-the-loop alone fixes unsafe architecture.
- Model confidence alone is sufficient to decide whether to act.

## Recommended human-review order

1. Verify the exact passages for all candidates marked `Relevant`.
2. Add the missing notes listed for Q001, Q003, Q005, Q006, Q008, and Q009.
3. Decide whether each proposed required point has at least one exact source
   passage.
4. Copy only human-confirmed decisions into the formal Batch 1 worksheet and
   `cases.draft.json`.
5. Approve a case only after relevance labels, evidence quality, required
   points, unsupported claims, reviewer identity, and review date are complete.
