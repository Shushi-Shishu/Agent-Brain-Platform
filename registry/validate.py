"""
Registry schema validator.

Usage:
    python validate.py                # validates techniques.json, prints summary
    python validate.py --strict       # exits 1 on any warning too
"""

import json
import sys
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent / "techniques.json"

VALID_TYPES = {
    "executable-policy",
    "decision-interface",
    "evaluation-method",
    "runtime-integration",
    "background-math",
}

VALID_FRAMEWORKS = {
    "RL", "MDP", "bandit", "game-theory", "Bayesian",
    "LLM", "symbolic", "control", "multi-agent", "safety", "statistics",
}

VALID_BLOCK_IDS = {
    "explorer", "stopper", "critic", "router", "budget-allocator",
    "planner", "belief-updater", "scheduler", "memory-policy",
    "constraint", "coordinator", "state",
}

VALID_EVIDENCE_GRADES = {"A", "B", "C", "D", "X"}
VALID_EVIDENCE_SOURCES = {"empirical", "literature", "simulation", "expert", "none"}
VALID_DYNAMICS = {"stationary", "depleting", "drifting", "adversarial", "unknown"}
VALID_HORIZONS = {"one-shot", "episodic", "continuous"}
VALID_OBSERVABILITY = {"full", "partial", "delayed", "noisy", "none"}
VALID_LATENCY = {"sub-ms", "ms", "seconds", "minutes", None}
VALID_SCHEMA_VERSIONS = {1, 2}


def error(record_id, msg):
    return ("ERROR", record_id, msg)


def warn(record_id, msg):
    return ("WARN", record_id, msg)


def validate_record(r, all_ids):
    issues = []
    rid = r.get("id", "<missing-id>")

    # Required top-level fields
    for field in ("id", "name", "full_name", "schema_version", "description", "example_use_case"):
        if field not in r:
            issues.append(error(rid, f"missing required field '{field}'"))

    sv = r.get("schema_version")
    if sv not in VALID_SCHEMA_VERSIONS:
        issues.append(error(rid, f"schema_version must be 1 or 2, got {sv!r}"))

    # classification block (required for v2; warned for v1/legacy)
    cls = r.get("classification")
    if cls is None:
        if sv == 2:
            issues.append(error(rid, "missing 'classification' block (required for schema_version 2)"))
    else:
        t = cls.get("type")
        if t not in VALID_TYPES:
            issues.append(error(rid, f"classification.type {t!r} not in allowed set"))
        fw = cls.get("framework")
        if fw not in VALID_FRAMEWORKS:
            issues.append(error(rid, f"classification.framework {fw!r} not in allowed set"))
        blocks = cls.get("decision_blocks", [])
        for b in blocks:
            if b not in VALID_BLOCK_IDS:
                issues.append(error(rid, f"unknown decision_block id {b!r}"))
        if t == "executable-policy" and not blocks:
            issues.append(warn(rid, "executable-policy should declare at least one decision_block"))

    # assumptions block
    asmp = r.get("assumptions")
    if asmp is None:
        if sv == 2:
            issues.append(error(rid, "missing 'assumptions' block (required for schema_version 2)"))
    else:
        dyn = asmp.get("dynamics")
        if dyn not in VALID_DYNAMICS:
            issues.append(error(rid, f"assumptions.dynamics {dyn!r} not in allowed set"))
        hor = asmp.get("horizon")
        if hor not in VALID_HORIZONS:
            issues.append(error(rid, f"assumptions.horizon {hor!r} not in allowed set"))
        obs = asmp.get("required_observability")
        if obs not in VALID_OBSERVABILITY:
            issues.append(error(rid, f"assumptions.required_observability {obs!r} not in allowed set"))

    # baseline block
    baseline = r.get("baseline")
    if baseline is None:
        if sv == 2 and cls and cls.get("type") == "executable-policy":
            issues.append(warn(rid, "executable-policy should declare a baseline"))
    else:
        if not baseline.get("id"):
            issues.append(warn(rid, "baseline.id is empty"))
        if not baseline.get("description"):
            issues.append(warn(rid, "baseline.description is empty"))

    # evidence block
    ev = r.get("evidence")
    if ev is None:
        if sv == 2:
            issues.append(error(rid, "missing 'evidence' block (required for schema_version 2)"))
    else:
        grade = ev.get("grade")
        if grade not in VALID_EVIDENCE_GRADES:
            issues.append(error(rid, f"evidence.grade {grade!r} not in allowed set"))
        src = ev.get("source")
        if src not in VALID_EVIDENCE_SOURCES:
            issues.append(error(rid, f"evidence.source {src!r} not in allowed set"))
        if not ev.get("summary"):
            issues.append(warn(rid, "evidence.summary is empty"))

    # failure_modes
    if sv == 2:
        fm = r.get("failure_modes")
        if not fm:
            issues.append(warn(rid, "no failure_modes declared"))

    # incompatible_when
    if sv == 2 and "incompatible_when" not in r:
        issues.append(warn(rid, "incompatible_when not declared"))

    # cost_model
    cm = r.get("cost_model")
    if cm:
        lat = cm.get("latency_class")
        if lat not in VALID_LATENCY:
            issues.append(error(rid, f"cost_model.latency_class {lat!r} not in allowed set"))

    return issues


def validate(path=REGISTRY_PATH, strict=False):
    data = json.loads(path.read_text(encoding="utf-8"))
    techniques = data.get("techniques", [])

    all_ids = [r.get("id") for r in techniques]

    # Duplicate ID check
    seen = set()
    dupes = []
    for rid in all_ids:
        if rid in seen:
            dupes.append(rid)
        seen.add(rid)

    all_issues = []
    for r in techniques:
        all_issues.extend(validate_record(r, all_ids))

    errors = [i for i in all_issues if i[0] == "ERROR"]
    warnings = [i for i in all_issues if i[0] == "WARN"]

    print(f"Registry: {len(techniques)} techniques, {len(dupes)} duplicate IDs")
    if dupes:
        for d in dupes:
            print(f"  DUPE: {d}")

    if errors:
        print(f"\n{len(errors)} ERROR(s):")
        for _, rid, msg in errors:
            print(f"  [{rid}] {msg}")
    if warnings:
        print(f"\n{len(warnings)} WARNING(s):")
        for _, rid, msg in warnings:
            print(f"  [{rid}] {msg}")

    if not errors and not warnings:
        print("All checks passed.")

    # Summary by type
    type_counts = {}
    for r in techniques:
        cls = r.get("classification") or {}
        t = cls.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    print("\nBy classification type:")
    for t, n in sorted(type_counts.items()):
        print(f"  {t}: {n}")

    v2_count = sum(1 for r in techniques if r.get("schema_version") == 2)
    print(f"\nSchema v2 (fully curated): {v2_count}/{len(techniques)}")

    if dupes or errors:
        return False
    if strict and warnings:
        return False
    return True


if __name__ == "__main__":
    strict = "--strict" in sys.argv
    ok = validate(strict=strict)
    sys.exit(0 if ok else 1)
