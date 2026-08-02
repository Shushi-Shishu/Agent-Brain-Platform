"""Sealed fixture integrity for POC 6c code workloads.

The benchmark gives an agent a public package while keeping tests, defect
inventories, mutations, and answer material in a private package.  This module
defines and validates that boundary without depending on an LLM provider or a
particular test framework.

Hashes are content-addressed and independent of filesystem enumeration order,
timestamps, permissions, and absolute checkout location.  Relative path names
remain part of a package hash because renaming a file changes the agent-visible
task.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence


ALLOWED_SPLITS = frozenset({"pilot", "selection", "confirmation"})
PACKAGE_ROLES = frozenset({"public", "private"})
FORBIDDEN_PUBLIC_MARKERS = ("hidden", "oracle", "mutant")
_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
_CANARY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class IntegrityError(ValueError):
    """Raised when a package cannot be fingerprinted safely."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def stable_hash_bytes(value: bytes) -> str:
    """Return an uppercase SHA-256 digest for bytes."""

    return hashlib.sha256(value).hexdigest().upper()


def stable_hash_text(value: str) -> str:
    """Return an uppercase SHA-256 digest for UTF-8 text."""

    return stable_hash_bytes(value.encode("utf-8"))


def _stable_hash_object(value: Any) -> str:
    return stable_hash_text(_canonical_json(value))


def _safe_relative_path(path: Path) -> str:
    text = path.as_posix()
    if path.is_absolute() or not text or text == ".":
        raise IntegrityError(f"unsafe package path: {text!r}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise IntegrityError(f"unsafe package path: {text!r}")
    return text


def _contains_marker(value: str | bytes) -> list[str]:
    haystack = value.lower() if isinstance(value, bytes) else value.casefold()
    markers: list[str] = []
    for marker in FORBIDDEN_PUBLIC_MARKERS:
        needle = marker.encode("ascii") if isinstance(value, bytes) else marker
        if needle in haystack:
            markers.append(marker)
    return markers


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _roots_overlap(first: Path, second: Path) -> bool:
    first_resolved = Path(first).resolve()
    second_resolved = Path(second).resolve()
    return (
        first_resolved == second_resolved
        or _is_relative_to(first_resolved, second_resolved)
        or _is_relative_to(second_resolved, first_resolved)
    )


@dataclass(frozen=True)
class FileFingerprint:
    """Stable identity of one regular package file."""

    path: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        _safe_relative_path(Path(self.path))
        if not isinstance(self.size_bytes, int) or self.size_bytes < 0:
            raise IntegrityError("size_bytes must be a non-negative integer")
        if not _SHA256_RE.fullmatch(self.sha256):
            raise IntegrityError("sha256 must be a 64-character uppercase digest")

    def canonical_record(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class PackageSnapshot:
    """Location-independent package snapshot."""

    files: tuple[FileFingerprint, ...]
    sha256: str

    def __post_init__(self) -> None:
        paths = [record.path for record in self.files]
        if paths != sorted(paths):
            raise IntegrityError("snapshot files must be sorted by path")
        if len(paths) != len(set(paths)):
            raise IntegrityError("snapshot contains duplicate paths")
        if not _SHA256_RE.fullmatch(self.sha256):
            raise IntegrityError("snapshot sha256 is invalid")
        expected = _stable_hash_object(
            {
                "schema": "poc6c-package-snapshot-v1",
                "files": [record.canonical_record() for record in self.files],
            }
        )
        if self.sha256 != expected:
            raise IntegrityError("snapshot sha256 does not match file records")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "poc6c-package-snapshot-v1",
            "sha256": self.sha256,
            "files": [record.canonical_record() for record in self.files],
        }


@dataclass(frozen=True)
class FixturePackage:
    """One side of a task fixture: agent-visible public or evaluator-private."""

    role: str
    root: Path

    def __post_init__(self) -> None:
        if self.role not in PACKAGE_ROLES:
            raise IntegrityError("package role must be public or private")
        object.__setattr__(self, "root", Path(self.root))


@dataclass(frozen=True)
class LeakageCanary:
    """Opaque private token used to detect accidental evaluator-data access.

    The token is intentionally supplied by the harness instead of generated
    here.  A caller may use a secret random value in real fixtures and a fixed
    value in deterministic tests.  Detection reports only ``canary_id`` so
    diagnostics do not echo the secret token.
    """

    canary_id: str
    token: str

    def __post_init__(self) -> None:
        if not _CANARY_ID_RE.fullmatch(self.canary_id):
            raise IntegrityError("invalid leakage canary id")
        if not isinstance(self.token, str) or len(self.token) < 16:
            raise IntegrityError("leakage canary token must contain 16+ characters")
        if self.token.isspace():
            raise IntegrityError("leakage canary token cannot be whitespace")

    @property
    def token_sha256(self) -> str:
        """Safe identity for logs and manifests; never returns the token."""

        return stable_hash_text(self.token)


@dataclass(frozen=True)
class FixtureTask:
    """A paired benchmark task with a sealed public/private package boundary."""

    task_id: str
    workload: str
    split: str
    public: FixturePackage
    private: FixturePackage
    canaries: tuple[LeakageCanary, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, str) or not self.task_id.strip():
            raise IntegrityError("task_id must be a non-empty string")
        if not isinstance(self.workload, str) or not self.workload.strip():
            raise IntegrityError("workload must be a non-empty string")
        if self.split not in ALLOWED_SPLITS:
            raise IntegrityError(f"unknown fixture split: {self.split!r}")
        if self.public.role != "public" or self.private.role != "private":
            raise IntegrityError("fixture packages are assigned to the wrong roles")
        canary_ids = [canary.canary_id for canary in self.canaries]
        canary_hashes = [canary.token_sha256 for canary in self.canaries]
        if len(canary_ids) != len(set(canary_ids)):
            raise IntegrityError("fixture has duplicate leakage canary ids")
        if len(canary_hashes) != len(set(canary_hashes)):
            raise IntegrityError("fixture has duplicate leakage canary tokens")


def snapshot_package(root: Path) -> PackageSnapshot:
    """Fingerprint every regular file under ``root``.

    Symlinks are rejected even when they point inside the package.  This makes
    a fixture self-contained and prevents a public package from indirectly
    reaching evaluator-only material.
    """

    root = Path(root)
    if not root.exists():
        raise IntegrityError(f"package root does not exist: {root}")
    if root.is_symlink():
        raise IntegrityError(f"package root cannot be a symlink: {root}")
    if not root.is_dir():
        raise IntegrityError(f"package root is not a directory: {root}")
    records: list[FileFingerprint] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root)
        relative_text = _safe_relative_path(relative)
        if path.is_symlink():
            raise IntegrityError(f"package contains a symlink: {relative_text}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise IntegrityError(f"package contains a non-regular file: {relative_text}")
        content = path.read_bytes()
        records.append(
            FileFingerprint(
                path=relative_text,
                size_bytes=len(content),
                sha256=stable_hash_bytes(content),
            )
        )
    records_tuple = tuple(sorted(records, key=lambda record: record.path))
    digest = _stable_hash_object(
        {
            "schema": "poc6c-package-snapshot-v1",
            "files": [record.canonical_record() for record in records_tuple],
        }
    )
    return PackageSnapshot(files=records_tuple, sha256=digest)


def _package_marker_errors(root: Path) -> list[str]:
    errors: list[str] = []
    root = Path(root)
    if not root.is_dir():
        return [f"public package root is not a directory: {root}"]
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root)
        relative_text = relative.as_posix()
        for part in relative.parts:
            if part.startswith("."):
                errors.append(f"public path is hidden: {relative_text}")
                break
        for marker in _contains_marker(relative_text):
            errors.append(
                f"public path contains forbidden marker {marker!r}: {relative_text}"
            )
        if path.is_file() and not path.is_symlink():
            content = path.read_bytes()
            for marker in _contains_marker(content):
                errors.append(
                    f"public content contains forbidden marker {marker!r}: "
                    f"{relative_text}"
                )
    return errors


