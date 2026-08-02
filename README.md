# Agent Brain Platform

> **A measurement and compilation layer for explicit, testable agent decision
> logic.**

**Current direction:** the early canvas, star ratings, and static
goal-to-technique ranking below are historical POC concepts. Testing showed
that policy value is workload- and budget-dependent, cheap workload detection
can fail, and a simple baseline is often sufficient. The authoritative current
direction is in [`VISION.md`](./VISION.md), the evidence is in
[`RESEARCH.md`](./RESEARCH.md), and the diagnostic comparative benchmark is
documented in [`poc6c/RESULTS.md`](./poc6c/RESULTS.md). Its untouched
confirmation stage is prepared but not activated because the recorded
readiness gates are unmet.

---

## What We Are Building

Most agent platforms today (n8n, Flowise, LangGraph, AutoGen) solve **orchestration**: how agents connect to tools, APIs, and each other.

**Agent Brain Platform** solves the layer above — **cognition**: how an agent thinks, decides, plans, explores, and learns.

We are building a **visual, theory-grounded platform** where a practitioner:

1. Defines a goal
2. Assembles the agent's cognitive architecture from composable blocks
3. Each block is filled with ranked techniques drawn from RL, game theory, Bayesian reasoning, and LLM methods
4. The platform validates the composition and generates a **Cognitive Blueprint** — a complete specification of how the agent thinks, exportable as config and code scaffold

---

## The Problem We Solve

| Today | Agent Brain Platform |
|---|---|
| Engineer manually selects RL vs LLM vs rules — no guidance | Goal-aware technique ranking per cognitive slot |
| No standard vocabulary for agent cognition | 11 standardized cognitive component slots |
| RL, MDP, Minimax, MCTS scattered across separate libraries | Unified technique registry — any framework, composable |
| No visual tool for cognitive architecture design | Visual canvas — drag, configure, validate |
| Architecture lives in code, not in a shareable specification | Generates Cognitive Blueprint as config + markdown + code |

---

## What It Is NOT

- Not a workflow engine (no API connectors, no triggers)
- Not an LLM wrapper or prompt builder
- Not a replacement for LangChain / n8n — it sits **upstream**, defining the brain those platforms execute

---

## The 11 Cognitive Component Slots

Every agent brain is assembled from these slots:

| # | Slot | Purpose |
|---|---|---|
| 1 | **Perception** | Receive + structure world input |
| 2 | **State Encoder** | Compress history → compact Markov state |
| 3 | **Memory** | Store and retrieve knowledge across time |
| 4 | **Reasoning Engine** | Core decision-making brain |
| 5 | **Planning** | Decompose goals → action sequences |
| 6 | **Value / Critic** | Evaluate state and action desirability |
| 7 | **Exploration Strategy** | Balance known vs unknown search space |
| 8 | **Action Layer** | Execute decisions on the world |
| 9 | **Feedback / Learning** | Update from outcomes |
| 10 | **Safety / Guardrails** | Constrain harmful behavior |
| 11 | **Orchestration** | Coordinate all components |

Each slot is filled with one or more techniques from the **Technique Registry**.

---

## The Technique Registry

A structured library of cognitive techniques — each with metadata:

- Which slot(s) it fills
- What goal dimensions it suits (adversarial, real-time, long horizon, data-scarce, multi-agent, interpretable, partial observability)
- Compatibility with other techniques
- Complexity and interpretability rating

Current registry spans:

| Framework | Techniques |
|---|---|
| Reinforcement Learning | Q-Learning, Policy Gradient, Actor-Critic, PPO, TD Learning, REINFORCE |
| Planning & Search | MDP, MCTS, Minimax, A*, Hierarchical RL, LLM Planner |
| Exploration | ε-Greedy, UCB, Thompson Sampling, Curiosity-Driven, Boltzmann |
| Memory | Vector DB, Episodic Buffer, Working Memory, Knowledge Graph |
| Reasoning | LLM, Chain-of-Thought, Bayesian Inference, MDP Policy, Rule Engine |
| Perception | RAG, API Polling, Document Parser, Sensor Fusion |
| Safety | Constitutional AI, Reward Shaping, Policy Constraints, Output Filtering |
| Orchestration | Single-Agent Loop, Multi-Agent, Hierarchical, ReAct Loop |

**The registry is extensible** — new techniques register in without changing the platform.

---

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│  1. Define Goal                                          │
│     "Negotiate vendor contracts in adversarial settings" │
└────────────────────┬────────────────────────────────────┘
                     │ Goal Encoder scores + ranks techniques
┌────────────────────▼────────────────────────────────────┐
│  2. Component Canvas                                     │
│                                                          │
│  [Perception]──▶[State Encoder]──▶[Reasoning Engine]    │
│                       │                  │               │
│                  [Memory]           [Planning]           │
│                                         │                │
│                                  [Exploration]           │
│                                         │                │
│                                    [Action]              │
│                                         │                │
│                  [Safety]◀──[Feedback]──▶[Orchestration] │
└────────────────────┬────────────────────────────────────┘
                     │ Validate + Score
