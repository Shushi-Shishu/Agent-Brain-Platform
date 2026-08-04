"""
One-time migration: upgrades techniques.json to v2 format.

- Adds schema_version, legacy, classification, assumptions, evidence,
  failure_modes, incompatible_when, compatible_blocks, cost_model,
  reference_implementation to all existing v1 records.
- Prepends 7 fully-curated v2 records.
- Leaves all existing v1 fields intact (index.html backward-compat).

Run once:  python migrate_v2.py
"""

import json
from pathlib import Path

REGISTRY = Path(__file__).parent / "techniques.json"

V2_RECORDS = [
    {
        "id": "explore-then-commit",
        "name": "Explore-Then-Commit",
        "full_name": "Explore-Then-Commit (ETC) Bandit Policy",
        "schema_version": 2,
        "legacy": False,
        "classification": {
            "type": "executable-policy",
            "decision_blocks": ["explorer"],
            "framework": "bandit"
        },
        "description": (
            "Allocates a fixed exploration budget to pull every arm a set number "
            "of times, then commits permanently to the arm with the highest observed "
            "mean reward."
        ),
        "theory_note": (
            "Simple two-phase policy: explore phase pulls each arm ⌊budget/K⌋ times; "
            "commit phase always selects argmax of empirical means. "
            "Optimal in stationary settings when budget/K is moderate."
        ),
        "assumptions": {
            "required_state": "Count of pulls and cumulative reward per arm",
            "required_feedback": "Scalar reward observable after each arm pull",
            "required_observability": "full",
            "dynamics": "stationary",
            "horizon": "episodic",
            "min_repeat_decisions": 2
        },
        "baseline": {
            "id": "explore-then-commit",
            "description": "This IS the simple baseline — compare against it before using UCB or Thompson"
        },
        "evidence": {
            "grade": "B",
            "source": "empirical",
            "summary": (
                "POC 2b: viable in stationary needle, depleting needle, and scarce regimes. "
                "POC 3: viable in 4/9 size-budget settings. "
                "POC 6a: ranked #1 or #2 on Project 008 corpus (ρ=0.943 vs simulation). "
                "Competitive with sophisticated policies in most non-deceptive workloads."
            ),
            "refs": [
                "poc2b/results.json", "poc3/results.json", "poc6a/results.json",
                "Lattimore & Szepesvari 2020 — Bandit Algorithms Ch.6"
            ]
        },
        "failure_modes": [
            "Performs poorly when the best arm is deceptive (high early noise, depleting yield) — UCB or Thompson needed",
            "Exploration budget is wasted if K is large and budget/K < 1",
            "Commit is irreversible — cannot recover from unlucky early pulls",
            "Does not adapt if reward distribution drifts after exploration phase"
        ],
        "incompatible_when": [
            "Deceptive-depleting dynamics where the apparent best arm changes after early pulls",
            "Non-stationary or adversarial environments where reward distributions shift",
            "Horizon is one-shot (single decision) — no exploration phase is possible"
        ],
        "compatible_blocks": ["stopper", "budget-allocator", "critic"],
        "cost_model": {
            "calls_per_decision": 1,
            "latency_class": "sub-ms",
            "notes": "Pure counting logic; zero LLM calls per decision"
        },
        "reference_implementation": "poc2b/policies.py:ExploreThenCommit",
        "example_use_case": (
            "Search agent allocates its first 6 queries evenly across 6 knowledge sources, "
            "then spends remaining budget on whichever source returned the most relevant results."
        ),
        "_v1_compat": {
            "slot": ["exploration"],
            "base_rank": None,
            "goal_boosts": None,
            "complexity": 1,
            "interpretability": 5,
            "sample_efficiency": 3,
            "tags": ["bandit", "simple", "two-phase", "stationary"],
            "conflicts_with": [],
            "pairs_well_with": ["ucb1", "thompson-sampling", "fixed-budget-stopper"],
            "requires": [],
            "references": ["Lattimore & Szepesvari 2020 — Bandit Algorithms"]
        }
    },
    {
        "id": "ucb1",
        "name": "UCB1",
        "full_name": "Upper Confidence Bound 1 (UCB1)",
        "schema_version": 2,
        "legacy": False,
        "classification": {
            "type": "executable-policy",
            "decision_blocks": ["explorer"],
            "framework": "bandit"
        },
        "description": (
            "Selects the arm with the highest upper confidence bound: "
            "mean_reward + c * sqrt(ln(t) / n_pulls). "
            "Optimistic in the face of uncertainty — prefers under-explored arms."
        ),
        "theory_note": (
            "Achieves O(log T) cumulative regret — logarithmically optimal for stationary bandits. "
            "Parameter c=2.0 is the standard choice; tune upward for more exploration."
        ),
        "assumptions": {
            "required_state": "Pull count and cumulative reward per arm; global step counter",
            "required_feedback": "Scalar reward in [0,1] (or normalizable) after each pull",
            "required_observability": "full",
            "dynamics": "stationary",
            "horizon": "episodic",
            "min_repeat_decisions": 2
        },
        "baseline": {
            "id": "explore-then-commit",
            "description": "Explore-Then-Commit: simpler, competitive on non-deceptive workloads"
        },
        "evidence": {
            "grade": "B",
            "source": "empirical",
            "summary": (
                "POC 2b: +13.44% over ETC in deceptive-depleting regime. "
                "POC 3: the only fixed policy meeting the viability-swing rule in 4/9 size-budget settings. "
                "POC 6a: ranked #4 on Project 008 corpus — ETC and EpsilonGreedy outperformed it. "
                "Material advantage is specific to deceptive dynamics; not a universal improvement."
            ),
            "refs": [
                "poc2b/results.json", "poc3/results.json", "poc6a/results.json",
                "Auer et al. 2002 — Finite-time Analysis of the Multiarmed Bandit Problem"
            ]
        },
        "failure_modes": [
            "Disqualified in stationary needle and depleting needle regimes (POC 2b) — worse than ETC",
            "Optimism can over-explore arms with high variance that are actually low-yield",
            "c parameter must be tuned per workload; wrong c causes excessive or insufficient exploration",
            "Reward must be bounded and comparable across arms — fails with raw token counts or unbounded scores"
        ],
        "incompatible_when": [
            "Stationary needle or depleting needle dynamics — ETC performs equally or better at lower cost",
            "Rewards are unbounded or not normalized — confidence bounds become meaningless",
            "Budget/K < 1 — not enough pulls to build meaningful confidence estimates"
        ],
        "compatible_blocks": ["stopper", "budget-allocator", "critic"],
        "cost_model": {
            "calls_per_decision": 1,
            "latency_class": "sub-ms",
            "notes": "Pure arithmetic; zero LLM calls"
        },
        "reference_implementation": "poc2b/policies.py:UCB1",
        "example_use_case": (
            "Research agent balances investigating new hypothesis branches vs. "
            "re-querying the most productive source — UCB selects which source "
            "to query next based on evidence yield so far."
        ),
        "_v1_compat": {
            "slot": ["exploration"],
            "base_rank": 4,
            "goal_boosts": {
                "adversarial": 0, "realtime": 0, "long_horizon": 2,
                "data_scarce": 2, "multi_agent": 0, "interpretable": 3, "partial_obs": 1
            },
            "complexity": 2,
            "interpretability": 4,
            "sample_efficiency": 4,
            "tags": ["bandit", "theory", "optimism", "confidence-bound"],
            "conflicts_with": [],
            "pairs_well_with": ["mcts", "qFunc"],
            "requires": [],
            "references": ["Auer et al. 2002 — Finite-time Analysis of the Multiarmed Bandit Problem"]
        }
    },
    {
        "id": "thompson-sampling",
        "name": "Thompson Sampling",
        "full_name": "Thompson Sampling (Posterior Sampling)",
        "schema_version": 2,
        "legacy": False,
        "classification": {
            "type": "executable-policy",
            "decision_blocks": ["explorer"],
            "framework": "Bayesian"
        },
        "description": (
            "Samples an arm by drawing from the posterior distribution of expected "
            "rewards — Beta(α, β) for Bernoulli rewards. Naturally balances "
            "exploration and exploitation without a tunable parameter."
        ),
        "theory_note": (
            "Bayesian-optimal for the multi-armed bandit in expectation. "
            "Posterior: Beta(α+wins, β+losses). Regret: O(sqrt(KT log K)). "
            "Discounted variant (γ<1) handles non-stationary / depleting dynamics."
        ),
        "assumptions": {
            "required_state": "Alpha and beta counts per arm (or equivalent posterior parameters)",
            "required_feedback": "Binary or normalized reward after each pull",
            "required_observability": "full",
            "dynamics": "stationary",
            "horizon": "episodic",
            "min_repeat_decisions": 2
        },
        "baseline": {
            "id": "explore-then-commit",
            "description": "Explore-Then-Commit: simpler, competitive on non-deceptive workloads"
        },
        "evidence": {
            "grade": "B",
            "source": "empirical",
            "summary": (
                "POC 2b: +44.45% over ETC in rich-depleting regime. "
                "POC 5: used as branch-selection controller; stopping rules tested on Thompson-generated trajectories. "
                "POC 3: viable in 4/9 size-budget settings. "
                "POC 2b disqualified for stationary needle. "
                "Discounted variant (γ=0.9) performs well in depleting workloads."
            ),
            "refs": [
                "poc2b/results.json", "poc3/results.json", "poc5/results.json",
                "Russo et al. 2018 — A Tutorial on Thompson Sampling"
            ]
        },
        "failure_modes": [
            "Disqualified in stationary needle regime (POC 2b) — posterior too diffuse early",
            "Standard Beta posterior assumes stationary rewards — fails for strongly depleting arms without discounting",
            "Parameter-free but prior choice (α0, β0) still matters for small budgets",
            "Stochastic sampling means two identical runs give different decisions — reduces reproducibility"
        ],
        "incompatible_when": [
            "Stationary needle dynamics — ETC matches or beats Thompson at lower complexity",
            "Deterministic reproducibility is required — sampling introduces non-determinism",
            "Rewards are not normalizable to [0,1] without domain knowledge"
        ],
        "compatible_blocks": ["stopper", "budget-allocator", "critic", "belief-updater"],
        "cost_model": {
            "calls_per_decision": 1,
            "latency_class": "sub-ms",
            "notes": "Beta sample is microseconds; zero LLM calls"
        },
        "reference_implementation": "poc2b/policies.py:ThompsonSampling",
        "example_use_case": (
            "Code-testing agent allocates test budget across fault-prone modules — "
            "Thompson Sampling directs more test runs to modules that have exposed "
            "faults, while continuing to probe under-tested areas."
        ),
        "_v1_compat": {
            "slot": ["exploration"],
            "base_rank": 5,
            "goal_boosts": {
                "adversarial": 1, "realtime": 0, "long_horizon": 1,
                "data_scarce": 3, "multi_agent": 1, "interpretable": 1, "partial_obs": 2
            },
            "complexity": 3,
            "interpretability": 3,
            "sample_efficiency": 5,
            "tags": ["Bayesian", "bandit", "posterior-sampling", "optimal"],
            "conflicts_with": [],
            "pairs_well_with": ["belief", "bayes", "ucb1"],
            "requires": [],
            "references": ["Russo et al. 2018 — A Tutorial on Thompson Sampling"]
        }
    },
    {
        "id": "fixed-budget-stopper",
        "name": "Fixed-Budget Stopper",
        "full_name": "Fixed-Budget Stopping Rule",
        "schema_version": 2,
        "legacy": False,
        "classification": {
            "type": "executable-policy",
            "decision_blocks": ["stopper"],
            "framework": "symbolic"
        },
        "description": (
            "Continues exploration until the full allocated budget is exhausted, "
            "then stops and commits to the best option found. No adaptive logic."
        ),
        "theory_note": (
            "Optimal for stationary workloads where evidence continues to accumulate "
            "uniformly throughout the budget. Stopping early in stationary settings "
            "provably discards useful information."
        ),
        "assumptions": {
            "required_state": "Remaining budget counter",
            "required_feedback": "None required — rule is budget-based, not quality-based",
            "required_observability": "none",
            "dynamics": "stationary",
            "horizon": "episodic",
            "min_repeat_decisions": 1
        },
        "baseline": {
            "id": "fixed-budget-stopper",
            "description": "This IS the reference baseline stopper — always test against it first"
        },
        "evidence": {
            "grade": "B",
            "source": "empirical",
            "summary": (
                "POC 5: viable (locked selection) for stationary uniform (28.96 utility, 192 pulls) "
                "and stationary needle (74.05 utility, 192 pulls). "
                "Stopping at half budget in stationary needle produced only 26.09 — a 65% quality loss. "
                "Best stopper for stationary workloads; wrong choice for depleting workloads."
            ),
            "refs": ["poc5/results.json"]
        },
        "failure_modes": [
            "Wastes budget continuing past the point of diminishing returns in depleting workloads",
            "In deceptive-depleting workload produced negative mean utility (-3.16) versus TrendMarginal (+3.08)",
            "No quality protection — stops even if current best answer is poor",
            "Does not detect when the task is unsolvable and early termination would save cost"
        ],
        "incompatible_when": [
            "Depleting dynamics — rewards decrease over time; continuing is actively harmful",
            "Deceptive-depleting dynamics — full budget produces negative utility",
            "Cost per step is high and task value is time-sensitive"
        ],
        "compatible_blocks": ["explorer", "budget-allocator", "critic"],
        "cost_model": {
            "calls_per_decision": 0,
            "latency_class": "sub-ms",
            "notes": "Counter decrement only"
        },
        "reference_implementation": "poc5/experiment.py:FixedBudget",
        "example_use_case": (
            "Search agent over a static document corpus: continue reading and "
            "synthesizing until the 6-note budget is exhausted, then finalize the answer."
        ),
        "_v1_compat": {
            "slot": [],
            "base_rank": None,
            "goal_boosts": None,
            "complexity": 1,
            "interpretability": 5,
            "sample_efficiency": 5,
            "tags": ["stopper", "simple", "stationary", "budget"],
            "conflicts_with": [],
            "pairs_well_with": ["explore-then-commit", "ucb1", "thompson-sampling"],
            "requires": [],
            "references": []
        }
    },
    {
        "id": "trend-marginal-stopper",
        "name": "Trend-Marginal Stopper",
        "full_name": "Trend-Based Marginal Value Stopping Rule",
        "schema_version": 2,
        "legacy": False,
        "classification": {
            "type": "executable-policy",
            "decision_blocks": ["stopper"],
            "framework": "statistics"
        },
        "description": (
            "Stops when the marginal reward trend over a recent window becomes "
            "non-positive — i.e., when the most recent N steps yielded no additional "
            "value compared to the preceding N steps."
        ),
        "theory_note": (
            "TrendMarginal(w1+w2): compare mean reward in last w2 steps vs. prior w1 steps. "
            "Stop when marginal_mean <= 0. Window sizes must match the expected depletion rate."
        ),
        "assumptions": {
            "required_state": "Reward history for the last w1+w2 steps",
            "required_feedback": "Scalar reward observable at each step",
            "required_observability": "full",
            "dynamics": "depleting",
            "horizon": "episodic",
            "min_repeat_decisions": 24
        },
        "baseline": {
            "id": "fixed-budget-stopper",
            "description": "Fixed-Budget: use full budget; correct for stationary workloads"
        },
        "evidence": {
            "grade": "B",
            "source": "empirical",
            "summary": (
                "POC 5: locked selection for deceptive-depleting workload. "
                "Changed mean utility from -3.16 (full budget) to +3.08 — an 83.4% pull reduction. "
                "Best stopper when rewards are deceptive and early stopping avoids negative utility. "
                "Disqualified for stationary workloads."
            ),
            "refs": ["poc5/results.json"]
        },
        "failure_modes": [
            "Stops too early in stationary workloads where trend appears flat but rewards continue accumulating",
            "Window size w1, w2 must be matched to the depletion timescale — wrong window causes premature stopping",
            "Sensitive to reward noise — a noisy zero-reward step can trigger early stop",
            "Requires minimum w1+w2 steps before any stop decision is made"
        ],
        "incompatible_when": [
            "Stationary workloads — will incorrectly stop valuable early-flat reward sequences",
            "Budget is shorter than w1+w2 — rule never activates",
            "Rewards are binary with high variance — trend signal is too noisy"
        ],
        "compatible_blocks": ["explorer", "budget-allocator", "critic"],
        "cost_model": {
            "calls_per_decision": 0,
            "latency_class": "sub-ms",
            "notes": "Window mean comparison only"
        },
        "reference_implementation": "poc5/experiment.py:TrendMarginal",
        "example_use_case": (
            "Research agent over a depleting corpus: stop querying additional sources "
            "once the last 12 notes returned no new supporting evidence compared "
            "to the prior 12."
        ),
        "_v1_compat": {
            "slot": [],
            "base_rank": None,
            "goal_boosts": None,
            "complexity": 2,
            "interpretability": 4,
            "sample_efficiency": 3,
            "tags": ["stopper", "trend", "depleting", "marginal-value"],
            "conflicts_with": [],
            "pairs_well_with": ["thompson-sampling", "ucb1"],
            "requires": [],
            "references": []
        }
    },
    {
        "id": "confidence-marginal-stopper",
        "name": "Confidence-Marginal Stopper",
        "full_name": "Confidence-Based Marginal Value Stopping Rule",
        "schema_version": 2,
        "legacy": False,
        "classification": {
            "type": "executable-policy",
            "decision_blocks": ["stopper"],
            "framework": "statistics"
        },
        "description": (
            "Stops when a statistical confidence test on recent marginal reward "
            "indicates the expected value of continuing falls below a threshold. "
            "Uses a one-sided z-test on marginal reward in a sliding window."
        ),
        "theory_note": (
            "ConfidenceMarginal(w, z): collect w recent rewards, compute mean and SE, "
            "stop if mean - z*SE <= 0. Higher z is more conservative (stops less readily). "
            "z=1.28 ≈ 90% one-sided confidence."
        ),
        "assumptions": {
            "required_state": "Reward history for the last w steps",
            "required_feedback": "Scalar reward with approximately known variance",
            "required_observability": "full",
            "dynamics": "depleting",
            "horizon": "episodic",
            "min_repeat_decisions": 24
        },
        "baseline": {
            "id": "fixed-budget-stopper",
            "description": "Fixed-Budget: use full budget; correct for stationary workloads"
        },
        "evidence": {
            "grade": "B",
            "source": "empirical",
            "summary": (
                "POC 5: locked selection for heterogeneous-depleting workload. "
                "Produced 38.18 utility using 158.1 of 192 pulls (17.7% pull savings) "
                "versus 35.34 with full budget. "
                "Best stopper for heterogeneous depletion where some arms exhaust early. "
                "WindowMarginal (without confidence threshold) was disqualified in all workloads."
            ),
            "refs": ["poc5/results.json"]
        },
        "failure_modes": [
            "Requires reward variance to be estimable from the window — unreliable with very small windows",
            "Conservative z setting may prevent stopping even when marginal value has clearly dropped",
            "Aggressive z setting may stop before enough evidence is collected in heterogeneous workloads",
            "Normality assumption for z-test may not hold for binary or heavy-tailed rewards"
        ],
        "incompatible_when": [
            "Stationary workloads — confidence test will eventually clear as rewards accumulate",
            "Window size w is smaller than ~6 — z-test is unreliable with too few samples",
            "Reward variance is unknown and cannot be estimated reliably from recent history"
        ],
        "compatible_blocks": ["explorer", "budget-allocator", "critic"],
        "cost_model": {
            "calls_per_decision": 0,
            "latency_class": "sub-ms",
            "notes": "Z-test arithmetic only"
        },
        "reference_implementation": "poc5/experiment.py:ConfidenceMarginal",
        "example_use_case": (
            "Code-testing agent stops allocating new test runs once the confidence "
            "interval on marginal fault exposure includes zero — some modules are "
            "exhausted while others still benefit from testing."
        ),
        "_v1_compat": {
            "slot": [],
            "base_rank": None,
            "goal_boosts": None,
            "complexity": 2,
            "interpretability": 3,
            "sample_efficiency": 3,
            "tags": ["stopper", "confidence", "depleting", "marginal-value", "z-test"],
            "conflicts_with": [],
            "pairs_well_with": ["thompson-sampling", "ucb1"],
            "requires": [],
            "references": []
        }
    },
    {
        "id": "evidence-critic",
        "name": "Evidence Critic",
        "full_name": "Evidence-Coverage Critic Gate",
        "schema_version": 2,
        "legacy": False,
        "classification": {
            "type": "executable-policy",
            "decision_blocks": ["critic"],
            "framework": "symbolic"
        },
        "description": (
            "Evaluates a candidate answer by checking that every factual claim is "
            "traceable to a cited source, unresolved gaps are explicitly declared, "
            "and no unsupported assertion is included in the final output. "
            "Rejects or flags answers that fail the evidence ledger check."
        ),
        "theory_note": (
            "Implements hard stopping conditions: (1) sentence-level support check, "
            "(2) gap disclosure requirement, (3) contradiction detection. "
            "Acts as a pre-output quality gate before the stopper commits."
        ),
        "assumptions": {
            "required_state": "Evidence ledger: list of (claim, source, support_status) entries",
            "required_feedback": "None required for gate logic; ledger is maintained in-context",
            "required_observability": "full",
            "dynamics": "stationary",
            "horizon": "one-shot",
            "min_repeat_decisions": 1
        },
        "baseline": {
            "id": "llm",
            "description": "LLM judge: prompt the model to self-assess coverage — implicit, unverified"
        },
        "evidence": {
            "grade": "B",
            "source": "empirical",
            "summary": (
                "POC 6c Search Candidate 2: evidence-coverage gate reversed the blind evaluation "
                "direction from -8.1/-6.6 (Candidate 1, no gate) to +6.0/+4.8 points. "
                "Candidate 1 stopped after fewer reads but left evidence gaps unbounded; "
                "Candidate 2 made sentence support and gap disclosure hard stopping conditions. "
                "Confirmed on seen selection tasks; formal confirmation gated on runtime requirements."
            ),
            "refs": [
                "poc6c/RESULTS.md",
                "poc6c/pilot/CONFIGURED_AGENT_V2.md",
                "poc6c/PROGRESS.md"
            ]
        },
        "failure_modes": [
            "Over-triggering: rejects valid answers that use paraphrase rather than verbatim citation",
            "Increases search calls — Candidate 2 used all 4 allowed queries vs. generic 1.4; quality improved but efficiency did not",
            "Cannot detect plausible-sounding claims that happen to be unsupported if the ledger is maintained by the LLM",
            "Adds latency — each claim requires a lookup against the evidence ledger before output"
        ],
        "incompatible_when": [
            "Workload has no retrievable evidence base — opinion or generative tasks cannot satisfy citation requirements",
            "Budget is insufficient to both explore and verify claims",
            "Exact citation matching is not feasible — paraphrase-heavy corpora cause false failures"
        ],
        "compatible_blocks": ["stopper", "explorer", "memory-policy"],
        "cost_model": {
            "calls_per_decision": 0,
            "latency_class": "ms",
            "notes": "Ledger lookup is in-memory; claim parsing may add one LLM call if done by model"
        },
        "reference_implementation": "poc6c/pilot/CONFIGURED_AGENT_V2.md",
        "example_use_case": (
            "Research agent producing a sourced report: before finalizing each "
            "paragraph, checks that every sentence has a supporting note citation, "
            "and declares explicitly which questions remain unanswered by the corpus."
        ),
        "_v1_compat": {
            "slot": ["value"],
            "base_rank": None,
            "goal_boosts": None,
            "complexity": 2,
            "interpretability": 5,
            "sample_efficiency": 5,
            "tags": ["critic", "evidence", "citation", "quality-gate", "search"],
            "conflicts_with": [],
            "pairs_well_with": ["explore-then-commit", "ucb1", "thompson-sampling",
                                "fixed-budget-stopper", "trend-marginal-stopper"],
            "requires": [],
            "references": ["poc6c/RESULTS.md"]
        }
    }
]

