# Technique Registry — Schema v2.0

**Agent Brain Platform** | Updated: 2026-08-04

---

## What changed in v2

Schema v1 modelled cognitive *slots* (perception, planning, etc.) and scored
techniques by static goal dimensions. POC 2–6c showed the platform's value is
in **decision-block testing and disqualification**, not static slot rankings.
v2 replaces slot/goal-boost scoring with decision-block mapping, executable
assumptions, empirical evidence grades, and failure modes.

v1 records are preserved and back-ported with v2 fields set where derivable;
fields that cannot be derived are set to `null` and marked `"legacy": true`.

---

## Technique Record Schema v2

```json
{
  "id":           "string — unique kebab-case identifier",
  "name":         "string — short display name",
  "full_name":    "string — expanded name",
  "schema_version": "integer — 1 = legacy v1, 2 = full v2",
  "legacy":       "boolean — true if back-ported from v1 without full curation",

  "classification": {
    "type": "string — one of: executable-policy | decision-interface | evaluation-method | runtime-integration | background-math",
    "decision_blocks": ["array of block IDs this technique can implement"],
    "framework": "string — RL | MDP | bandit | game-theory | Bayesian | LLM | symbolic | control | multi-agent | safety | statistics"
  },

  "description":  "string — 1–2 sentence plain-English description",
  "theory_note":  "string | null — key theoretical property or formula",

  "assumptions": {
    "required_state":       "string — what state/context must exist at decision time",
    "required_feedback":    "string — what signal must be observable after each action",
    "required_observability": "string — full | partial | delayed | noisy | none",
    "dynamics":             "string — stationary | depleting | drifting | adversarial | unknown",
    "horizon":              "string — one-shot | episodic | continuous",
    "min_repeat_decisions": "integer | null — minimum number of repeated decisions before the technique is useful"
  },

  "baseline": {
    "id":          "string — id of the simplest acceptable alternative",
    "description": "string — one line describing what the baseline does"
  },

  "evidence": {
    "grade":   "string — A | B | C | D | X",
    "source":  "string — empirical | literature | simulation | expert | none",
    "summary": "string — one sentence on what the evidence shows",
    "refs":    ["array of citation strings or arXiv IDs"]
  },

  "failure_modes": [
    "string — each entry is one concrete way this technique fails or becomes harmful"
  ],

  "incompatible_when": [
    "string — each entry is a condition under which this technique must not be used"
  ],

  "compatible_blocks": ["array of decision-block IDs that compose well with this technique"],

  "cost_model": {
    "calls_per_decision": "integer | null — LLM or tool calls consumed per decision",
    "latency_class":      "string — sub-ms | ms | seconds | minutes | null",
    "notes":              "string | null"
  },

  "reference_implementation": "string | null — pointer to poc/ or external repo",

  "example_use_case": "string",

  "_v1_compat": {
    "slot":            ["legacy slot IDs"],
    "base_rank":       "integer | null",
    "goal_boosts":     "object | null",
    "complexity":      "integer | null",
    "interpretability":"integer | null",
    "sample_efficiency":"integer | null",
    "tags":            ["array"],
    "conflicts_with":  ["array"],
    "pairs_well_with": ["array"],
    "requires":        ["array"],
    "references":      ["array"]
  }
}
```

---

## Evidence Grade Definitions

| Grade | Meaning |
|---|---|
| **A** | Confirmed on untouched tasks with auditable model/cost telemetry, pre-registered pass/fail rule, and ≥80% power |
| **B** | Diagnostic empirical result (this project's POCs) — pre-registered but telemetry gaps or seen tasks |
| **C** | Literature result — peer-reviewed, applicable to agent decision context |
| **D** | Simulation result only — not yet transferred to a live LLM agent |
| **X** | No empirical evidence; expert judgment or theoretical only |

---

## Decision Block IDs

| Block ID          | Question answered |
|---|---|
| `explorer`        | Which branch, hypothesis, or source to investigate next? |
| `stopper`         | Continue, retry, answer, escalate, or abandon? |
| `critic`          | How good is this state, plan, or result? |
| `router`          | Which model, tool, source, or agent should act? |
| `budget-allocator`| Where should time, calls, and tokens be spent? |
| `planner`         | Which action sequence or branch to expand? |
| `belief-updater`  | How should new evidence change confidence? |
| `scheduler`       | Which task should execute next? |
| `memory-policy`   | What to store, recall, compress, or forget? |
| `constraint`      | Which actions are forbidden or need approval? |
| `coordinator`     | How do multiple agents share work and resolve conflict? |
| `state`           | What information must be carried forward? |

---

## Classification Types

| Type | Meaning |
|---|---|
| `executable-policy` | Can be directly instantiated as runtime controller logic |
| `decision-interface` | Defines a state/contract structure used by policies |
| `evaluation-method` | Used to score or compare; not a controller itself |
| `runtime-integration` | Connects to an external framework or tool |
| `background-math` | Theoretical foundation; not directly executable |

---

## Files

| File | Contents |
|---|---|
| `schema.md` | This document — data model spec v2 |
| `techniques.json` | All technique records (v1 back-ported + v2 curated) |
| `validate.py` | Schema validator + duplicate checker |
| `test_registry.py` | Automated tests for schema conformance and evidence claims |
| `index.html` | Browser UI (v1 visual; v2 fields not yet surfaced in UI) |