┌────────────────────▼────────────────────────────────────┐
│  3. Cognitive Blueprint Output                           │
│                                                          │
│  Perception:      RAG + API Polling                      │
│  State Encoder:   Markov State                           │
│  Reasoning:       LLM + MDP Policy                       │
│  Planning:        Minimax ★★★★★  MCTS ★★★★☆            │
│  Exploration:     Thompson Sampling ★★★★★               │
│  ...                                                     │
│                                                          │
│  Status: ✅ Valid  │  Export: JSON · Markdown · Scaffold │
└─────────────────────────────────────────────────────────┘
```

---

## Current Research-Gated Phases

| Phase | What | Status |
|---|---|---|
| **0** | Simulation, sensitivity, stopping, and historical transfer | ✅ Done |
| **1** | Matched generic-agent versus configured-agent search diagnostic | ✅ Done |
| **2** | Diagnostic transfer to code development, review, and testing | ✅ Done |
| **3** | Confirmation and transaction economics | 🟨 Prepared; readiness-gated |
| **4** | Decision contracts, three proven blocks, and trace schema | ⬜ |
| **5** | Architecture compiler and one runtime adapter | ⬜ |
| **6** | Guided visual workbench | ⬜ |

## Visual Tooling (POC Build — Phases 1–6)

The following tooling was built as a visual POC layer. It implements the original canvas vision and can serve as a front-end reference once the research gates above are cleared.

| Phase | Deliverable | Status |
|---|---|---|
| **1** | Technique Registry schema + seed data | ✅ Done |
| **2** | Component Canvas — visual slot configuration | ✅ Done |
| **3** | Goal Encoder — scoring + auto-ranking engine | ✅ Done |
| **4** | Blueprint Generator — per-slot rationale + export | ✅ Done |
| **5** | Python Scaffold Generator — agent.py skeleton | ✅ Done |
| **6** | Runtime Bridge — n8n · LangGraph · SAP BTP | ✅ Done |

---

## Project Structure

```
Agent-Brain-Platform/
├── README.md                  ← This file — project definition
├── VISION.md                  ← Full vision document
├── POC.html                   ← Interactive single-file POC (open in browser)
├── registry/                  ← Phase 1 ✅ Technique Registry
│   ├── schema.md              ← Data model specification
│   ├── techniques.json        ← 51 seed technique records
│   └── index.html             ← Standalone browser UI for the registry
├── canvas/                    ← Phase 2 ✅ Component Canvas
│   └── index.html             ← Visual slot-configuration canvas
├── encoder/                   ← Phase 3 ✅ Goal Encoder
│   └── index.html             ← NL goal → dimension scoring → ranked recommendations
├── generator/                 ← Phase 4+5 ✅ Blueprint Generator + Python Scaffold
│   └── index.html             ← Cognitive Blueprint viewer + Python agent.py generator
└── bridge/                    ← Phase 6 ✅ Runtime Bridge
    └── index.html             ← n8n workflow · LangGraph graph · SAP BTP · Deploy guide
```

## End-to-End Flow

```
Goal Encoder  →  Canvas  →  Full Blueprint  →  Runtime Bridge
(encoder/)      (canvas/)   (generator/)        (bridge/)
     ↓               ↓            ↓                  ↓
NL goal         Configure     Download:          Export to:
→ dim detect    11 slots      • Markdown BP      • n8n workflow.json
→ ranked recs   → picker      • JSON config      • LangGraph graph.py
→ Send →        → Send →      • agent.py         • SAP AI Core / Joule
```

---

## Historical Visual POC

[`POC.html`](./POC.html) — open directly in any browser, no server needed.

The original visual POC demonstrates:
- All 11 cognitive slots on a visual canvas
- Technique library with ★ rankings per slot
- Goal text → auto-encode dimensions → re-rank techniques
- Multi-technique selection per slot
- Generate Cognitive Blueprint modal with JSON export and Markdown download

Its star rankings and static recommendation behavior are not supported by the
later experiments and must not be treated as the current product specification.

---

## Competitive Landscape

| Platform | Layer | RL/MDP as first-class? |
|---|---|---|
| n8n, Make | Workflow automation | ✗ |
| Flowise, Langflow | LLM orchestration | ✗ |
| AutoGen Studio | Multi-agent orchestration | ✗ |
| OpenAI Agent Builder | LLM agent builder | ✗ |
| LangChain / CrewAI | Code framework | ✗ |
| **Agent Brain Platform** | **Cognitive architecture** | **✅** |

---

## North Star

> Any practitioner — whether they know RL theory or just know their business problem — should be able to compose a theoretically sound agent brain in under 30 minutes, with the platform guiding every choice.

---

*Project started: 2026-07-28*
