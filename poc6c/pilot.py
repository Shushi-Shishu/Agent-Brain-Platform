"""Validation and blinding helpers for the POC 6c search pilot."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from corpus import FrozenCorpus


HERE = Path(__file__).resolve().parent
TASKS_PATH = HERE / "pilot" / "tasks_batch1.json"
BEHAVIORS = {"answer", "partial", "abstain", "error"}


def load_tasks() -> dict[str, Any]:
    return json.loads(TASKS_PATH.read_text(encoding="utf-8"))


def validate_pilot_output(
    output: dict[str, Any],
    corpus: FrozenCorpus,
) -> list[str]:
    errors: list[str] = []
    tasks = load_tasks()
    budget = tasks["per_case_budget"]
    expected_ids = [case["id"] for case in tasks["cases"]]
    if output.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if output.get("stage") != "instrumentation_only":
        errors.append("stage must be instrumentation_only")
    if output.get("arm") not in {"generic", "configured"}:
        errors.append("arm must be generic or configured")
    model_usage = output.get("model_usage")
    if not isinstance(model_usage, dict):
        errors.append("model_usage must be an object")
    else:
        for key in ("input_tokens", "output_tokens"):
            value = model_usage.get(key)
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value < 0
            ):
                errors.append(f"model_usage.{key} must be null or non-negative")
        cost = model_usage.get("provider_cost_usd")
        if cost is not None and (
            not isinstance(cost, (int, float))
            or isinstance(cost, bool)
            or cost < 0
        ):
            errors.append("provider_cost_usd must be null or non-negative")

    cases = output.get("cases")
    if not isinstance(cases, list):
        errors.append("cases must be a list")
        return errors
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if ids != expected_ids:
        errors.append("case IDs/order must exactly match Batch 1")

    for case in cases:
        if not isinstance(case, dict):
            errors.append("every case must be an object")
            continue
        case_id = case.get("id", "unknown")
        if case.get("behavior") not in BEHAVIORS:
            errors.append(f"{case_id}: invalid behavior")
        if not isinstance(case.get("answer"), str):
            errors.append(f"{case_id}: answer must be a string")
        gaps = case.get("declared_gaps")
        if not isinstance(gaps, list) or not all(
            isinstance(gap, str) for gap in gaps
        ):
            errors.append(f"{case_id}: declared_gaps must be a string list")

        trace = case.get("operational_trace")
        if not isinstance(trace, dict):
            errors.append(f"{case_id}: operational_trace must be an object")
            continue
        searches = trace.get("search_queries")
        reads = trace.get("documents_read")
        facets = trace.get("facets")
        if not isinstance(searches, list) or not all(
            isinstance(query, str) and query for query in searches
        ):
            errors.append(f"{case_id}: search_queries must be strings")
            searches = []
        if not isinstance(reads, list) or not all(
            isinstance(path, str) and path for path in reads
        ):
            errors.append(f"{case_id}: documents_read must be strings")
            reads = []
        if not isinstance(facets, list) or not all(
            isinstance(facet, str) for facet in facets
        ):
            errors.append(f"{case_id}: facets must be strings")
        if len(searches) > budget["max_search_queries"]:
            errors.append(f"{case_id}: search-query budget exceeded")
        if len(reads) > budget["max_documents_read"]:
            errors.append(f"{case_id}: document-read budget exceeded")
        if len(reads) != len(set(reads)):
            errors.append(f"{case_id}: duplicate document reads recorded")
        if not isinstance(trace.get("stop_reason"), str) or not trace.get(
            "stop_reason"
        ):
            errors.append(f"{case_id}: stop_reason is required")

        citations = case.get("citations")
        if not isinstance(citations, list):
            errors.append(f"{case_id}: citations must be a list")
            continue
        for citation_index, citation in enumerate(citations, start=1):
            citation_label = f"{case_id}: citation {citation_index}"
            if not isinstance(citation, dict):
                errors.append(f"{citation_label} must be an object")
                continue
            path = citation.get("path")
            excerpt = citation.get("supporting_excerpt")
            if not isinstance(path, str) or not isinstance(excerpt, str):
                errors.append(
                    f"{citation_label} path/excerpt must be strings"
                )
                continue
            try:
                note = corpus.read_note(path)
            except Exception:
                errors.append(
                    f"{citation_label} path is outside frozen corpus"
                )
                continue
            normalized_excerpt = " ".join(excerpt.split())
            normalized_content = " ".join(note["content"].split())
            if not normalized_excerpt or normalized_excerpt not in normalized_content:
                errors.append(
                    f"{citation_label} excerpt not found in note"
                )
            if path not in reads:
                errors.append(
                    f"{citation_label} note not recorded as read"
                )
    return errors


def blinded_cases(
    generic_output: dict[str, Any],
    configured_output: dict[str, Any],
    *,
    salt: str,
) -> list[dict[str, Any]]:
    """Return deterministic shuffled answers with all arm/trace data removed."""

    generic_by_id = {case["id"]: case for case in generic_output["cases"]}
    configured_by_id = {
        case["id"]: case for case in configured_output["cases"]
    }
    if set(generic_by_id) != set(configured_by_id):
        raise ValueError("pilot arms contain different cases")
    blinded: list[dict[str, Any]] = []
    questions = {
        case["id"]: case["question"] for case in load_tasks()["cases"]
    }
    for case_id in sorted(generic_by_id):
        pair = []
        for hidden_arm, source in (
            ("generic", generic_by_id[case_id]),
            ("configured", configured_by_id[case_id]),
        ):
            digest = hashlib.sha256(
                f"{salt}\0{case_id}\0{hidden_arm}".encode("utf-8")
            ).hexdigest()
            item = {
                "blind_output_id": "B-" + digest[:16].upper(),
                "behavior": source["behavior"],
                "answer": source["answer"],
                "citations": copy.deepcopy(source["citations"]),
                "declared_gaps": copy.deepcopy(source["declared_gaps"]),
                "_sort_key": digest,
            }
            pair.append(item)
        pair.sort(key=lambda item: item.pop("_sort_key"))
        blinded.append(
            {
                "case_id": case_id,
                "question": questions[case_id],
                "answers": pair,
            }
        )
    return blinded


def operational_summary(
    generic_output: dict[str, Any],
    configured_output: dict[str, Any],
) -> dict[str, Any]:
    """Describe observable pilot behavior without treating it as efficacy."""

    arm_summaries: dict[str, Any] = {}
    for output in (generic_output, configured_output):
        arm = output["arm"]
        cases = output["cases"]
        search_counts = [
            len(case["operational_trace"]["search_queries"]) for case in cases
        ]
        read_counts = [
            len(case["operational_trace"]["documents_read"]) for case in cases
        ]
        citation_counts = [len(case["citations"]) for case in cases]
        gap_counts = [len(case["declared_gaps"]) for case in cases]
        behavior_counts = Counter(case["behavior"] for case in cases)
        arm_summaries[arm] = {
            "case_count": len(cases),
            "mean_search_queries": sum(search_counts) / len(cases),
            "mean_documents_read": sum(read_counts) / len(cases),
            "mean_citations": sum(citation_counts) / len(cases),
            "mean_declared_gaps": sum(gap_counts) / len(cases),
            "behavior_counts": dict(sorted(behavior_counts.items())),
            "model_usage": copy.deepcopy(output["model_usage"]),
        }
    return {
        "status": "instrumentation_only_no_efficacy_claim",
        "arms": arm_summaries,
        "limitations": [
            "Batch 1 was seen during design and is excluded from confirmation.",
            "Provider token, cost, latency, and model identity are unaudited "
            "when reported as null or unknown.",
            "Collaboration agents share a host filesystem, so hard execution "
            "isolation is not proven.",
        ],
    }
