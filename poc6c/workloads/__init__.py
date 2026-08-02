"""Provider-independent workload fixture primitives for POC 6c."""

from .fixture_integrity import (
    ALLOWED_SPLITS,
    FORBIDDEN_PUBLIC_MARKERS,
    FileFingerprint,
    FixturePackage,
    FixtureTask,
    IntegrityError,
    LeakageCanary,
    PackageSnapshot,
    detect_canary_leakage,
    fixture_identity,
    snapshot_package,
    stable_hash_bytes,
    stable_hash_text,
    validate_fixture_task,
    validate_matched_public_copies,
    validate_split_isolation,
)

__all__ = [
    "ALLOWED_SPLITS",
    "FORBIDDEN_PUBLIC_MARKERS",
    "FileFingerprint",
    "FixturePackage",
    "FixtureTask",
    "IntegrityError",
    "LeakageCanary",
    "PackageSnapshot",
    "detect_canary_leakage",
    "fixture_identity",
    "snapshot_package",
    "stable_hash_bytes",
    "stable_hash_text",
    "validate_fixture_task",
    "validate_matched_public_copies",
    "validate_split_isolation",
]
