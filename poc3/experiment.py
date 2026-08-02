"""POC 3 sensitivity experiment.

The design and pass/fail rules are locked in PREREGISTRATION.md. Corrections
after the first run require a new POC identifier.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
POC2B = ROOT / "poc2b"
sys.path.insert(0, str(POC2B))

from environment import PotentialOutcomeEnv, Regime, build_trial_outcomes  # noqa: E402
from policies import (  # noqa: E402
    DiscountedThompson,
    EpsilonGreedy,
    ExploreThenCommit,
    POLICIES,
    RoundRobin,
    ThompsonSampling,
    UCB1,
)

from policy_variants import FAMILY_VARIANTS  # noqa: E402


BASE_SEED = 20260728
CONFIRMATION_OFFSET = 2_000_000
POLICY_SEED_OFFSET = 11_000_000
N_SELECTION = 250
N_CONFIRMATION = 750
K_VALUES = (5, 12, 30)
BUDGET_MULTIPLIERS = (1, 4, 16)
CONTROL_MAX_GAP_PCT = 3.0
Z_95 = 1.96

SHAPES = (
    "stationary_uniform",
    "stationary_needle",
    "depleting_needle",
    "deceptive_depleting",
    "heterogeneous_depleting",
)
NON_CONTROL_SHAPES = SHAPES[1:]

PRIMARY_POLICIES = (
    RoundRobin,
    ExploreThenCommit,
    EpsilonGreedy,
    UCB1,
    ThompsonSampling,
    DiscountedThompson,
)

PRIMARY_DISPLAY_NAMES = {
    RoundRobin: "RoundRobin",
    ExploreThenCommit: "ExploreThenCommit",
    EpsilonGreedy: "EpsilonGreedy(e=0.1)",
    UCB1: "UCB1(c=2.0)",
    ThompsonSampling: "ThompsonSampling(prior=1.0)",
    DiscountedThompson: "DiscountedThompson(g=0.9)",
}


def mean_ci(values: np.ndarray) -> tuple[float, float, float]:
    mean = float(values.mean())
    half = Z_95 * float(values.std(ddof=1)) / math.sqrt(len(values))
    return mean, mean - half, mean + half


def classify(policy: np.ndarray, reference: np.ndarray) -> dict[str, object]:
    viable_mean, viable_low, viable_high = mean_ci(policy - 0.95 * reference)
    disqual_mean, disqual_low, disqual_high = mean_ci(policy - 0.80 * reference)
    if viable_low >= 0:
        status = "viable"
    elif disqual_high < 0:
        status = "disqualified"
    else:
        status = "uncertain"
    return {
        "status": status,
        "relative_to_locked_reference_pct": (
            100.0 * float(policy.mean()) / float(reference.mean())
        ),
        "viability_stat": {
            "mean": viable_mean,
            "ci95": [viable_low, viable_high],
        },
        "disqualification_stat": {
            "mean": disqual_mean,
            "ci95": [disqual_low, disqual_high],
        },
    }


def scaled_size(multiplier: float, k: int, minimum: int) -> int:
    return max(minimum, int(round(multiplier * k)))


def build_regime(shape: str, k: int, budget_multiplier: int) -> Regime:
    budget = budget_multiplier * k
    if shape == "stationary_uniform":
        return Regime(
            shape,
            "Equal stationary branches.",
            k,
            budget,
            "stationary",
            (0.35,) * k,
        )
    if shape == "stationary_needle":
        return Regime(
            shape,
            "One strong stationary branch.",
            k,
            budget,
            "stationary",
            (0.75,) + (0.10,) * (k - 1),
        )
    if shape == "depleting_needle":
        return Regime(
            shape,
            "One strong finite branch among poor finite branches.",
            k,
            budget,
            "finite_urn",
            (0.75,) + (0.10,) * (k - 1),
            (scaled_size(5.3, k, 12),)
            + (scaled_size(2.3, k, 8),) * (k - 1),
        )
    if shape == "deceptive_depleting":
        return Regime(
            shape,
            "A shallow certain trap plus a sustainable branch.",
            k,
            budget,
            "finite_urn",
            (1.0, 0.38) + (0.10,) * (k - 2),
            (
                scaled_size(0.6, k, 3),
                scaled_size(6.7, k, 20),
            )
            + (scaled_size(2.0, k, 6),) * (k - 2),
        )
    if shape == "heterogeneous_depleting":
        return Regime(
            shape,
            "One strong finite branch among moderate finite branches.",
            k,
            budget,
            "finite_urn",
            (0.75,) + (0.20,) * (k - 1),
            (scaled_size(6.7, k, 20),)
            + (scaled_size(2.5, k, 8),) * (k - 1),
        )
    raise ValueError(f"unknown shape: {shape}")


def run_episode(
    policy_class: type,
    outcomes: np.ndarray,
    budget: int,
    policy_seed: int,
) -> int:
    env = PotentialOutcomeEnv(outcomes, budget)
    policy = policy_class(env.k, np.random.default_rng(policy_seed), budget)
    total = 0
    while not env.done:
        branch = policy.select()
        reward = env.pull(branch)
        policy.update(branch, reward)
        total += reward
    return total


def run_split(
    regime: Regime,
    policy_classes: tuple[type, ...],
    start_seed: int,
    n_trials: int,
    seed_namespace: int,
) -> dict[str, np.ndarray]:
    scores = {
        policy_class.name: np.zeros(n_trials, dtype=float)
        for policy_class in policy_classes
    }
    for trial_index in range(n_trials):
        world_seed = start_seed + trial_index
        outcomes = build_trial_outcomes(regime, world_seed)
        for policy_index, policy_class in enumerate(policy_classes):
            policy_seed = (
                POLICY_SEED_OFFSET
                + seed_namespace * 10_000_000
                + world_seed * len(policy_classes)
                + policy_index
            )
            scores[policy_class.name][trial_index] = run_episode(
                policy_class,
                outcomes,
                regime.budget,
                policy_seed,
            )
    return scores


def control_gap(scores: dict[str, np.ndarray]) -> dict[str, object]:
    means = {name: float(values.mean()) for name, values in scores.items()}
    grand_mean = float(np.mean(list(means.values())))
    gap = max(means.values()) - min(means.values())
    gap_pct = 100.0 * gap / grand_mean
    return {
        "means": means,
        "grand_mean": grand_mean,
        "max_mean_gap": gap,
        "max_mean_gap_pct": gap_pct,
        "passed": bool(gap_pct <= CONTROL_MAX_GAP_PCT),
    }


def cell_key(k: int, budget_multiplier: int, shape: str) -> str:
    return f"k{k}_b{budget_multiplier}_{shape}"


def setting_key(k: int, budget_multiplier: int) -> str:
    return f"k{k}_b{budget_multiplier}"


def main() -> int:
    results: dict[str, object] = {
        "design": {
            "selection_trials": N_SELECTION,
            "confirmation_trials": N_CONFIRMATION,
            "k_values": K_VALUES,
            "budget_multipliers": BUDGET_MULTIPLIERS,
            "shapes": SHAPES,
            "preregistration": "PREREGISTRATION.md",
        },
        "primary_cells": {},
        "settings": {},
        "parameter_analysis": {},
    }
    confirmation_cache: dict[str, dict[str, np.ndarray]] = {}
    outcome_cache: dict[str, Regime] = {}

    print("=" * 94)
    print("POC 3 - size, budget, workload, and parameter sensitivity")
    print(
        f"primary cells={len(K_VALUES) * len(BUDGET_MULTIPLIERS) * len(SHAPES)} "
        f"| selection={N_SELECTION} | confirmation={N_CONFIRMATION}"
    )
    print("=" * 94)

    cell_number = 0
    total_cells = len(K_VALUES) * len(BUDGET_MULTIPLIERS) * len(SHAPES)
    for k in K_VALUES:
        for budget_multiplier in BUDGET_MULTIPLIERS:
            for shape_index, shape in enumerate(SHAPES):
                cell_number += 1
                regime = build_regime(shape, k, budget_multiplier)
                key = cell_key(k, budget_multiplier, shape)
                outcome_cache[key] = regime
                selection = run_split(
                    regime,
                    PRIMARY_POLICIES,
                    BASE_SEED,
                    N_SELECTION,
                    seed_namespace=shape_index,
                )
                selection_named = {
                    PRIMARY_DISPLAY_NAMES[policy_class]: selection[policy_class.name]
                    for policy_class in PRIMARY_POLICIES
                }
                locked_reference = max(
                    selection_named,
                    key=lambda name: selection_named[name].mean(),
                )

                confirmation_raw = run_split(
                    regime,
                    PRIMARY_POLICIES,
                    BASE_SEED + CONFIRMATION_OFFSET,
                    N_CONFIRMATION,
                    seed_namespace=shape_index,
                )
                confirmation = {
                    PRIMARY_DISPLAY_NAMES[policy_class]: confirmation_raw[
                        policy_class.name
                    ]
                    for policy_class in PRIMARY_POLICIES
                }
                confirmation_cache[key] = confirmation
                reference = confirmation[locked_reference]
                ranked = sorted(
                    confirmation,
                    key=lambda name: confirmation[name].mean(),
                    reverse=True,
                )
                policies = {}
                for name in ranked:
                    mean, low, high = mean_ci(confirmation[name])
                    policies[name] = {
                        "mean": mean,
                        "ci95": [low, high],
                        **classify(confirmation[name], reference),
                    }

                baseline = confirmation["ExploreThenCommit"]
                material_stat = reference - 1.02 * baseline
                _, material_low, material_high = mean_ci(material_stat)
                raw_uplift = (
                    100.0
                    * (float(reference.mean()) - float(baseline.mean()))
                    / float(baseline.mean())
                )

                control = (
                    control_gap(confirmation)
                    if shape == "stationary_uniform"
                    else None
                )
                results["primary_cells"][key] = {
                    "k": k,
                    "budget_multiplier": budget_multiplier,
                    "budget": regime.budget,
                    "shape": shape,
                    "locked_reference": locked_reference,
                    "selection_means": {
                        name: float(values.mean())
                        for name, values in selection_named.items()
                    },
                    "confirmation_ranking": ranked,
                    "policies": policies,
                    "control": control,
                    "reference_vs_explore_then_commit": {
                        "raw_uplift_pct": raw_uplift,
                        "material_beyond_2pct": bool(material_low > 0),
                        "test_ci95": [material_low, material_high],
                    },
                }
                print(
                    f"[{cell_number:02d}/{total_cells}] K={k:<2} "
                    f"B={budget_multiplier:<2} shape={shape:<25} "
                    f"ref={locked_reference}"
                )

    persistent_counts = {name: 0 for name in PRIMARY_DISPLAY_NAMES.values()}
    simple_viable_settings = 0
    controls_pass = True

    for k in K_VALUES:
        for budget_multiplier in BUDGET_MULTIPLIERS:
            skey = setting_key(k, budget_multiplier)
            statuses_by_policy: dict[str, dict[str, str]] = {
                name: {} for name in PRIMARY_DISPLAY_NAMES.values()
            }
            for shape in NON_CONTROL_SHAPES:
                cell = results["primary_cells"][
                    cell_key(k, budget_multiplier, shape)
                ]
                for name in statuses_by_policy:
                    statuses_by_policy[name][shape] = cell["policies"][name]["status"]

            swinging = []
            for name, statuses in statuses_by_policy.items():
                if (
                    "viable" in statuses.values()
                    and "disqualified" in statuses.values()
                ):
                    swinging.append(name)
                    persistent_counts[name] += 1

            simple_viable = "viable" in statuses_by_policy[
                "ExploreThenCommit"
            ].values()
            simple_viable_settings += int(simple_viable)
            control = results["primary_cells"][
                cell_key(k, budget_multiplier, "stationary_uniform")
            ]["control"]
            controls_pass = controls_pass and control["passed"]
            results["settings"][skey] = {
                "k": k,
                "budget_multiplier": budget_multiplier,
                "swinging_policies": swinging,
                "statuses": statuses_by_policy,
                "explore_then_commit_viable": simple_viable,
                "control_passed": control["passed"],
                "control_max_gap_pct": control["max_mean_gap_pct"],
            }

    # Parameter perturbations at K=12 reuse the primary locked references.
    family_results: dict[str, object] = {}
    for family_index, (family_name, variants) in enumerate(FAMILY_VARIANTS.items()):
        variant_statuses: dict[str, dict[str, str]] = {
            variant.name: {} for variant in variants
        }
        for budget_multiplier in BUDGET_MULTIPLIERS:
            for shape_index, shape in enumerate(NON_CONTROL_SHAPES):
                key = cell_key(12, budget_multiplier, shape)
                regime = outcome_cache[key]
                primary_cell = results["primary_cells"][key]
                reference = confirmation_cache[key][
                    primary_cell["locked_reference"]
                ]
                variant_scores = run_split(
                    regime,
                    variants,
                    BASE_SEED + CONFIRMATION_OFFSET,
                    N_CONFIRMATION,
                    seed_namespace=100 + family_index * 10 + shape_index,
                )
                for variant in variants:
                    status = classify(variant_scores[variant.name], reference)
                    short_cell = f"b{budget_multiplier}_{shape}"
                    variant_statuses[variant.name][short_cell] = status["status"]

        swinging_configurations = []
        for variant_name, statuses in variant_statuses.items():
            if "viable" in statuses.values() and "disqualified" in statuses.values():
                swinging_configurations.append(variant_name)
        robust = len(swinging_configurations) >= 2
        family_results[family_name] = {
            "parameter_robust_swing": robust,
            "swinging_configurations": swinging_configurations,
            "statuses": variant_statuses,
        }
        print(
            f"[parameters] {family_name:<22} "
            f"swinging={len(swinging_configurations)} robust={robust}"
        )

    results["parameter_analysis"] = family_results

    persistent_policies = [
        name for name, count in persistent_counts.items() if count >= 3
    ]
    robust_families = [
        name
        for name, data in family_results.items()
        if data["parameter_robust_swing"]
    ]

    conditions = {
        "all_nine_controls_pass": bool(controls_pass),
        "at_least_two_policies_swing_in_three_settings": bool(
            len(persistent_policies) >= 2
        ),
        "explore_then_commit_viable_in_six_settings": bool(
            simple_viable_settings >= 6
        ),
        "at_least_two_parameter_robust_families": bool(
            len(robust_families) >= 2
        ),
    }
    passed = all(conditions.values())
    results["verdict"] = {
        "passed": bool(passed),
        "conditions": conditions,
        "persistent_policy_counts": persistent_counts,
        "persistent_policies": persistent_policies,
        "simple_viable_settings": simple_viable_settings,
        "parameter_robust_families": robust_families,
    }

    print("\n" + "=" * 94)
    print("PRE-REGISTERED VERDICT")
    print("=" * 94)
    print(f"all 9 controls pass: {controls_pass}")
    print(
        "policies swinging in >=3 settings: "
        f"{len(persistent_policies)} ({', '.join(persistent_policies) or 'none'})"
    )
    print(
        "settings where ExploreThenCommit is viable: "
        f"{simple_viable_settings}/9"
    )
    print(
        "parameter-robust families: "
        f"{len(robust_families)} ({', '.join(robust_families) or 'none'})"
    )
    print(f"POC 3: {'PASS' if passed else 'FAIL'}")

    destination = Path(__file__).with_name("results.json")
    destination.write_text(
        json.dumps(results, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"results: {destination}")
    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main())
