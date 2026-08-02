"""Trace and matching primitives for the POC 6c paired-agent benchmark.

This module deliberately contains no LLM-provider integration. It validates
provider-independent run records so generic and configured agents can be
compared under identical experimental conditions.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
ARMS = {"generic", "configured"}
ACCESS_MODES = {"vault_only", "vault_plus_web"}
EVENT_TYPES = {
    "decision",
    "vault_search",
    "web_search",
    "document_read",
    "tool_call",
    "evaluation",
    "stop",
    "answer",
    "error",
}
REQUIRED_INVARIANTS = (
    "task_id",
    "trial",
    "model_id",
    "model_version",
    "task_prompt_sha256",
    "data_snapshot_sha256",
    "access_mode",
    "tool_allowlist",
    "max_model_calls",
    "max_tool_calls",
    "max_input_tokens",
    "max_output_tokens",
    "max_wall_seconds",
)


def canonical_json(value: Any) -> str:
    """Return stable JSON for hashing and equality checks."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def blind_id(task_id: str, trial: int, arm: str, salt: str) -> str:
    """Create a stable reviewer identifier that does not reveal the arm."""

    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    payload = f"{salt}\0{task_id}\0{trial}\0{arm}"
    return "B-" + sha256_text(payload)[:16]


def validate_trace(trace: dict[str, Any]) -> list[str]:
    """Return every structural or experimental error in a run trace."""

    errors: list[str] = []
    required = {
        "schema_version",
        "run_id",
        "blind_id",
        "arm",
        "invariants",
        "policy",
        "events",
        "usage",
        "result",
    }
    missing = required - trace.keys()
    if missing:
        errors.append(f"missing trace fields: {sorted(missing)}")
        return errors

    if trace["schema_version"] != SCHEMA_VERSION:
        errors.append("unsupported schema_version")
    if trace["arm"] not in ARMS:
        errors.append("arm must be generic or configured")
    if not isinstance(trace["blind_id"], str) or not trace["blind_id"].startswith(
        "B-"
    ):
        errors.append("blind_id must use the B- prefix")

    invariants = trace["invariants"]
    if not isinstance(invariants, dict):
        errors.append("invariants must be an object")
        return errors
    invariant_missing = set(REQUIRED_INVARIANTS) - invariants.keys()
    if invariant_missing:
        errors.append(f"missing invariants: {sorted(invariant_missing)}")
    if invariants.get("access_mode") not in ACCESS_MODES:
        errors.append("invalid access_mode")
    allowlist = invariants.get("tool_allowlist")
    if not isinstance(allowlist, list) or not all(
        isinstance(tool, str) and tool for tool in allowlist
    ):
        errors.append("tool_allowlist must be a non-empty string list")
    for key in (
        "max_model_calls",
        "max_tool_calls",
        "max_input_tokens",
        "max_output_tokens",
        "max_wall_seconds",
    ):
        value = invariants.get(key)
        if not isinstance(value, int) or value < 0:
            errors.append(f"{key} must be a non-negative integer")

    policy = trace["policy"]
    if not isinstance(policy, dict):
        errors.append("policy must be an object")
    elif trace["arm"] == "generic" and policy.get("decision_architecture"):
        errors.append("generic arm cannot declare a decision architecture")
    elif trace["arm"] == "configured" and not policy.get(
        "decision_architecture"
    ):
        errors.append("configured arm requires a decision architecture")

    events = trace["events"]
    if not isinstance(events, list) or not events:
        errors.append("events must be a non-empty list")
    else:
        previous_sequence = 0
        for index, event in enumerate(events):
            if not isinstance(event, dict):
                errors.append(f"event {index} must be an object")
                continue
            sequence = event.get("sequence")
            if not isinstance(sequence, int) or sequence <= previous_sequence:
                errors.append("event sequences must strictly increase")
            else:
                previous_sequence = sequence
            if event.get("type") not in EVENT_TYPES:
                errors.append(f"invalid event type at sequence {sequence}")
        if not any(event.get("type") == "answer" for event in events):
            errors.append("trace requires an answer event")
        if not any(event.get("type") == "stop" for event in events):
            errors.append("trace requires a stop event")

    usage = trace["usage"]
    if not isinstance(usage, dict):
        errors.append("usage must be an object")
    else:
        for key in (
            "model_calls",
            "tool_calls",
            "input_tokens",
            "output_tokens",
            "wall_milliseconds",
        ):
            value = usage.get(key)
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value < 0
            ):
                errors.append(f"usage.{key} must be null or non-negative integer")
        budget_pairs = (
            ("model_calls", "max_model_calls"),
            ("tool_calls", "max_tool_calls"),
            ("input_tokens", "max_input_tokens"),
            ("output_tokens", "max_output_tokens"),
        )
        for actual_key, limit_key in budget_pairs:
            actual = usage.get(actual_key)
            limit = invariants.get(limit_key)
            if isinstance(actual, int) and isinstance(limit, int) and actual > limit:
                errors.append(f"{actual_key} exceeds matched budget")
        wall = usage.get("wall_milliseconds")
        wall_limit = invariants.get("max_wall_seconds")
        if (
            isinstance(wall, int)
            and isinstance(wall_limit, int)
            and wall > wall_limit * 1000
        ):
            errors.append("wall time exceeds matched budget")

    result = trace["result"]
    if not isinstance(result, dict):
        errors.append("result must be an object")
    else:
        if result.get("status") not in {
            "answer",
            "partial_answer",
            "abstain",
            "error",
        }:
            errors.append("invalid result status")
        if not isinstance(result.get("answer"), str):
            errors.append("result.answer must be a string")
        if not isinstance(result.get("citations"), list):
            errors.append("result.citations must be a list")
        if not isinstance(result.get("declared_gaps"), list):
            errors.append("result.declared_gaps must be a list")

    return errors


def matched_pair_errors(
    generic: dict[str, Any],
    configured: dict[str, Any],
) -> list[str]:
    """Return differences that invalidate a paired comparison."""

    errors: list[str] = []
    if generic.get("arm") != "generic":
        errors.append("first trace is not the generic arm")
    if configured.get("arm") != "configured":
        errors.append("second trace is not the configured arm")
    generic_invariants = generic.get("invariants", {})
    configured_invariants = configured.get("invariants", {})
    for key in REQUIRED_INVARIANTS:
        if generic_invariants.get(key) != configured_invariants.get(key):
            errors.append(f"pair invariant mismatch: {key}")
    if generic.get("blind_id") == configured.get("blind_id"):
        errors.append("paired arms require distinct blind identifiers")
    return errors


def usage_summary(trace: dict[str, Any]) -> dict[str, int | None]:
    """Summarize auditable actions without inventing missing provider usage."""

    events = trace.get("events", [])
    return {
        "vault_searches": sum(
            event.get("type") == "vault_search" for event in events
        ),
        "web_searches": sum(
            event.get("type") == "web_search" for event in events
        ),
        "documents_read": sum(
            event.get("type") == "document_read" for event in events
        ),
        "decisions_recorded": sum(
            event.get("type") == "decision" for event in events
        ),
        "model_calls": trace.get("usage", {}).get("model_calls"),
        "tool_calls": trace.get("usage", {}).get("tool_calls"),
        "input_tokens": trace.get("usage", {}).get("input_tokens"),
        "output_tokens": trace.get("usage", {}).get("output_tokens"),
        "wall_milliseconds": trace.get("usage", {}).get("wall_milliseconds"),
    }

