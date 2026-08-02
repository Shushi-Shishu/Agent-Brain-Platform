"""Blind search-answer scoring and pilot deblinding for POC 6c."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping


SCORE_LIMITS = {
    "claim_support": 30,
    "question_coverage": 20,
    "gap_handling": 15,
    "unsupported_claim_avoidance": 15,
    "practical_usefulness": 10,
    "citation_precision": 10,
}


def validate_blind_scores(
    scores: dict[str, Any],
    blind_cases: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    if scores.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if scores.get("stage") != "instrumentation_only":
        errors.append("stage must be instrumentation_only")
    expected = {
        case["case_id"]: {
            answer["blind_output_id"] for answer in case["answers"]
        }
        for case in blind_cases
    }
    cases = scores.get("cases")
    if not isinstance(cases, list):
        errors.append("cases must be a list")
        return errors
    seen_cases: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            errors.append("score case must be an object")
            continue
        case_id = case.get("case_id")
        if case_id not in expected:
            errors.append(f"unexpected case_id: {case_id}")
            continue
        if case_id in seen_cases:
            errors.append(f"duplicate score case: {case_id}")
        seen_cases.add(case_id)
        entries = case.get("scores")
        if not isinstance(entries, list):
            errors.append(f"{case_id}: scores must be a list")
            continue
        ids = {
            entry.get("blind_output_id")
            for entry in entries
            if isinstance(entry, dict)
        }
        if ids != expected[case_id]:
            errors.append(f"{case_id}: blind output IDs do not match")
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append(f"{case_id}: score entry must be an object")
                continue
            for name, maximum in SCORE_LIMITS.items():
                value = entry.get(name)
                if (
                    not isinstance(value, int)
                    or isinstance(value, bool)
                    or not 0 <= value <= maximum
                ):
                    errors.append(
                        f"{case_id}: {name} must be integer 0..{maximum}"
                    )
            if not isinstance(entry.get("critical_failure"), bool):
                errors.append(f"{case_id}: critical_failure must be boolean")
            if not isinstance(entry.get("notes"), str):
                errors.append(f"{case_id}: notes must be a string")
    if seen_cases != set(expected):
        errors.append("score cases do not cover the full blind batch")
    return errors


def deblind_score_rows(
    scores: dict[str, Any],
    mapping: Mapping[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in scores["cases"]:
        for entry in case["scores"]:
            blind_id = entry["blind_output_id"]
            arm = mapping.get(blind_id)
            if arm not in {"generic", "configured"}:
                raise ValueError(f"missing arm mapping for {blind_id}")
            component_total = sum(entry[name] for name in SCORE_LIMITS)
            rows.append(
                {
                    "task_id": case["case_id"],
                    "repeat": 1,
                    "arm": arm,
                    "quality": component_total,
                    "critical_failure": entry["critical_failure"],
                    "components": {
                        name: entry[name] for name in SCORE_LIMITS
                    },
                    "notes": entry["notes"],
                }
            )
    return rows


def pilot_descriptive_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe the diagnostic pilot without inferential efficacy claims."""

    by_arm: dict[str, list[float]] = defaultdict(list)
    critical: dict[str, int] = defaultdict(int)
    for row in rows:
        by_arm[row["arm"]].append(float(row["quality"]))
        critical[row["arm"]] += int(row["critical_failure"])
    by_task = defaultdict(dict)
    for row in rows:
        by_task[row["task_id"]][row["arm"]] = float(row["quality"])
    paired_deltas = sorted(
        scores["configured"] - scores["generic"]
        for scores in by_task.values()
        if {"generic", "configured"} <= scores.keys()
    )
    midpoint = len(paired_deltas) // 2
    if not paired_deltas:
        median_delta = None
    elif len(paired_deltas) % 2:
        median_delta = paired_deltas[midpoint]
    else:
        median_delta = (
            paired_deltas[midpoint - 1] + paired_deltas[midpoint]
        ) / 2
    return {
        "status": "instrumentation_only_no_efficacy_claim",
        "task_count": len({row["task_id"] for row in rows}),
        "arm_descriptives": {
            arm: {
                "mean_quality": sum(values) / len(values),
                "min_quality": min(values),
                "max_quality": max(values),
                "critical_failures": critical[arm],
            }
            for arm, values in sorted(by_arm.items())
        },
        "paired_descriptives": {
            "mean_quality_delta_configured_minus_generic": (
                sum(paired_deltas) / len(paired_deltas)
                if paired_deltas
                else None
            ),
            "median_quality_delta_configured_minus_generic": median_delta,
            "configured_wins": sum(delta > 0 for delta in paired_deltas),
            "ties": sum(delta == 0 for delta in paired_deltas),
            "configured_losses": sum(delta < 0 for delta in paired_deltas),
        },
    }


def evaluator_agreement(
    first_scores: dict[str, Any],
    second_scores: dict[str, Any],
) -> dict[str, Any]:
    """Compare two blind diagnostic evaluators without arm information."""

    def flattened(scores: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
        return {
            (case["case_id"], entry["blind_output_id"]): entry
            for case in scores["cases"]
            for entry in case["scores"]
        }

    first = flattened(first_scores)
    second = flattened(second_scores)
    if set(first) != set(second):
        raise ValueError("evaluators scored different blind outputs")
    absolute_differences: list[int] = []
    critical_matches = 0
    for key in sorted(first):
        first_total = sum(first[key][name] for name in SCORE_LIMITS)
        second_total = sum(second[key][name] for name in SCORE_LIMITS)
        absolute_differences.append(abs(first_total - second_total))
        critical_matches += int(
            first[key]["critical_failure"] == second[key]["critical_failure"]
        )

    preference_matches = 0
    preference_cases = 0
    case_ids = sorted({case_id for case_id, _ in first})
    for case_id in case_ids:
        blind_ids = sorted(
            blind_id
            for scored_case_id, blind_id in first
            if scored_case_id == case_id
        )
        if len(blind_ids) != 2:
            continue
        first_delta = sum(
            first[(case_id, blind_ids[0])][name] for name in SCORE_LIMITS
        ) - sum(
            first[(case_id, blind_ids[1])][name] for name in SCORE_LIMITS
        )
        second_delta = sum(
            second[(case_id, blind_ids[0])][name] for name in SCORE_LIMITS
        ) - sum(
            second[(case_id, blind_ids[1])][name] for name in SCORE_LIMITS
        )
        preference_cases += 1
        preference_matches += int(
            (first_delta > 0) == (second_delta > 0)
            and (first_delta < 0) == (second_delta < 0)
        )

    count = len(absolute_differences)
    return {
        "status": "diagnostic_inter_evaluator_agreement",
        "blind_output_count": count,
        "mean_absolute_total_score_difference": (
            sum(absolute_differences) / count if count else None
        ),
        "max_absolute_total_score_difference": (
            max(absolute_differences) if absolute_differences else None
        ),
        "critical_failure_agreement_rate": (
            critical_matches / count if count else None
        ),
        "pair_preference_agreement_rate": (
            preference_matches / preference_cases
            if preference_cases
            else None
        ),
    }