V2_NULL_FIELDS = {
    "schema_version": 1,
    "legacy": True,
    "classification": None,
    "assumptions": None,
    "evidence": None,
    "failure_modes": None,
    "incompatible_when": None,
    "compatible_blocks": None,
    "cost_model": None,
    "reference_implementation": None,
}


def migrate():
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    existing = data["techniques"]

    # back-port existing records: add v2 fields as null without removing v1 fields
    backported = []
    for r in existing:
        updated = {}
        # id/name/full_name first
        for k in ("id", "name", "full_name"):
            if k in r:
                updated[k] = r[k]
        # inject v2 null fields
        updated.update(V2_NULL_FIELDS)
        # carry over all original v1 fields
        for k, v in r.items():
            if k not in updated:
                updated[k] = v
        backported.append(updated)

    # new v2 records go first, then back-ported v1 records
    # (skip back-ported records whose id collides with a new v2 id)
    new_ids = {r["id"] for r in V2_RECORDS}
    merged = V2_RECORDS + [r for r in backported if r["id"] not in new_ids]

    data["_meta"]["schema_version"] = "2.0"
    data["_meta"]["technique_count"] = len(merged)
    data["_meta"]["updated"] = "2026-08-04"
    data["techniques"] = merged

    REGISTRY.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Migration complete: {len(merged)} techniques ({len(V2_RECORDS)} v2, {len(merged)-len(V2_RECORDS)} v1-legacy)")


if __name__ == "__main__":
    migrate()