def detect_canary_leakage(
    payload: str | bytes | Mapping[str, Any] | Sequence[Any],
    canaries: Iterable[LeakageCanary],
) -> tuple[str, ...]:
    """Return canary IDs whose secret tokens appear in an output or trace.

    Mappings and non-string sequences are serialized canonically so the same
    interface can scan answers, patches, event records, and provider payloads.
    The function never returns or embeds token values.
    """

    if isinstance(payload, bytes):
        content = payload
    elif isinstance(payload, str):
        content = payload.encode("utf-8")
    else:
        content = _canonical_json(payload).encode("utf-8")
    leaked = {
        canary.canary_id
        for canary in canaries
        if canary.token.encode("utf-8") in content
    }
    return tuple(sorted(leaked))


def _canary_boundary_errors(task: FixtureTask) -> list[str]:
    errors: list[str] = []
    try:
        public_snapshot = snapshot_package(task.public.root)
        private_snapshot = snapshot_package(task.private.root)
    except IntegrityError as exc:
        return [str(exc)]

    for canary in task.canaries:
        token = canary.token.encode("utf-8")
        public_matches = sum(
            canary.token in record.path
            or token in (task.public.root / record.path).read_bytes()
            for record in public_snapshot.files
        )
        if public_matches:
            errors.append(
                f"leakage canary {canary.canary_id!r} appears in public package"
            )
        private_matches = sum(
            canary.token in record.path
            or token in (task.private.root / record.path).read_bytes()
            for record in private_snapshot.files
        )
        if private_matches == 0:
            errors.append(
                f"leakage canary {canary.canary_id!r} is absent from private package"
            )
    return errors


