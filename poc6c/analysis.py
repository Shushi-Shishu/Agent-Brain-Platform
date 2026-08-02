"""Task-clustered statistics and transaction economics for POC 6c."""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import NormalDist
from typing import Iterable, Mapping

import numpy as np


def _finite_number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def task_deltas(
    rows: Iterable[Mapping[str, object]],
    metric: str,
) -> dict[str, float]:
    """Average paired repeat differences within each independent task.

    Repeats estimate stochasticity. They do not become independent samples.
    """

    grouped: dict[tuple[str, int], dict[str, float]] = defaultdict(dict)
    for row in rows:
        task_id = row.get("task_id")
        repeat = row.get("repeat")
        arm = row.get("arm")
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("task_id must be a non-empty string")
        if not isinstance(repeat, int) or repeat < 1:
            raise ValueError("repeat must be a positive integer")
        if arm not in {"generic", "configured"}:
            raise ValueError("arm must be generic or configured")
        key = (task_id, repeat)
        if arm in grouped[key]:
            raise ValueError(f"duplicate arm record for {key}")
        grouped[key][str(arm)] = _finite_number(row.get(metric), metric)

    per_task: dict[str, list[float]] = defaultdict(list)
    for key, arms in grouped.items():
        if set(arms) != {"generic", "configured"}:
            raise ValueError(f"incomplete paired repeat: {key}")
        per_task[key[0]].append(arms["configured"] - arms["generic"])
    return {
        task_id: float(np.mean(repeat_deltas))
        for task_id, repeat_deltas in sorted(per_task.items())
    }


