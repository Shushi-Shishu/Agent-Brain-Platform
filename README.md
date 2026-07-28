# Agent Brain Platform

> **An IDE for agent cognitive architecture — not the execution layer, but the brain behind it.**

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

## Build Phases

| Phase | What | Status |
|---|---|---|
| **0** | Vision + project definition | ✅ Done |
| **1** | Technique Registry schema + seed data | 🔄 Next |
| **2** | Component Canvas — visual slot configuration | ⬜ |
| **3** | Goal Encoder — scoring + auto-ranking engine | ⬜ |
| **4** | Draft Generator — blueprint + JSON config export | ⬜ |
| **5** | Code Scaffold Generator — Python agent skeleton | ⬜ |
| **6** | Runtime Bridge — connect blueprint to n8n / LangGraph | ⬜ |

---

## Project Structure

```
Agent-Brain-Platform/
├── README.md          ← This file — project definition
├── VISION.md          ← Full vision document
├── POC.html           ← Interactive single-file POC (open in browser)
├── registry/          ← Technique Registry (Phase 1)
├── canvas/            ← Canvas UI (Phase 2)
├── encoder/           ← Goal Encoder engine (Phase 3)
├── generator/         ← Blueprint + scaffold generator (Phase 4-5)
└── bridge/            ← Runtime bridge (Phase 6)
```

---

## POC

[`POC.html`](./POC.html) — open directly in any browser, no server needed.

Demonstrates:
- All 11 cognitive slots on a visual canvas
- Technique library with ★ rankings per slot
- Goal text → auto-encode dimensions → re-rank techniques
- Multi-technique selection per slot
- Generate Cognitive Blueprint modal with JSON export and Markdown download

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
