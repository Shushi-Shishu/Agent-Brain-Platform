"""Deterministic finding scorer for CRV-P003."""

from __future__ import annotations

import json
from pathlib import Path
import sys


TASK_ID = "CRV-P003"
SEVERITY_WEIGHT = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def evaluate(findings):
    if not isinstance(findings, list):
        raise ValueError("findings must be a list")
    inventory = json.loads(
        (Path(__file__).with_name("defect_inventory.json")).read_text(encoding="utf-8")
    )
    tolerance = inventory["location_tolerance_lines"]
    remaining = list(inventory["defects"])
    matched = []
    false_positive_indexes = []
    for finding_index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            false_positive_indexes.append(finding_index)
            continue
        line = finding.get("line")
        if isinstance(line, bool) or not isinstance(line, int):
            false_positive_indexes.append(finding_index)
            continue
        # Category labels are open vocabulary in the public schema, so a
        # semantically correct location cannot be rejected for using a synonym.
        match_index = next(
            (
                index
                for index, defect in enumerate(remaining)
                if finding.get("file") == defect["file"]
                and abs(line - defect["line"]) <= tolerance
            ),
            None,
        )
        if match_index is None:
            false_positive_indexes.append(finding_index)
        else:
            matched.append(remaining.pop(match_index))
    earned = sum(SEVERITY_WEIGHT[item["severity"]] for item in matched)
    possible = sum(
        SEVERITY_WEIGHT[item["severity"]] for item in inventory["defects"]
    )
    return {
        "task_id": TASK_ID,
        "true_positive_count": len(matched),
        "missed_count": len(remaining),
        "false_positive_count": len(false_positive_indexes),
        "matched_defect_ids": sorted(item["defect_id"] for item in matched),
        "false_positive_indexes": false_positive_indexes,
        "severity_weighted_recall": earned / possible if possible else 1.0,
    }


if __name__ == "__main__":
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(json.dumps(evaluate(payload), sort_keys=True))
