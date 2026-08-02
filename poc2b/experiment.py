"""POC 2b confirmatory experiment.

The design and pass/fail rules are locked in PREREGISTRATION.md. Do not change
them after inspecting results; corrections require a new POC identifier.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

from environment import PotentialOutcomeEnv, build_regimes, build_trial_outcomes
from policies import POLICIES, ExploreThenCommit


BASE_SEED = 20260728
CONFIRMATION_OFFSET = 1_000_000
POLICY_SEED_OFFSET = 9_000_000
N_SELECTION = 1000
N_CONFIRMATION = 2000
EQUIVALENCE_PCT = 2.0
Z_95 = 1.96


def mean_ci(values: np.ndarray) -> tuple[float, float, float]:
    mean = float(values.mean())
    if len(values) < 2:
        return mean, mean, mean
    half_width = Z_95 * float(values.std(ddof=1)) / math.sqrt(len(values))
    return mean, mean - half_width, mean + half_width


def run_episode(
    policy_class: type,
    outcomes: np.ndarray,
    budget: int,
    policy_seed: int,
) -> int:
    env = PotentialOutcomeEnv(outcomes, budget)
    policy = policy_class(
        env.k,
        np.random.default_rng(policy_seed),
        budget,
    )
    found = 0
    while not env.done:
        branch = policy.select()
        reward = env.pull(branch)
        policy.update(branch, reward)
        found += reward
    return found


def run_split(regime, start_seed: int, n_trials: int) -> dict[str, np.ndarray]:
    scores = {
        policy_class.name: np.zeros(n_trials, dtype=float)
        for policy_class in POLICIES
    }
    for trial_index in range(n_trials):
        world_seed = start_seed + trial_index
        outcomes = build_trial_outcomes(regime, world_seed)
        for policy_index, policy_class in enumerate(POLICIES):
            policy_seed = (
                POLICY_SEED_OFFSET
                + world_seed * len(POLICIES)
                + policy_index
            )
            scores[policy_class.name][trial_index] = run_episode(
                policy_class,
                outcomes,
                regime.budget,
                policy_seed,
            )
    return scores


def classify(policy: np.ndarray, reference: np.ndarray) -> dict[str, object]:
    relative_mean = 100.0 * float(policy.mean()) / float(reference.mean())

    viable_stat = policy - 0.95 * reference
    viable_mean, viable_low, viable_high = mean_ci(viable_stat)

    disqual_stat = policy - 0.80 * reference
    disqual_mean, disqual_low, disqual_high = mean_ci(disqual_stat)

    if viable_low >= 0:
        status = "viable"
    elif disqual_high < 0:
        status = "disqualified"
    else:
        status = "uncertain"

    return {
        "status": status,
        "relative_to_locked_reference_pct": relative_mean,
        "viability_stat": {
            "mean": viable_mean,
            "ci95": [viable_low, viable_high],
        },
        "disqualification_stat": {
            "mean": disqual_mean,
            "ci95": [disqual_low, disqual_high],
        },
    }


def control_equivalence(
    scores: dict[str, np.ndarray],
) -> tuple[bool, float, list[dict[str, object]]]:
    grand_mean = float(np.mean([values.mean() for values in scores.values()]))
    bound = EQUIVALENCE_PCT / 100.0 * grand_mean
    names = list(scores)
    comparisons = []
    passed = True
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            mean, low, high = mean_ci(scores[left] - scores[right])
            equivalent = low >= -bound and high <= bound
            passed = passed and equivalent
            comparisons.append(
                {
                    "left": left,
                    "right": right,
                    "mean_difference": mean,
                    "ci95": [low, high],
                    "equivalence_bound": bound,
                    "equivalent": bool(equivalent),
                }
            )
    return passed, grand_mean, comparisons


def main() -> int:
    regimes = build_regimes(k=12)
    output: dict[str, object] = {
        "design": {
            "base_seed": BASE_SEED,
            "selection_trials": N_SELECTION,
            "confirmation_trials": N_CONFIRMATION,
            "equivalence_pct": EQUIVALENCE_PCT,
            "preregistration": "PREREGISTRATION.md",
        },
        "regimes": {},
    }

    print("=" * 88)
    print("POC 2b - corrected confirmatory policy-viability test")
    print(
        f"selection={N_SELECTION} | confirmation={N_CONFIRMATION} | "
        "paired potential outcomes"
    )
    print("=" * 88)

    all_confirm_scores: dict[str, dict[str, np.ndarray]] = {}

    for regime in regimes:
        print(f"\n[{regime.name}] budget={regime.budget}, K={regime.k}")
        selection = run_split(regime, BASE_SEED, N_SELECTION)
        locked_reference = max(selection, key=lambda name: selection[name].mean())

        confirmation = run_split(
            regime,
            BASE_SEED + CONFIRMATION_OFFSET,
            N_CONFIRMATION,
        )
        all_confirm_scores[regime.name] = confirmation
        reference_scores = confirmation[locked_reference]

        ranked = sorted(
            confirmation,
            key=lambda name: confirmation[name].mean(),
            reverse=True,
        )
        policies = {}
        print(f"locked reference from selection: {locked_reference}")
        print(f"{'policy':<30}{'mean':>9}{'CI half':>11}{'relative':>11}{'status':>16}")
        for name in ranked:
            mean, low, high = mean_ci(confirmation[name])
            classification = classify(confirmation[name], reference_scores)
            policies[name] = {
                "mean": mean,
                "ci95": [low, high],
                **classification,
            }
            print(
                f"{name:<30}{mean:>9.3f}{(high - low) / 2:>11.3f}"
                f"{classification['relative_to_locked_reference_pct']:>10.1f}%"
                f"{classification['status']:>16}"
            )

        baseline = confirmation[ExploreThenCommit.name]
        material_stat = reference_scores - 1.02 * baseline
        material_mean, material_low, material_high = mean_ci(material_stat)
        material = material_low > 0
        raw_uplift = (
            100.0
            * (float(reference_scores.mean()) - float(baseline.mean()))
            / float(baseline.mean())
        )
        print(
            "locked reference vs ExploreThenCommit: "
            f"raw uplift={raw_uplift:+.2f}% | "
            f"material beyond 2%={material}"
        )

        output["regimes"][regime.name] = {
            "description": regime.description,
            "budget": regime.budget,
            "k": regime.k,
            "mode": regime.mode,
            "locked_reference": locked_reference,
            "selection_means": {
                name: float(values.mean()) for name, values in selection.items()
            },
            "confirmation_ranking": ranked,
            "policies": policies,
            "reference_vs_explore_then_commit": {
                "raw_uplift_pct": raw_uplift,
                "material_beyond_2pct": bool(material),
                "test_stat_mean": material_mean,
                "test_stat_ci95": [material_low, material_high],
            },
        }

    control_name = "stationary_uniform"
    control_pass, control_grand_mean, control_comparisons = control_equivalence(
        all_confirm_scores[control_name]
    )

    non_control_names = [
        regime.name for regime in regimes if regime.name != control_name
    ]
    policy_swings: list[str] = []
    policy_statuses: dict[str, dict[str, str]] = {}
    for policy_class in POLICIES:
        name = policy_class.name
        statuses = {
            regime_name: output["regimes"][regime_name]["policies"][name]["status"]
            for regime_name in non_control_names
        }
        policy_statuses[name] = statuses
        if "viable" in statuses.values() and "disqualified" in statuses.values():
            policy_swings.append(name)

    baseline_viable = any(
        policy_statuses[ExploreThenCommit.name][regime_name] == "viable"
        for regime_name in non_control_names
    )
    disqualification_pass = len(policy_swings) >= 2
    passed = control_pass and disqualification_pass and baseline_viable

    verdict = {
        "passed": bool(passed),
        "conditions": {
            "valid_control": bool(control_pass),
            "at_least_two_regime_dependent_disqualifications": bool(
                disqualification_pass
            ),
            "explore_then_commit_viable_somewhere": bool(baseline_viable),
        },
        "swinging_policies": policy_swings,
        "policy_statuses_non_control": policy_statuses,
        "control_grand_mean": control_grand_mean,
        "control_pairwise_equivalence": control_comparisons,
    }
    output["verdict"] = verdict

    print("\n" + "=" * 88)
    print("PRE-REGISTERED VERDICT")
    print("=" * 88)
    print(f"valid stationary control: {control_pass}")
    print(
        "policies viable somewhere and disqualified elsewhere: "
        f"{len(policy_swings)} ({', '.join(policy_swings) or 'none'})"
    )
    print(f"ExploreThenCommit viable in a non-control regime: {baseline_viable}")
    print(f"POC 2b: {'PASS' if passed else 'FAIL'}")

    destination = Path(__file__).with_name("results.json")
    destination.write_text(
        json.dumps(output, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"results: {destination}")
    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main())
