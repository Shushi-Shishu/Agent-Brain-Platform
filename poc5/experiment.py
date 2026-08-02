"""POC 5 stopping-rule generality experiment.

The design and pass/fail rules are locked in PREREGISTRATION.md. Corrections
after the first run require a new POC identifier.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
POC2B = ROOT / "poc2b"
sys.path.insert(0, str(POC2B))

from environment import PotentialOutcomeEnv, Regime, build_trial_outcomes  # noqa: E402
from policies import ThompsonSampling  # noqa: E402


BASE_SEED = 20260728
CONFIRMATION_OFFSET = 6_000_000
POLICY_SEED_OFFSET = 23_000_000
K = 12
BUDGET = 192
PULL_COST = 0.20
N_SELECTION_PER_SHAPE = 500
N_CONFIRMATION_PER_SHAPE = 1_500
Z_95 = 1.96

SHAPES = (
    "stationary_uniform",
    "stationary_needle",
    "depleting_needle",
    "deceptive_depleting",
    "heterogeneous_depleting",
)


def scaled_size(multiplier: float, k: int, minimum: int) -> int:
    return max(minimum, int(round(multiplier * k)))


def build_regime(shape: str) -> Regime:
    if shape == "stationary_uniform":
        return Regime(
            shape,
            "Equal stationary branches.",
            K,
            BUDGET,
            "stationary",
            (0.35,) * K,
        )
    if shape == "stationary_needle":
        return Regime(
            shape,
            "One strong stationary branch.",
            K,
            BUDGET,
            "stationary",
            (0.75,) + (0.10,) * (K - 1),
        )
    if shape == "depleting_needle":
        return Regime(
            shape,
            "One strong finite branch among poor finite branches.",
            K,
            BUDGET,
            "finite_urn",
            (0.75,) + (0.10,) * (K - 1),
            (scaled_size(5.3, K, 12),)
            + (scaled_size(2.3, K, 8),) * (K - 1),
        )
    if shape == "deceptive_depleting":
        return Regime(
            shape,
            "A shallow certain trap plus a sustainable branch.",
            K,
            BUDGET,
            "finite_urn",
            (1.0, 0.38) + (0.10,) * (K - 2),
            (
                scaled_size(0.6, K, 3),
                scaled_size(6.7, K, 20),
            )
            + (scaled_size(2.0, K, 6),) * (K - 2),
        )
    if shape == "heterogeneous_depleting":
        return Regime(
            shape,
            "One strong finite branch among moderate finite branches.",
            K,
            BUDGET,
            "finite_urn",
            (0.75,) + (0.20,) * (K - 1),
            (scaled_size(6.7, K, 20),)
            + (scaled_size(2.5, K, 8),) * (K - 1),
        )
    raise ValueError(f"unknown shape: {shape}")


@dataclass(frozen=True)
class StopResult:
    pulls: int
    findings: int
    utility: float


class StoppingRule:
    name = "StoppingRule"
    adaptive = False

    def stop_time(self, rewards: np.ndarray) -> int:
        raise NotImplementedError


class FixedBudget(StoppingRule):
    name = "FixedBudget"

    def stop_time(self, rewards: np.ndarray) -> int:
        return len(rewards)


class FixedHalf(StoppingRule):
    name = "FixedHalf"

    def stop_time(self, rewards: np.ndarray) -> int:
        return min(BUDGET // 2, len(rewards))


class PatienceStop(StoppingRule):
    name = "PatienceStop(8)"
    adaptive = True
    minimum = 12
    patience = 8

    def stop_time(self, rewards: np.ndarray) -> int:
        for pulls in range(self.minimum, len(rewards) + 1):
            if int(rewards[pulls - self.patience : pulls].sum()) == 0:
                return pulls
        return len(rewards)


class WindowMarginal(StoppingRule):
    name = "WindowMarginal(24)"
    adaptive = True
    minimum = 24
    window = 24

    def stop_time(self, rewards: np.ndarray) -> int:
        for pulls in range(self.minimum, len(rewards) + 1):
            recent_rate = float(rewards[pulls - self.window : pulls].mean())
            if recent_rate <= PULL_COST:
                return pulls
        return len(rewards)


class ConfidenceMarginal(StoppingRule):
    name = "ConfidenceMarginal(24,z=1.28)"
    adaptive = True
    minimum = 24
    window = 24
    z = 1.28

    def stop_time(self, rewards: np.ndarray) -> int:
        for pulls in range(self.minimum, len(rewards) + 1):
            recent = rewards[pulls - self.window : pulls]
            p_hat = float(recent.mean())
            upper = p_hat + self.z * math.sqrt(
                (p_hat * (1.0 - p_hat) + 0.25) / (self.window + 2)
            )
            if upper <= PULL_COST:
                return pulls
        return len(rewards)


class TrendMarginal(StoppingRule):
    name = "TrendMarginal(12+12)"
    adaptive = True
    minimum = 24
    window = 12

    def stop_time(self, rewards: np.ndarray) -> int:
        for pulls in range(self.minimum, len(rewards) + 1):
            recent = float(rewards[pulls - self.window : pulls].mean())
            prior = float(
                rewards[
                    pulls - 2 * self.window : pulls - self.window
                ].mean()
            )
            if recent < PULL_COST and recent + 0.10 <= prior:
                return pulls
        return len(rewards)


RULE_CLASSES = (
    FixedBudget,
    FixedHalf,
    PatienceStop,
    WindowMarginal,
    ConfidenceMarginal,
    TrendMarginal,
)
RULE_BY_NAME = {rule.name: rule for rule in RULE_CLASSES}
ADAPTIVE_RULE_NAMES = tuple(
    rule.name for rule in RULE_CLASSES if rule.adaptive
)


def generate_trajectory(
    regime: Regime,
    world_seed: int,
    policy_seed: int,
) -> np.ndarray:
    outcomes = build_trial_outcomes(regime, world_seed)
    env = PotentialOutcomeEnv(outcomes, BUDGET)
    policy = ThompsonSampling(K, np.random.default_rng(policy_seed), BUDGET)
    rewards = np.zeros(BUDGET, dtype=np.int8)
    for pull in range(BUDGET):
        branch = policy.select()
        reward = env.pull(branch)
        policy.update(branch, reward)
        rewards[pull] = reward
    return rewards


def evaluate_rule(
    rule_class: type[StoppingRule],
    rewards: np.ndarray,
    pull_cost: float = PULL_COST,
) -> StopResult:
    pulls = int(rule_class().stop_time(rewards))
    if pulls < 0 or pulls > len(rewards):
        raise ValueError(f"invalid stop time from {rule_class.name}: {pulls}")
    findings = int(rewards[:pulls].sum())
    return StopResult(
        pulls=pulls,
        findings=findings,
        utility=findings - pull_cost * pulls,
    )


def build_trajectories(
    start_seed: int,
    trials_per_shape: int,
    namespace: int,
) -> dict[str, np.ndarray]:
    trajectories: dict[str, np.ndarray] = {}
    for shape_index, shape in enumerate(SHAPES):
        regime = build_regime(shape)
        shape_trajectories = np.zeros(
            (trials_per_shape, BUDGET),
            dtype=np.int8,
        )
        for trial_index in range(trials_per_shape):
            world_seed = start_seed + shape_index * 100_000 + trial_index
            policy_seed = (
                POLICY_SEED_OFFSET
                + namespace * 10_000_000
                + shape_index * 1_000_000
                + trial_index
            )
            shape_trajectories[trial_index] = generate_trajectory(
                regime,
                world_seed,
                policy_seed,
            )
        trajectories[shape] = shape_trajectories
    return trajectories


def evaluate_all(
    trajectories: dict[str, np.ndarray],
) -> dict[str, dict[str, dict[str, np.ndarray]]]:
    results: dict[str, dict[str, dict[str, np.ndarray]]] = {}
    for shape in SHAPES:
        results[shape] = {}
        for rule_class in RULE_CLASSES:
            utilities = np.zeros(len(trajectories[shape]), dtype=float)
            pulls = np.zeros(len(trajectories[shape]), dtype=float)
            findings = np.zeros(len(trajectories[shape]), dtype=float)
            for index, rewards in enumerate(trajectories[shape]):
                outcome = evaluate_rule(rule_class, rewards)
                utilities[index] = outcome.utility
                pulls[index] = outcome.pulls
                findings[index] = outcome.findings
            results[shape][rule_class.name] = {
                "utility": utilities,
                "pulls": pulls,
                "findings": findings,
            }
    return results


def lock_references(
    selection: dict[str, dict[str, dict[str, np.ndarray]]],
) -> dict[str, str]:
    order = list(RULE_BY_NAME)
    return {
        shape: max(
            order,
            key=lambda name: (
                float(selection[shape][name]["utility"].mean()),
                -order.index(name),
            ),
        )
        for shape in SHAPES
    }


def mean_ci(values: np.ndarray) -> tuple[float, float, float]:
    mean = float(values.mean())
    half = Z_95 * float(values.std(ddof=1)) / math.sqrt(len(values))
    return mean, mean - half, mean + half


def classify(
    candidate: np.ndarray,
    reference: np.ndarray,
) -> dict[str, object]:
    viable_mean, viable_low, viable_high = mean_ci(
        candidate - 0.95 * reference
    )
    disqual_mean, disqual_low, disqual_high = mean_ci(
        candidate - 0.80 * reference
    )
    if viable_low >= 0:
        status = "viable"
    elif disqual_high < 0:
        status = "disqualified"
    else:
        status = "uncertain"
    return {
        "status": status,
        "relative_to_locked_reference_pct": (
            100.0 * float(candidate.mean()) / float(reference.mean())
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


def hindsight_prefix_utility(rewards: np.ndarray) -> float:
    pulls = np.arange(1, len(rewards) + 1, dtype=float)
    utilities = np.cumsum(rewards, dtype=float) - PULL_COST * pulls
    return float(max(0.0, float(utilities.max())))


def main() -> int:
    print("=" * 94)
    print("POC 5 - stopping-rule generality")
    print(
        f"K={K} max_budget={BUDGET} pull_cost={PULL_COST} "
        f"| selection={N_SELECTION_PER_SHAPE}/shape "
        f"| confirmation={N_CONFIRMATION_PER_SHAPE}/shape"
    )
    print("=" * 94)

    selection_trajectories = build_trajectories(
        BASE_SEED,
        N_SELECTION_PER_SHAPE,
        namespace=1,
    )
    selection = evaluate_all(selection_trajectories)
    locked_references = lock_references(selection)
    for shape in SHAPES:
        reference = locked_references[shape]
        mean = selection[shape][reference]["utility"].mean()
        print(f"locked reference[{shape}] = {reference} ({mean:.3f})")

    confirmation_trajectories = build_trajectories(
        BASE_SEED + CONFIRMATION_OFFSET,
        N_CONFIRMATION_PER_SHAPE,
        namespace=2,
    )
    confirmation = evaluate_all(confirmation_trajectories)

    statuses: dict[str, dict[str, str]] = {
        rule.name: {} for rule in RULE_CLASSES
    }
    workload_results: dict[str, object] = {}
    positive_references = True
    zero_cost_sanity = True

    for shape in SHAPES:
        reference_name = locked_references[shape]
        reference_values = confirmation[shape][reference_name]["utility"]
        reference_mean = float(reference_values.mean())
        positive_references = positive_references and reference_mean > 0

        policy_results: dict[str, object] = {}
        ranking = sorted(
            RULE_BY_NAME,
            key=lambda name: float(
                confirmation[shape][name]["utility"].mean()
            ),
            reverse=True,
        )
        for rule_name in RULE_BY_NAME:
            data = confirmation[shape][rule_name]
            classification = classify(data["utility"], reference_values)
            statuses[rule_name][shape] = classification["status"]
            policy_results[rule_name] = {
                **classification,
                "mean_utility": float(data["utility"].mean()),
                "mean_findings": float(data["findings"].mean()),
                "mean_pulls": float(data["pulls"].mean()),
                "utility_vs_fixed_budget": {
                    "mean_difference": float(
                        (
                            data["utility"]
                            - confirmation[shape]["FixedBudget"]["utility"]
                        ).mean()
                    ),
                    "difference_ci95": list(
                        mean_ci(
                            data["utility"]
                            - confirmation[shape]["FixedBudget"]["utility"]
                        )[1:]
                    ),
                },
            }

        hindsight = np.asarray(
            [
                hindsight_prefix_utility(rewards)
                for rewards in confirmation_trajectories[shape]
            ],
            dtype=float,
        )
        workload_results[shape] = {
            "locked_reference": reference_name,
            "reference_confirmation_mean": reference_mean,
            "confirmation_ranking": ranking,
            "rules": policy_results,
            "hindsight_prefix_oracle_mean": float(hindsight.mean()),
        }

    uniform_trajectories = confirmation_trajectories["stationary_uniform"]
    full_findings = uniform_trajectories.sum(axis=1)
    for rule_class in RULE_CLASSES:
        prefix_findings = np.asarray(
            [
                evaluate_rule(rule_class, rewards, pull_cost=0.0).findings
                for rewards in uniform_trajectories
            ]
        )
        zero_cost_sanity = zero_cost_sanity and bool(
            np.all(full_findings >= prefix_findings)
        )

    swinging_rules = [
        rule_name
        for rule_name, by_shape in statuses.items()
        if "viable" in by_shape.values()
        and "disqualified" in by_shape.values()
    ]
    fixed_budget_viable = "viable" in statuses["FixedBudget"].values()
    efficient_adaptive_evidence: list[dict[str, object]] = []
    for rule_name in ADAPTIVE_RULE_NAMES:
        for shape in SHAPES:
            mean_pulls = float(
                confirmation[shape][rule_name]["pulls"].mean()
            )
            if (
                statuses[rule_name][shape] == "viable"
                and mean_pulls <= 0.80 * BUDGET
            ):
                efficient_adaptive_evidence.append(
                    {
                        "rule": rule_name,
                        "shape": shape,
                        "mean_pulls": mean_pulls,
                        "budget_fraction": mean_pulls / BUDGET,
                    }
                )

    conditions = {
        "shared_prefix_sanity_passes": bool(zero_cost_sanity),
        "all_reference_means_positive": bool(positive_references),
        "at_least_one_rule_swings": bool(swinging_rules),
        "fixed_budget_viable_somewhere": bool(fixed_budget_viable),
        "efficient_adaptive_stopper_viable_somewhere": bool(
            efficient_adaptive_evidence
        ),
    }
    passed = all(conditions.values())

    results = {
        "design": {
            "k": K,
            "maximum_budget": BUDGET,
            "pull_cost": PULL_COST,
            "finding_value": 1.0,
            "selection_trials_per_shape": N_SELECTION_PER_SHAPE,
            "confirmation_trials_per_shape": N_CONFIRMATION_PER_SHAPE,
            "shapes": SHAPES,
            "rules": tuple(RULE_BY_NAME),
            "trajectory_policy": "ThompsonSampling(prior=1.0)",
            "preregistration": "PREREGISTRATION.md",
        },
        "selection": {
            "locked_references": locked_references,
            "mean_utilities": {
                shape: {
                    rule_name: float(data["utility"].mean())
                    for rule_name, data in selection[shape].items()
                }
                for shape in SHAPES
            },
        },
        "confirmation": {
            "workloads": workload_results,
            "statuses": statuses,
            "swinging_rules": swinging_rules,
            "efficient_adaptive_evidence": efficient_adaptive_evidence,
            "zero_cost_sanity_passed": bool(zero_cost_sanity),
        },
        "verdict": {
            "conditions": conditions,
            "passed": bool(passed),
        },
    }

    print("\n" + "=" * 94)
    print("PRE-REGISTERED VERDICT")
    print("=" * 94)
    for condition, value in conditions.items():
        print(f"{condition}: {value}")
    print(f"swinging rules: {', '.join(swinging_rules) or 'none'}")
    print(
        "efficient adaptive evidence: "
        f"{len(efficient_adaptive_evidence)} rule/workload pairs"
    )
    print(f"POC 5: {'PASS' if passed else 'FAIL'}")

    destination = Path(__file__).with_name("results.json")
    destination.write_text(
        json.dumps(results, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"results: {destination}")
    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main())
