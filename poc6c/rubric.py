"""
R07 — Rubric calibration support for the POC 6c search confirmation.

Verifies:
  - the EVALUATION_RUBRIC_V1.md file exists and its content hash matches the
    preregistered value;
  - all six scoring dimensions are present with the correct max points;
  - total possible score equals 100;
  - anchor points within each dimension are non-negative and do not exceed
    the dimension maximum;
  - no dimension anchor is negative;
  - the critical-failure flag definition is present.

Calibration scope (PLAN.md R07):
  This module operates only on the frozen rubric text and its preregistered
  hash.  It MUST NOT be called with confirmation outputs; calibration must
  use non-confirmation pilot material only (pilot/blind/batch1_v2_*.json).
  The module does not produce scores — it verifies that the rubric is
  structurally sound and hash-stable before any confirmation run starts.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Preregistered rubric artifact identity (from PREREGISTRATION_DRAFT.md)
# ---------------------------------------------------------------------------

RUBRIC_PATH = Path(__file__).resolve().parent / "confirmation" / "EVALUATION_RUBRIC_V1.md"

EXPECTED_RUBRIC_SHA256 = (
    "3B1913ACFE347B9515D1C9946F47854D77E1F20DD2044B13210425AC54B264F8"
)

# Scoring dimensions and their maximum points as declared in the rubric text.
EXPECTED_DIMENSIONS: dict[str, int] = {
    "claim_support":             30,
    "question_coverage":         20,
    "gap_handling":              15,
    "unsupported_claim_avoidance": 15,
    "practical_usefulness":      10,
    "citation_precision":        10,
}

EXPECTED_TOTAL = 100  # sum of all dimension maxima

# Anchors present in the rubric text (dimension_key -> set of anchor scores)
# These are verified structurally: each must be >= 0 and <= dimension max.
EXPECTED_ANCHORS: dict[str, set[int]] = {
    "claim_support":             {0, 8, 18, 24, 30},
    "question_coverage":         {0, 4, 10, 16, 20},
    "gap_handling":              {0, 4, 8, 12, 15},
    "unsupported_claim_avoidance": {0, 4, 8, 12, 15},
    "practical_usefulness":      {0, 2, 5, 8, 10},
    "citation_precision":        {0, 2, 5, 8, 10},
}


# ---------------------------------------------------------------------------
# Hash helper
# ---------------------------------------------------------------------------

def _sha256_text(path: Path) -> str:
    return hashlib.sha256(
        path.read_text(encoding="utf-8").encode("utf-8")
    ).hexdigest().upper()


# ---------------------------------------------------------------------------
# Structural rubric validation
# ---------------------------------------------------------------------------

def _parse_dimension_maxima(text: str) -> dict[str, int]:
    """
    Extract '## dimension_name — 0 to N' declarations from the rubric.
    Returns {normalised_key: N}.
    """
    pattern = re.compile(
        r"^##\s+(.+?)\s+—\s+0\s+to\s+(\d+)", re.MULTILINE
    )
    result: dict[str, int] = {}
    for match in pattern.finditer(text):
        raw_name = match.group(1).strip().lower()
        key = re.sub(r"[^a-z0-9]+", "_", raw_name).strip("_")
        result[key] = int(match.group(2))
    return result


def _parse_anchor_scores(text: str, dimension_key: str, max_score: int) -> set[int]:
    """
    Find '- **N:**' anchor lines in the rubric section for a dimension.
    Returns the set of integer anchor scores found.

    Handles headings that use hyphens within the dimension name
    (e.g. 'Unsupported-claim avoidance' for 'unsupported_claim_avoidance').
    """
    # Build a pattern that matches each word with optional intervening
    # hyphens or spaces, so 'unsupported_claim_avoidance' finds both
    # 'Unsupported claim avoidance' and 'Unsupported-claim avoidance'.
    words = dimension_key.split("_")
    word_pattern = r"[\s\-]+".join(re.escape(w) for w in words)
    heading_pattern = re.compile(
        r"^##\s+.*?" + word_pattern + r".*?$",
        re.IGNORECASE | re.MULTILINE,
    )
    match = heading_pattern.search(text)
    if not match:
        return set()
    section_start = match.end()
    # Section ends at next '##' or end of text
    next_section = re.search(r"^##\s+", text[section_start:], re.MULTILINE)
    section_end = section_start + next_section.start() if next_section else len(text)
    section = text[section_start:section_end]
    anchor_pattern = re.compile(r"-\s+\*\*(\d+):\*\*")
    return {int(m.group(1)) for m in anchor_pattern.finditer(section)}


class RubricError(ValueError):
    """Raised when the rubric file fails a structural or hash check."""


def validate_rubric(path: Path | None = None) -> list[str]:
    """
    Return a list of validation errors.  Empty list means the rubric is
    structurally correct and hash-stable.

    Checks performed:
      1. File exists.
      2. SHA-256 matches the preregistered value.
      3. All six dimensions are present with the correct max scores.
      4. Total possible score equals 100.
      5. Each dimension's anchor scores are non-negative and ≤ max.
      6. Critical-failure flag definition is present.
    """
    rubric_path = path or RUBRIC_PATH
    errors: list[str] = []

    if not rubric_path.exists():
        errors.append(f"rubric file not found: {rubric_path}")
        return errors  # cannot continue without the file

    actual_hash = _sha256_text(rubric_path)
    if actual_hash != EXPECTED_RUBRIC_SHA256:
        errors.append(
            f"rubric hash mismatch: expected {EXPECTED_RUBRIC_SHA256}, "
            f"got {actual_hash}"
        )
        # Hash mismatch means the text changed — still check structure.

    text = rubric_path.read_text(encoding="utf-8")

    found_dims = _parse_dimension_maxima(text)
    for dim_key, expected_max in EXPECTED_DIMENSIONS.items():
        readable = dim_key.replace("_", " ")
        if dim_key not in found_dims:
            errors.append(f"dimension missing from rubric: {readable}")
        elif found_dims[dim_key] != expected_max:
            errors.append(
                f"dimension '{readable}' max changed: "
                f"expected {expected_max}, found {found_dims[dim_key]}"
            )

    total = sum(found_dims.get(k, 0) for k in EXPECTED_DIMENSIONS)
    if total != EXPECTED_TOTAL:
        errors.append(
            f"rubric total score changed: expected {EXPECTED_TOTAL}, got {total}"
        )

    for dim_key, expected_anchors in EXPECTED_ANCHORS.items():
        max_score = EXPECTED_DIMENSIONS.get(dim_key, 0)
        found_anchors = _parse_anchor_scores(text, dim_key, max_score)
        # Each anchor must be non-negative and within the declared max.
        for anchor in found_anchors:
            if anchor < 0:
                errors.append(f"negative anchor {anchor} in dimension '{dim_key}'")
            elif anchor > max_score:
                errors.append(
                    f"anchor {anchor} exceeds max {max_score} "
                    f"in dimension '{dim_key}'"
                )
        missing = expected_anchors - found_anchors
        if missing:
            errors.append(
                f"dimension '{dim_key}' missing anchor(s): {sorted(missing)}"
            )

    if "critical_failure" not in text.lower():
        errors.append("rubric missing critical_failure definition")

    return errors


def rubric_calibration_evidence(path: Path | None = None) -> dict[str, Any]:
    """
    Return a structured calibration record suitable for embedding in the
    readiness matrix.  Does NOT produce scores — only verifies structure.

    Must be called with non-confirmation material only.
    """
    rubric_path = path or RUBRIC_PATH
    errors = validate_rubric(rubric_path)

    actual_hash: str | None = None
    if rubric_path.exists():
        actual_hash = _sha256_text(rubric_path)

    return {
        "requirement": "R07",
        "check": "rubric_calibration",
        "rubric_path": str(rubric_path),
        "expected_sha256": EXPECTED_RUBRIC_SHA256,
        "actual_sha256": actual_hash,
        "hash_match": actual_hash == EXPECTED_RUBRIC_SHA256,
        "dimensions_found": list(EXPECTED_DIMENSIONS.keys()),
        "expected_total": EXPECTED_TOTAL,
        "errors": errors,
        "passed": len(errors) == 0,
        "calibration_scope": "non_confirmation_only",
        "selection_limitation": (
            "This rubric calibration uses frozen text only. "
            "No confirmation outputs have been scored. "
            "All ablation results remain labeled selection-only."
        ),
    }
