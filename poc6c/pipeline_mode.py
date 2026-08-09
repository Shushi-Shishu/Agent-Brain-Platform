"""
POC 6c pipeline mode — explicit diagnostic vs production gate.

Two valid modes only:
  diagnostic  — synthetic tasks/providers/answers/scores; no live secrets required;
                 all outputs tagged diagnostic_synthetic_only; confirmation_ready=False
  production  — fail-closed before arm execution if any required attestation or
                 runtime evidence is absent, synthetic, test-only, stale, or mismatched
"""
from __future__ import annotations

import enum


class PipelineMode(str, enum.Enum):
    DIAGNOSTIC  = "diagnostic"
    PRODUCTION  = "production"


class InvalidMode(ValueError):
    """Raised when the mode value is missing, ambiguous, or unknown."""


def validate_mode(mode_str: str | None) -> PipelineMode:
    """
    Parse and return a PipelineMode.

    Raises InvalidMode for None, empty, or unrecognised values.
    Only 'diagnostic' and 'production' are accepted.
    """
    if not mode_str or not isinstance(mode_str, str):
        raise InvalidMode(
            "Pipeline mode must be 'diagnostic' or 'production'; "
            f"got {mode_str!r}."
        )
    cleaned = mode_str.strip().lower()
    try:
        return PipelineMode(cleaned)
    except ValueError:
        raise InvalidMode(
            f"Unknown pipeline mode {mode_str!r}. "
            "Only 'diagnostic' and 'production' are valid."
        )