def validate_fixture_task(task: FixtureTask) -> list[str]:
    """Return every public/private boundary or content-integrity error."""

    errors: list[str] = []
    if _roots_overlap(task.public.root, task.private.root):
        errors.append("public and private package roots overlap")

    for package in (task.public, task.private):
        try:
            snapshot_package(package.root)
        except IntegrityError as exc:
            errors.append(f"{package.role} package invalid: {exc}")

    errors.extend(_package_marker_errors(task.public.root))
    errors.extend(_canary_boundary_errors(task))
    return list(dict.fromkeys(errors))


def fixture_identity(task: FixtureTask) -> str:
    """Return a stable identity for split-isolation checks."""

    public = snapshot_package(task.public.root)
    private = snapshot_package(task.private.root)
    return _stable_hash_object(
        {
            "schema": "poc6c-fixture-task-v1",
            "task_id": task.task_id,
            "workload": task.workload,
            "public_sha256": public.sha256,
            "private_sha256": private.sha256,
            "canary_sha256": sorted(
                canary.token_sha256 for canary in task.canaries
            ),
        }
    )


def validate_split_isolation(tasks: Iterable[FixtureTask]) -> list[str]:
    """Reject reused IDs or fixture content across experimental stages.

    All task IDs, full fixture identities, public package hashes, and private
    package hashes must be unique.  This is stricter than cross-split checking:
    accidental duplicates inside one split are also rejected before they can
    distort task-level sample size.
    """

    errors: list[str] = []
    seen: dict[str, dict[str, str]] = {
        "task_id": {},
        "fixture hash": {},
        "public hash": {},
        "private hash": {},
    }
    for task in tasks:
        try:
            public_hash = snapshot_package(task.public.root).sha256
            private_hash = snapshot_package(task.private.root).sha256
            values = {
                "task_id": task.task_id,
                "fixture hash": fixture_identity(task),
                "public hash": public_hash,
                "private hash": private_hash,
            }
        except IntegrityError as exc:
            errors.append(f"{task.split}/{task.task_id}: {exc}")
            continue
        location = f"{task.split}/{task.task_id}"
        for kind, value in values.items():
            previous = seen[kind].get(value)
            if previous is not None:
                errors.append(f"duplicate {kind}: {previous} and {location}")
            else:
                seen[kind][value] = location
    return errors


def _snapshot_difference(
    expected: PackageSnapshot,
    actual: PackageSnapshot,
    label: str,
) -> list[str]:
    expected_by_path = {record.path: record for record in expected.files}
    actual_by_path = {record.path: record for record in actual.files}
    errors: list[str] = []
    missing = sorted(expected_by_path.keys() - actual_by_path.keys())
    extra = sorted(actual_by_path.keys() - expected_by_path.keys())
    changed = sorted(
        path
        for path in expected_by_path.keys() & actual_by_path.keys()
        if expected_by_path[path] != actual_by_path[path]
    )
    if missing:
        errors.append(f"{label} public snapshot missing paths: {missing}")
    if extra:
        errors.append(f"{label} public snapshot has extra paths: {extra}")
    if changed:
        errors.append(f"{label} public snapshot changed paths: {changed}")
    if expected.sha256 != actual.sha256 and not (missing or extra or changed):
        errors.append(f"{label} public snapshot hash mismatch")
    return errors


def validate_matched_public_copies(
    source_root: Path,
    generic_root: Path,
    configured_root: Path,
) -> list[str]:
    """Verify both arms received byte-identical copies of one public package."""

    roots = {
        "source": Path(source_root),
        "generic": Path(generic_root),
        "configured": Path(configured_root),
    }
    errors: list[str] = []
    root_pairs = (
        ("source", "generic"),
        ("source", "configured"),
        ("generic", "configured"),
    )
    for first_label, second_label in root_pairs:
        if _roots_overlap(roots[first_label], roots[second_label]):
            errors.append(
                f"{first_label} and {second_label} public roots overlap"
            )

    try:
        source = snapshot_package(source_root)
    except IntegrityError as exc:
        errors.append(f"source public snapshot invalid: {exc}")
        return errors

    arm_snapshots: dict[str, PackageSnapshot] = {}
    for label, root in (
        ("generic", generic_root),
        ("configured", configured_root),
    ):
        try:
            arm_snapshots[label] = snapshot_package(root)
        except IntegrityError as exc:
            errors.append(f"{label} public snapshot invalid: {exc}")
            continue
        errors.extend(_snapshot_difference(source, arm_snapshots[label], label))

    if (
        "generic" in arm_snapshots
        and "configured" in arm_snapshots
        and arm_snapshots["generic"].sha256
        != arm_snapshots["configured"].sha256
    ):
        errors.append("generic and configured public snapshots do not match")
    return errors