def task_cluster_bootstrap_ci(
    deltas: Mapping[str, float],
    *,
    confidence: float = 0.95,
    resamples: int = 20_000,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Bootstrap the mean by resampling tasks, never individual repeats."""

    if not 0 < confidence < 1:
        raise ValueError("confidence must be between zero and one")
    if resamples < 1_000:
        raise ValueError("resamples must be at least 1000")
    values = np.asarray(list(deltas.values()), dtype=float)
    if values.size < 2:
        raise ValueError("at least two independent tasks are required")
    rng = np.random.default_rng(seed)
    sample_indices = rng.integers(
        0,
        values.size,
        size=(resamples, values.size),
    )
    means = values[sample_indices].mean(axis=1)
    alpha = 1.0 - confidence
    return (
        float(values.mean()),
        float(np.quantile(means, alpha / 2)),
        float(np.quantile(means, 1 - alpha / 2)),
    )


def sign_flip_pvalue(
    deltas: Mapping[str, float],
    *,
    permutations: int = 50_000,
    seed: int = 0,
) -> float:
    """Two-sided paired randomization sensitivity test at the task level."""

    values = np.asarray(list(deltas.values()), dtype=float)
    if values.size < 2:
        raise ValueError("at least two independent tasks are required")
    observed = abs(float(values.mean()))
    if values.size <= 18:
        assignments = np.arange(2**values.size, dtype=np.uint64)[:, None]
        bits = (assignments >> np.arange(values.size, dtype=np.uint64)) & 1
        signs = np.where(bits == 0, -1.0, 1.0)
    else:
        if permutations < 1_000:
            raise ValueError("permutations must be at least 1000")
        rng = np.random.default_rng(seed)
        signs = rng.choice(
            np.asarray([-1.0, 1.0]),
            size=(permutations, values.size),
        )
    randomized = np.abs((signs * values).mean(axis=1))
    return float((np.count_nonzero(randomized >= observed) + 1) / (len(randomized) + 1))


def relative_change(
    generic: float,
    configured: float,
    *,
    minimum_denominator: float = 1e-9,
) -> float | None:
    generic_value = _finite_number(generic, "generic")
    configured_value = _finite_number(configured, "configured")
    if abs(generic_value) <= minimum_denominator:
        return None
    return 100.0 * (configured_value - generic_value) / abs(generic_value)


def required_paired_tasks(
    *,
    target_delta: float,
    paired_task_sd: float,
    alpha: float = 0.05,
    power: float = 0.80,
    unusable_fraction: float = 0.10,
) -> int:
    """Normal-approximation planning count for independent paired tasks."""

    delta = abs(_finite_number(target_delta, "target_delta"))
    sd = abs(_finite_number(paired_task_sd, "paired_task_sd"))
    if delta == 0 or sd == 0:
        raise ValueError("target_delta and paired_task_sd must be positive")
    if not 0 < alpha < 1 or not 0 < power < 1:
        raise ValueError("alpha and power must be between zero and one")
    if not 0 <= unusable_fraction < 1:
        raise ValueError("unusable_fraction must be in [0, 1)")
    normal = NormalDist()
    z_alpha = normal.inv_cdf(1 - alpha / 2)
    z_power = normal.inv_cdf(power)
    usable = ((z_alpha + z_power) * sd / delta) ** 2
    return math.ceil(usable / (1 - unusable_fraction))


def holm_adjust(pvalues: Mapping[str, float]) -> dict[str, float]:
    """Return Holm-adjusted p-values while preserving hypothesis names."""

    ordered = sorted(
        (
            (name, _finite_number(value, f"pvalue[{name}]"))
            for name, value in pvalues.items()
        ),
        key=lambda pair: pair[1],
    )
    count = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for index, (name, value) in enumerate(ordered):
        if not 0 <= value <= 1:
            raise ValueError("p-values must lie in [0, 1]")
        candidate = min(1.0, (count - index) * value)
        running = max(running, candidate)
        adjusted[name] = running
    return adjusted


def transaction_value(row: Mapping[str, object]) -> float:
    """Expected/realized business value for one arm on one transaction."""

    monetized_outcome = _finite_number(
        row.get("monetized_outcome"),
        "monetized_outcome",
    )
    model_tool_cost = _finite_number(
        row.get("model_tool_cost"),
        "model_tool_cost",
    )
    human_minutes = _finite_number(row.get("human_minutes"), "human_minutes")
    hourly_rate = _finite_number(row.get("hourly_rate"), "hourly_rate")
    latency_cost = _finite_number(row.get("latency_cost"), "latency_cost")
    variable_monitoring = _finite_number(
        row.get("variable_monitoring_cost"),
        "variable_monitoring_cost",
    )
    return (
        monetized_outcome
        - model_tool_cost
        - human_minutes / 60.0 * hourly_rate
        - latency_cost
        - variable_monitoring
    )


def paired_transaction_delta(
    generic: Mapping[str, object],
    configured: Mapping[str, object],
) -> float:
    return transaction_value(configured) - transaction_value(generic)


def portfolio_projection(
    *,
    delta_per_transaction: Mapping[str, float],
    monthly_volumes: Mapping[str, list[int]],
    one_time_cost: float,
    monthly_fixed_costs: list[float],
) -> dict[str, object]:
    """Project cumulative value using the declared workload mix and volumes."""

    if set(delta_per_transaction) != set(monthly_volumes):
        raise ValueError("workloads differ between deltas and volumes")
    month_counts = {len(values) for values in monthly_volumes.values()}
    if len(month_counts) != 1:
        raise ValueError("every workload must provide the same month count")
    months = next(iter(month_counts), 0)
    if len(monthly_fixed_costs) != months:
        raise ValueError("monthly_fixed_costs length must match volumes")
    cumulative = -_finite_number(one_time_cost, "one_time_cost")
    monthly: list[dict[str, float | int]] = []
    payback_month: int | None = None
    for index in range(months):
        gross = 0.0
        for workload, delta in delta_per_transaction.items():
            volume = monthly_volumes[workload][index]
            if not isinstance(volume, int) or volume < 0:
                raise ValueError("monthly volumes must be non-negative integers")
            gross += volume * _finite_number(delta, f"delta[{workload}]")
        fixed = _finite_number(monthly_fixed_costs[index], "monthly_fixed_cost")
        net = gross - fixed
        cumulative += net
        if payback_month is None and cumulative > 0:
            payback_month = index + 1
        monthly.append(
            {
                "month": index + 1,
                "gross_incremental_value": gross,
                "fixed_cost": fixed,
                "net_incremental_value": net,
                "cumulative_value": cumulative,
            }
        )
    return {
        "months": monthly,
        "payback_month": payback_month,
        "final_cumulative_value": cumulative,
    }


def break_even_transactions(
    *,
    one_time_cost: float,
    delta_per_transaction: float,
    variable_maintenance_per_transaction: float = 0.0,
) -> int | None:
    net_delta = _finite_number(
        delta_per_transaction,
        "delta_per_transaction",
    ) - _finite_number(
        variable_maintenance_per_transaction,
        "variable_maintenance_per_transaction",
    )
    if net_delta <= 0:
        return None
    return math.ceil(_finite_number(one_time_cost, "one_time_cost") / net_delta)

