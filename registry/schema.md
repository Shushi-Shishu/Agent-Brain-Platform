# Technique Registry — Schema v1.0

**Phase 1 deliverable** | Agent Brain Platform

---

## Purpose

The Technique Registry is the single source of truth for every cognitive technique available to the platform. Every technique carries structured metadata so the Goal Encoder can score and rank it, the Canvas can display it, and the Draft Generator can validate and export it.

The registry is **append-only and extensible** — new techniques register in without any platform code changes.

---

## Technique Record Schema

```json
{
  "id":              "string  — unique kebab-case identifier, e.g. 'mcts'",
  "name":            "string  — display name, e.g. 'MCTS'",
  "full_name":       "string  — full expanded name, e.g. 'Monte Carlo Tree Search'",
  "slot":            ["array of slot IDs this technique can fill"],
  "framework":       "string  — parent framework: RL | MDP | game-theory | Bayesian | LLM | symbolic | control | multi-agent | safety",
  "description":     "string  — 1-2 sentence plain-English description",
  "theory_note":     "string  — optional brief theoretical grounding / key property",
  "tags":            ["array of lowercase keyword tags"],
  "complexity":      "integer 1-5  — implementation complexity (1=trivial, 5=research-level)",
  "interpretability":"integer 1-5  — how explainable the technique's decisions are (1=black-box, 5=fully auditable)",
  "sample_efficiency":"integer 1-5 — data efficiency (1=data-hungry, 5=learns from very few samples)",
  "base_rank":       "integer 1-5  — default quality/applicability rank before goal scoring",
  "goal_boosts": {
    "adversarial":      "integer — rank delta when environment is adversarial",
    "realtime":         "integer — rank delta when low-latency response required",
    "long_horizon":     "integer — rank delta for long multi-step tasks",
    "data_scarce":      "integer — rank delta when training data is limited",
    "multi_agent":      "integer — rank delta for multi-agent coordination tasks",
    "interpretable":    "integer — rank delta when auditability is required",
    "partial_obs":      "integer — rank delta for partially observable environments"
  },
  "conflicts_with":  ["array of technique IDs that are incompatible in the same slot"],
  "pairs_well_with": ["array of technique IDs that synergize across slots"],
  "requires":        ["array of technique IDs that must also be present (hard dependencies)"],
  "example_use_case":"string  — one concrete real-world example",
  "references":      ["array of key papers / resources"]
}
```

---

## Slot IDs

| Slot ID         | Display Name          | Required? |
|---|---|---|
| `perception`    | Perception            | Yes |
| `stateEncoder`  | State Encoder         | Yes |
| `memory`        | Memory                | Yes |
| `reasoning`     | Reasoning Engine      | Yes |
| `planning`      | Planning              | Yes |
| `value`         | Value / Critic        | Optional |
| `exploration`   | Exploration Strategy  | Optional |
| `action`        | Action Layer          | Yes |
| `feedback`      | Feedback / Learning   | Yes |
| `safety`        | Safety / Guardrails   | Optional |
| `orchestration` | Orchestration         | Yes |

---

## Framework Values

| Value         | Covers |
|---|---|
| `RL`          | Reinforcement Learning algorithms |
| `MDP`         | Markov Decision Process formalisms |
| `game-theory` | Adversarial / cooperative game theoretic methods |
| `Bayesian`    | Probabilistic inference and belief-state methods |
| `LLM`         | Large language model-based techniques |
| `symbolic`    | Rule-based, logic, and deterministic systems |
| `control`     | Control theory, PID, feedback systems |
| `multi-agent` | Coordination and communication protocols |
| `safety`      | Alignment, constraint, and guardrail methods |

---

## Goal Dimension Definitions

| Dimension       | True When... |
|---|---|
| `adversarial`   | Agent must compete against or defend against rational opponents |
| `realtime`      | Response latency is a hard constraint (sub-second) |
| `long_horizon`  | Task spans many steps or long time horizon |
| `data_scarce`   | Limited training data; must generalize from few examples |
| `multi_agent`   | Multiple agents cooperating or competing |
| `interpretable` | Decisions must be auditable / explainable to humans |
| `partial_obs`   | Agent cannot observe full world state |

---

## Scoring Formula

```
effective_rank(technique, goal_dims) = min(5, base_rank + sum(goal_boosts[dim] for dim if dim is active))
```

Techniques are sorted descending by `effective_rank` within each slot.

---

## Files

| File              | Contents |
|---|---|
| `schema.md`       | This document — data model specification |
| `techniques.json` | All technique records conforming to this schema |
| `index.html`      | Standalone browser UI for exploring the registry |
