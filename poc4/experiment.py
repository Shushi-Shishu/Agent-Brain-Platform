"""POC 4 cheap workload-identification experiment.

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
from policies import (  # noqa: E402
    DiscountedThompson,
    EpsilonGreedy,
    ExploreThenCommit,
    RoundRobin,
    ThompsonSampling,
    UCB1,
)


BASE_SEED = 20260728
CONFIRMATION_OFFSET = 4_000_000
POLICY_SEED_OFFSET = 17_000_000
K = 12
BUDGET = 48
N_SELECTION_PER_SHAPE = 500
N_CONFIRMATION_PER_SHAPE = 1_500
PROBE_FRACTIONS = (0.05, 0.10, 0.15)
PROBE_PULLS = tuple(math.ceil(fraction * BUDGET) for fraction in PROBE_FRACTIONS)
KNN_NEIGHBORS = 31
CV_FOLDS = 5
MATERIAL_UPLIFT = 0.02
Z_95 = 1.96

SHAPES = (
    "stationary_needle",
    "depleting_needle",
    "deceptive_depleting",
    "heterogeneous_depleting",
)

POLICY_CLASSES = (
    RoundRobin,
    ExploreThenCommit,
    EpsilonGreedy,
    UCB1,
    ThompsonSampling,
    DiscountedThompson,
)

DISPLAY_NAMES = {
    RoundRobin: "RoundRobin",
    ExploreThenCommit: "ExploreThenCommit",
    EpsilonGreedy: "EpsilonGreedy(e=0.1)",
    UCB1: "UCB1(c=2.0)",
    ThompsonSampling: "ThompsonSampling(prior=1.0)",
    DiscountedThompson: "DiscountedThompson(g=0.9)",
}

CLASS_BY_NAME = {DISPLAY_NAMES[policy]: policy for policy in POLICY_CLASSES}
CLASS_INDEX = {policy: index for index, policy in enumerate(POLICY_CLASSES)}


def scaled_size(multiplier: float, k: int, minimum: int) -> int:
    return max(minimum, int(round(multiplier * k)))


def build_regime(shape: str) -> Regime:
    """Build the locked K=12, B=48 POC 3 workload shapes."""
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


def probe_schedule(probe_pulls: int) -> tuple[int, ...]:
    if probe_pulls < 1 or probe_pulls > 2 * K:
        raise ValueError("probe pulls must be between 1 and 2K")
    unique_branches = math.ceil(probe_pulls / 2)
    first_pass = tuple(range(unique_branches))
    repeat_pass = tuple(range(probe_pulls - unique_branches))
    return first_pass + repeat_pass


@dataclass(frozen=True)
class ProbeTrace:
    branches: tuple[int, ...]
    rewards: tuple[int, ...]
    first_pass_size: int


def collect_probe(outcomes: np.ndarray, probe_pulls: int) -> ProbeTrace:
    schedule = probe_schedule(probe_pulls)
    env = PotentialOutcomeEnv(outcomes, BUDGET)
    rewards = tuple(env.pull(branch) for branch in schedule)
    return ProbeTrace(schedule, rewards, math.ceil(probe_pulls / 2))


def trace_features(trace: ProbeTrace, k: int = K) -> np.ndarray:
    counts: dict[int, int] = {}
    successes: dict[int, int] = {}
    per_branch_rewards: dict[int, list[int]] = {}
    for branch, reward in zip(trace.branches, trace.rewards, strict=True):
        counts[branch] = counts.get(branch, 0) + 1
        successes[branch] = successes.get(branch, 0) + reward
        per_branch_rewards.setdefault(branch, []).append(reward)

    sampled = sorted(counts)
    branch_rates = np.asarray(
        [successes[branch] / counts[branch] for branch in sampled],
        dtype=float,
    )
    first_rewards = np.asarray(trace.rewards[: trace.first_pass_size], dtype=float)
    repeat_rewards = np.asarray(trace.rewards[trace.first_pass_size :], dtype=float)

    success_to_failure = 0
    failure_to_success = 0
    repeated = 0
    for rewards in per_branch_rewards.values():
        if len(rewards) < 2:
            continue
        repeated += 1
        success_to_failure += int(rewards[0] == 1 and rewards[1] == 0)
        failure_to_success += int(rewards[0] == 0 and rewards[1] == 1)

    repeat_rate = float(repeat_rewards.mean()) if len(repeat_rewards) else 0.0
    first_rate = float(first_rewards.mean())
    repeated_denominator = max(repeated, 1)
    return np.asarray(
        [
            float(np.mean(trace.rewards)),
            len(sampled) / k,
            sum(successes[branch] > 0 for branch in sampled) / len(sampled),
            float(branch_rates.max()),
            float(branch_rates.std(ddof=0)),
            first_rate,
            repeat_rate,
            repeat_rate - first_rate,
            success_to_failure / repeated_denominator,
            failure_to_success / repeated_denominator,
            max(successes.values()) / len(trace.rewards),
        ],
        dtype=float,
    )


class StandardizedKNN:
    def __init__(self, neighbors: int = KNN_NEIGHBORS):
        self.neighbors = neighbors
        self.mean: np.ndarray | None = None
        self.scale: np.ndarray | None = None
        self.x: np.ndarray | None = None
        self.y: np.ndarray | None = None
        self.labels: tuple[str, ...] = ()

    def fit(self, x: np.ndarray, y: np.ndarray) -> "StandardizedKNN":
        if x.ndim != 2 or y.ndim != 1 or len(x) != len(y):
            raise ValueError("invalid training arrays")
        self.mean = x.mean(axis=0)
        scale = x.std(axis=0, ddof=0)
        self.scale = np.where(scale > 0, scale, 1.0)
        self.x = (x - self.mean) / self.scale
        self.y = y.astype(str)
        self.labels = tuple(sorted(set(self.y.tolist())))
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        if self.x is None or self.y is None or self.mean is None or self.scale is None:
            raise RuntimeError("classifier is not fitted")
        query = np.atleast_2d(x)
        normalized = (query - self.mean) / self.scale
        predictions: list[str] = []
        neighbors = min(self.neighbors, len(self.x))
        for row in normalized:
            distances = np.sum((self.x - row) ** 2, axis=1)
            order = np.argsort(distances, kind="stable")[:neighbors]
            votes = {
                label: int(np.sum(self.y[order] == label))
                for label in self.labels
            }
            best_vote = max(votes.values())
            tied = [label for label in self.labels if votes[label] == best_vote]
            if len(tied) > 1:
                distance_sums = {
                    label: float(distances[order][self.y[order] == label].sum())
                    for label in tied
                }
                best_distance = min(distance_sums.values())
                tied = [
                    label
                    for label in tied
                    if math.isclose(
                        distance_sums[label],
                        best_distance,
                        rel_tol=0.0,
                        abs_tol=1e-12,
                    )
                ]
            predictions.append(sorted(tied)[0])
        return np.asarray(predictions, dtype=str)


def policy_seed(split_namespace: int, shape_index: int, trial_index: int, policy: type) -> int:
    return (
        POLICY_SEED_OFFSET
        + split_namespace * 10_000_000
        + shape_index * 1_000_000
        + trial_index * len(POLICY_CLASSES)
        + CLASS_INDEX[policy]
    )


def run_full_policy(policy_class: type, outcomes: np.ndarray, seed: int) -> int:
    env = PotentialOutcomeEnv(outcomes, BUDGET)
    policy = policy_class(K, np.random.default_rng(seed), BUDGET)
    total = 0
    while not env.done:
        branch = policy.select()
        reward = env.pull(branch)
        policy.update(branch, reward)
        total += reward
    return total


def run_probe_then_policy(
    policy_class: type,
    outcomes: np.ndarray,
    probe_pulls: int,
    seed: int,
) -> int:
    env = PotentialOutcomeEnv(outcomes, BUDGET)
    policy = policy_class(K, np.random.default_rng(seed), BUDGET)
    total = 0
    for branch in probe_schedule(probe_pulls):
        reward = env.pull(branch)
        policy.update(branch, reward)
        total += reward
    while not env.done:
        branch = policy.select()
        reward = env.pull(branch)
        policy.update(branch, reward)
        total += reward
    return total


def build_worlds(start_seed: int, trials_per_shape: int) -> dict[str, list[np.ndarray]]:
    worlds: dict[str, list[np.ndarray]] = {}
    for shape_index, shape in enumerate(SHAPES):
        regime = build_regime(shape)
        worlds[shape] = [
            build_trial_outcomes(
                regime,
                start_seed + shape_index * 100_000 + trial_index,
            )
            for trial_index in range(trials_per_shape)
        ]
    return worlds


def evaluate_candidates(
    worlds: dict[str, list[np.ndarray]],
    split_namespace: int,
) -> dict[str, dict[str, np.ndarray]]:
    scores: dict[str, dict[str, np.ndarray]] = {}
    for shape_index, shape in enumerate(SHAPES):
        scores[shape] = {}
        for policy_class in POLICY_CLASSES:
            name = DISPLAY_NAMES[policy_class]
            scores[shape][name] = np.asarray(
                [
                    run_full_policy(
                        policy_class,
                        outcomes,
                        policy_seed(
                            split_namespace,
                            shape_index,
                            trial_index,
                            policy_class,
                        ),
                    )
                    for trial_index, outcomes in enumerate(worlds[shape])
                ],
                dtype=float,
            )
    return scores


def lock_policy_choices(
    scores: dict[str, dict[str, np.ndarray]],
) -> tuple[str, dict[str, str], dict[str, object]]:
    mixture_means = {
        name: float(np.mean([scores[shape][name].mean() for shape in SHAPES]))
        for name in CLASS_BY_NAME
    }
    best_fixed = max(
        CLASS_BY_NAME,
        key=lambda name: (mixture_means[name], -list(CLASS_BY_NAME).index(name)),
    )
    oracle_map = {
        shape: max(
            CLASS_BY_NAME,
            key=lambda name: (
                float(scores[shape][name].mean()),
                -list(CLASS_BY_NAME).index(name),
            ),
        )
        for shape in SHAPES
    }
    details = {
        "equal_mixture_means": mixture_means,
        "per_shape_means": {
            shape: {
                name: float(values.mean())
                for name, values in scores[shape].items()
            }
            for shape in SHAPES
        },
    }
    return best_fixed, oracle_map, details


def build_probe_dataset(
    worlds: dict[str, list[np.ndarray]],
    probe_pulls: int,
) -> tuple[np.ndarray, np.ndarray, list[tuple[str, int]]]:
    features: list[np.ndarray] = []
    labels: list[str] = []
    metadata: list[tuple[str, int]] = []
    for shape in SHAPES:
        for trial_index, outcomes in enumerate(worlds[shape]):
            features.append(trace_features(collect_probe(outcomes, probe_pulls)))
            labels.append(shape)
            metadata.append((shape, trial_index))
    return np.vstack(features), np.asarray(labels, dtype=str), metadata


def cross_validated_predictions(
    x: np.ndarray,
    y: np.ndarray,
    metadata: list[tuple[str, int]],
) -> np.ndarray:
    predictions = np.empty(len(y), dtype=f"<U{max(map(len, SHAPES))}")
    trial_indices = np.asarray([trial_index for _, trial_index in metadata])
    for fold in range(CV_FOLDS):
        test = trial_indices % CV_FOLDS == fold
        train = ~test
        model = StandardizedKNN().fit(x[train], y[train])
        predictions[test] = model.predict(x[test])
    return predictions


def evaluate_oof_meta(
    worlds: dict[str, list[np.ndarray]],
    metadata: list[tuple[str, int]],
    predictions: np.ndarray,
    oracle_map: dict[str, str],
    probe_pulls: int,
) -> np.ndarray:
    values = np.zeros(len(metadata), dtype=float)
    shape_indices = {shape: index for index, shape in enumerate(SHAPES)}
    for index, ((shape, trial_index), predicted_shape) in enumerate(
        zip(metadata, predictions, strict=True)
    ):
        policy_class = CLASS_BY_NAME[oracle_map[str(predicted_shape)]]
        values[index] = run_probe_then_policy(
            policy_class,
            worlds[shape][trial_index],
            probe_pulls,
            policy_seed(
                1,
                shape_indices[shape],
                trial_index,
                policy_class,
            ),
        )
    return values


def mean_ci(values: np.ndarray) -> tuple[float, float, float]:
    mean = float(values.mean())
    half = Z_95 * float(values.std(ddof=1)) / math.sqrt(len(values))
    return mean, mean - half, mean + half


def comparison(candidate: np.ndarray, baseline: np.ndarray) -> dict[str, object]:
    mean_diff, low, high = mean_ci(candidate - baseline)
    uplift = float(candidate.mean() / baseline.mean() - 1.0)
    return {
        "candidate_mean": float(candidate.mean()),
        "baseline_mean": float(baseline.mean()),
        "mean_difference": mean_diff,
        "difference_ci95": [low, high],
        "relative_uplift_pct": 100.0 * uplift,
        "material_win": bool(uplift >= MATERIAL_UPLIFT and low > 0),
    }


def confusion_matrix(actual: np.ndarray, predicted: np.ndarray) -> dict[str, dict[str, int]]:
    return {
        actual_shape: {
            predicted_shape: int(
                np.sum((actual == actual_shape) & (predicted == predicted_shape))
            )
            for predicted_shape in SHAPES
        }
        for actual_shape in SHAPES
    }


def main() -> int:
    print("=" * 94)
    print("POC 4 - cheap workload identification")
    print(
        f"K={K} budget={BUDGET} | selection={N_SELECTION_PER_SHAPE}/shape "
        f"| confirmation={N_CONFIRMATION_PER_SHAPE}/shape"
    )
    print("=" * 94)

    selection_worlds = build_worlds(BASE_SEED, N_SELECTION_PER_SHAPE)
    selection_scores = evaluate_candidates(selection_worlds, split_namespace=1)
    best_fixed, oracle_map, selection_details = lock_policy_choices(selection_scores)
    print(f"locked best fixed: {best_fixed}")
    for shape in SHAPES:
        print(f"  oracle[{shape}] = {oracle_map[shape]}")

    fixed_selection = np.concatenate(
        [selection_scores[shape][best_fixed] for shape in SHAPES]
    )
    selection_probe_results: dict[int, dict[str, object]] = {}
    fitted_models: dict[int, StandardizedKNN] = {}

    for probe_pulls in PROBE_PULLS:
        x, y, metadata = build_probe_dataset(selection_worlds, probe_pulls)
        predictions = cross_validated_predictions(x, y, metadata)
        oof_scores = evaluate_oof_meta(
            selection_worlds,
            metadata,
            predictions,
            oracle_map,
            probe_pulls,
        )
        accuracy = float(np.mean(predictions == y))
        policy_accuracy = float(
            np.mean(
                [
                    oracle_map[str(predicted)] == oracle_map[str(actual)]
                    for actual, predicted in zip(y, predictions, strict=True)
                ]
            )
        )
        selection_probe_results[probe_pulls] = {
            "oof_mean_reward": float(oof_scores.mean()),
            "oof_vs_best_fixed": comparison(oof_scores, fixed_selection),
            "oof_exact_accuracy": accuracy,
            "oof_policy_accuracy": policy_accuracy,
        }
        fitted_models[probe_pulls] = StandardizedKNN().fit(x, y)
        print(
            f"probe={probe_pulls:2d} "
            f"OOF mean={oof_scores.mean():.3f} "
            f"exact={100 * accuracy:.1f}% "
            f"policy={100 * policy_accuracy:.1f}%"
        )

    locked_probe = max(
        PROBE_PULLS,
        key=lambda pulls: (
            selection_probe_results[pulls]["oof_mean_reward"],
            -pulls,
        ),
    )
    print(f"locked probe: {locked_probe} pulls")

    confirmation_worlds = build_worlds(
        BASE_SEED + CONFIRMATION_OFFSET,
        N_CONFIRMATION_PER_SHAPE,
    )
    strategy_scores: dict[str, dict[str, np.ndarray]] = {
        shape: {} for shape in SHAPES
    }
    fraction_results: dict[int, dict[str, object]] = {}

    for probe_pulls in PROBE_PULLS:
        x, y, metadata = build_probe_dataset(confirmation_worlds, probe_pulls)
        predictions = fitted_models[probe_pulls].predict(x)
        by_shape_predictions = {
            shape: predictions[
                np.asarray([actual == shape for actual, _ in metadata])
            ]
            for shape in SHAPES
        }

        flat_probe_fixed: list[np.ndarray] = []
        flat_probe_detected: list[np.ndarray] = []
        flat_probe_oracle: list[np.ndarray] = []
        per_shape: dict[str, dict[str, object]] = {}

        for shape_index, shape in enumerate(SHAPES):
            n_trials = len(confirmation_worlds[shape])
            probe_fixed = np.zeros(n_trials, dtype=float)
            probe_detected = np.zeros(n_trials, dtype=float)
            probe_oracle = np.zeros(n_trials, dtype=float)
            shape_predictions = by_shape_predictions[shape]
            for trial_index, outcomes in enumerate(confirmation_worlds[shape]):
                fixed_class = CLASS_BY_NAME[best_fixed]
                detected_class = CLASS_BY_NAME[
                    oracle_map[str(shape_predictions[trial_index])]
                ]
                oracle_class = CLASS_BY_NAME[oracle_map[shape]]
                probe_fixed[trial_index] = run_probe_then_policy(
                    fixed_class,
                    outcomes,
                    probe_pulls,
                    policy_seed(2, shape_index, trial_index, fixed_class),
                )
                probe_detected[trial_index] = run_probe_then_policy(
                    detected_class,
                    outcomes,
                    probe_pulls,
                    policy_seed(2, shape_index, trial_index, detected_class),
                )
                probe_oracle[trial_index] = run_probe_then_policy(
                    oracle_class,
                    outcomes,
                    probe_pulls,
                    policy_seed(2, shape_index, trial_index, oracle_class),
                )

            flat_probe_fixed.append(probe_fixed)
            flat_probe_detected.append(probe_detected)
            flat_probe_oracle.append(probe_oracle)
            per_shape[shape] = {
                "probe_fixed_mean": float(probe_fixed.mean()),
                "probe_detected_mean": float(probe_detected.mean()),
                "probe_oracle_mean": float(probe_oracle.mean()),
                "exact_accuracy": float(np.mean(shape_predictions == shape)),
                "policy_accuracy": float(
                    np.mean(
                        [
                            oracle_map[str(predicted)] == oracle_map[shape]
                            for predicted in shape_predictions
                        ]
                    )
                ),
            }

        actual = y
        fraction_results[probe_pulls] = {
            "exact_accuracy": float(np.mean(predictions == actual)),
            "policy_accuracy": float(
                np.mean(
                    [
                        oracle_map[str(predicted)] == oracle_map[str(true_shape)]
                        for true_shape, predicted in zip(actual, predictions, strict=True)
                    ]
                )
            ),
            "confusion_matrix": confusion_matrix(actual, predictions),
            "per_shape": per_shape,
            "_probe_fixed": np.concatenate(flat_probe_fixed),
            "_probe_detected": np.concatenate(flat_probe_detected),
            "_probe_oracle": np.concatenate(flat_probe_oracle),
        }
        print(
            f"confirm probe={probe_pulls:2d} "
            f"exact={100 * fraction_results[probe_pulls]['exact_accuracy']:.1f}% "
            f"policy={100 * fraction_results[probe_pulls]['policy_accuracy']:.1f}%"
        )

    flat_best_fixed: list[np.ndarray] = []
    flat_free_oracle: list[np.ndarray] = []
    for shape_index, shape in enumerate(SHAPES):
        n_trials = len(confirmation_worlds[shape])
        best_values = np.zeros(n_trials, dtype=float)
        oracle_values = np.zeros(n_trials, dtype=float)
        fixed_class = CLASS_BY_NAME[best_fixed]
        oracle_class = CLASS_BY_NAME[oracle_map[shape]]
        for trial_index, outcomes in enumerate(confirmation_worlds[shape]):
            best_values[trial_index] = run_full_policy(
                fixed_class,
                outcomes,
                policy_seed(2, shape_index, trial_index, fixed_class),
            )
            oracle_values[trial_index] = run_full_policy(
                oracle_class,
                outcomes,
                policy_seed(2, shape_index, trial_index, oracle_class),
            )
        strategy_scores[shape]["best_fixed"] = best_values
        strategy_scores[shape]["free_oracle"] = oracle_values
        flat_best_fixed.append(best_values)
        flat_free_oracle.append(oracle_values)

    best_fixed_values = np.concatenate(flat_best_fixed)
    free_oracle_values = np.concatenate(flat_free_oracle)
    locked = fraction_results[locked_probe]
    probe_fixed_values = locked["_probe_fixed"]
    probe_detected_values = locked["_probe_detected"]
    probe_oracle_values = locked["_probe_oracle"]

    comparisons = {
        "free_oracle_vs_best_fixed": comparison(
            free_oracle_values,
            best_fixed_values,
        ),
        "probe_oracle_vs_probe_fixed": comparison(
            probe_oracle_values,
            probe_fixed_values,
        ),
        "probe_detected_vs_probe_fixed": comparison(
            probe_detected_values,
            probe_fixed_values,
        ),
        "probe_detected_vs_best_fixed": comparison(
            probe_detected_values,
            best_fixed_values,
        ),
    }
    conditions = {
        "selection_opportunity_exists": comparisons[
            "free_oracle_vs_best_fixed"
        ]["material_win"],
        "opportunity_survives_probe_cost": comparisons[
            "probe_oracle_vs_probe_fixed"
        ]["material_win"],
        "detection_creates_value": comparisons[
            "probe_detected_vs_probe_fixed"
        ]["material_win"],
        "net_task_value_positive": comparisons[
            "probe_detected_vs_best_fixed"
        ]["material_win"],
    }
    passed = all(conditions.values())

    oracle_gain = float(free_oracle_values.mean() - best_fixed_values.mean())
    captured_gain = (
        float(probe_detected_values.mean() - best_fixed_values.mean()) / oracle_gain
        if oracle_gain != 0
        else None
    )

    serializable_fraction_results = {}
    for probe_pulls, data in fraction_results.items():
        serializable_fraction_results[str(probe_pulls)] = {
            key: value
            for key, value in data.items()
            if not key.startswith("_")
        }
        serializable_fraction_results[str(probe_pulls)]["comparisons"] = {
            "detected_vs_probe_fixed": comparison(
                data["_probe_detected"],
                data["_probe_fixed"],
            ),
            "detected_vs_best_fixed": comparison(
                data["_probe_detected"],
                best_fixed_values,
            ),
            "probe_oracle_vs_probe_fixed": comparison(
                data["_probe_oracle"],
                data["_probe_fixed"],
            ),
        }

    results = {
        "design": {
            "k": K,
            "budget": BUDGET,
            "shapes": SHAPES,
            "probe_fractions": PROBE_FRACTIONS,
            "probe_pulls": PROBE_PULLS,
            "selection_trials_per_shape": N_SELECTION_PER_SHAPE,
            "confirmation_trials_per_shape": N_CONFIRMATION_PER_SHAPE,
            "knn_neighbors": KNN_NEIGHBORS,
            "cv_folds": CV_FOLDS,
            "material_uplift_floor_pct": 100 * MATERIAL_UPLIFT,
            "preregistration": "PREREGISTRATION.md",
        },
        "locked_choices": {
            "best_fixed_policy": best_fixed,
            "oracle_policy_by_shape": oracle_map,
            "probe_pulls": locked_probe,
        },
        "selection": {
            "candidate_results": selection_details,
            "probe_results": {
                str(pulls): data
                for pulls, data in selection_probe_results.items()
            },
        },
        "confirmation": {
            "probe_results": serializable_fraction_results,
            "primary_comparisons": comparisons,
            "per_shape_free_strategy_means": {
                shape: {
                    name: float(values.mean())
                    for name, values in strategy_scores[shape].items()
                }
                for shape in SHAPES
            },
            "free_oracle_gain_captured_fraction": captured_gain,
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
    print(
        "locked detector accuracy: "
        f"{100 * locked['exact_accuracy']:.1f}% exact, "
        f"{100 * locked['policy_accuracy']:.1f}% policy"
    )
    for name, data in comparisons.items():
        print(
            f"{name}: uplift={data['relative_uplift_pct']:.2f}% "
            f"CI=[{data['difference_ci95'][0]:.3f}, "
            f"{data['difference_ci95'][1]:.3f}] "
            f"material={data['material_win']}"
        )
    print(f"POC 4: {'PASS' if passed else 'FAIL'}")

    destination = Path(__file__).with_name("results.json")
    destination.write_text(
        json.dumps(results, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"results: {destination}")
    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main())
