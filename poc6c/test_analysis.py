"""Tests for task-clustered analysis and transaction economics."""

from __future__ import annotations

import random
import unittest

from analysis import (
    break_even_transactions,
    holm_adjust,
    paired_transaction_delta,
    portfolio_projection,
    relative_change,
    required_paired_tasks,
    sign_flip_pvalue,
    task_cluster_bootstrap_ci,
    task_deltas,
)


def rows_with_uplift(task_count: int = 6, repeats: int = 3, uplift: float = 5.0):
    rows = []
    for task in range(task_count):
        for repeat in range(1, repeats + 1):
            base = 50.0 + task + repeat / 10
            rows.extend(
                [
                    {
                        "task_id": f"T{task:02d}",
                        "repeat": repeat,
                        "arm": "generic",
                        "quality": base,
                    },
                    {
                        "task_id": f"T{task:02d}",
                        "repeat": repeat,
                        "arm": "configured",
                        "quality": base + uplift,
                    },
                ]
            )
    return rows


class AnalysisTests(unittest.TestCase):
    def test_identical_arms_have_zero_task_delta(self):
        deltas = task_deltas(rows_with_uplift(uplift=0.0), "quality")
        self.assertTrue(all(value == 0 for value in deltas.values()))

    def test_known_uplift_is_recovered_and_order_invariant(self):
        rows = rows_with_uplift(uplift=5.0)
        first = task_deltas(rows, "quality")
        random.Random(7).shuffle(rows)
        second = task_deltas(rows, "quality")
        self.assertEqual(first, second)
        self.assertTrue(all(value == 5.0 for value in first.values()))

    def test_duplicate_identical_repeats_do_not_create_new_tasks(self):
        rows = rows_with_uplift(task_count=4, repeats=1, uplift=3.0)
        duplicated = list(rows)
        for row in rows:
            copy = dict(row)
            copy["repeat"] = 2
            duplicated.append(copy)
        one = task_deltas(rows, "quality")
        two = task_deltas(duplicated, "quality")
        self.assertEqual(one, two)
        self.assertEqual(len(two), 4)

    def test_bootstrap_and_randomization_are_deterministic(self):
        deltas = task_deltas(rows_with_uplift(task_count=8), "quality")
        self.assertEqual(
            task_cluster_bootstrap_ci(deltas, seed=11),
            task_cluster_bootstrap_ci(deltas, seed=11),
        )
        self.assertEqual(
            sign_flip_pvalue(deltas, seed=11),
            sign_flip_pvalue(deltas, seed=11),
        )

    def test_relative_change_suppresses_zero_baseline(self):
        self.assertIsNone(relative_change(0.0, 5.0))
        self.assertEqual(relative_change(50.0, 55.0), 10.0)

    def test_power_count_uses_independent_tasks(self):
        count = required_paired_tasks(
            target_delta=5,
            paired_task_sd=10,
            unusable_fraction=0,
        )
        self.assertEqual(count, 32)

    def test_holm_adjustment(self):
        adjusted = holm_adjust({"a": 0.01, "b": 0.03, "c": 0.20})
        self.assertAlmostEqual(adjusted["a"], 0.03)
        self.assertAlmostEqual(adjusted["b"], 0.06)
        self.assertAlmostEqual(adjusted["c"], 0.20)

    def test_paired_transaction_delta_and_arm_swap(self):
        generic = {
            "monetized_outcome": 100,
            "model_tool_cost": 5,
            "human_minutes": 30,
            "hourly_rate": 60,
            "latency_cost": 2,
            "variable_monitoring_cost": 1,
        }
        configured = {
            **generic,
            "model_tool_cost": 4,
            "human_minutes": 20,
        }
        delta = paired_transaction_delta(generic, configured)
        self.assertEqual(delta, 11)
        self.assertEqual(paired_transaction_delta(configured, generic), -11)

    def test_break_even_handles_non_positive_value(self):
        self.assertEqual(
            break_even_transactions(
                one_time_cost=1000,
                delta_per_transaction=10,
            ),
            100,
        )
        self.assertIsNone(
            break_even_transactions(
                one_time_cost=1000,
                delta_per_transaction=0,
            )
        )

    def test_portfolio_projection_charges_one_time_cost_once(self):
        result = portfolio_projection(
            delta_per_transaction={"search": 2.0, "review": 5.0},
            monthly_volumes={
                "search": [100, 100],
                "review": [10, 10],
            },
            one_time_cost=300,
            monthly_fixed_costs=[25, 25],
        )
        self.assertEqual(result["payback_month"], 2)
        self.assertEqual(result["final_cumulative_value"], 150)


if __name__ == "__main__":
    unittest.main()
