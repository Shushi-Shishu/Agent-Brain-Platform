"""Provider-independent code-development instrumentation for POC 6c.

The harness creates byte-identical, isolated copies of a fixture's public
package for the generic and configured arms.  It deliberately does not know
how an LLM is invoked.  A caller can either:

* call :func:`begin_arm_run`, invoke an agent with only ``workspace`` and the
  selected instruction text, then call :func:`complete_arm_run`; or
* pass a provider adapter callback to :func:`run_arm`.

Only the copied arm workspace is agent-visible.  Private evaluator material is
opened by this harness after the agent run has ended.  Guard snapshots detect
changes to the fixture source, private package, other arm, and other paths
inside the paired run directory.  Python cannot police arbitrary writes
outside those roots, so every report states that limitation explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Callable, Mapping

from .fixture_integrity import (
    FileFingerprint,
    FixturePackage,
    FixtureTask,
    IntegrityError,
    LeakageCanary,
    PackageSnapshot,
    detect_canary_leakage,
    snapshot_package,
    stable_hash_bytes,
    stable_hash_text,
    validate_fixture_task,
    validate_matched_public_copies,
)


SCHEMA = "poc6c-code-development-run-v1"
ARMS = frozenset({"generic", "configured"})
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "code_development"
GENERIC_INSTRUCTIONS = Path(__file__).parent / "GENERIC_CODE_DEVELOPMENT_AGENT.md"
CONFIGURED_INSTRUCTIONS = (
    Path(__file__).parent / "CONFIGURED_CODE_DEVELOPMENT_AGENT.md"
)
INSTRUCTION_PATHS = {
    "generic": GENERIC_INSTRUCTIONS,
    "configured": CONFIGURED_INSTRUCTIONS,
}
_RAN_RE = re.compile(r"Ran\s+(\d+)\s+tests?", re.IGNORECASE)
_COUNT_RE = re.compile(r"\b(failures|errors|skipped)=(\d+)\b")


class HarnessError(ValueError):
    """Raised when a code-development run cannot be instrumented safely."""


@dataclass(frozen=True)
class PreparedCodeDevelopmentPair:
    """A fresh matched pair plus its locked pre-run evidence."""

    task: FixtureTask
    pair_root: Path
    generic_root: Path
    configured_root: Path
    source_public_snapshot: PackageSnapshot
    private_snapshot: PackageSnapshot
    arm_start_snapshot: PackageSnapshot
    matched_conditions: Mapping[str, Any]

    def workspace_for(self, arm: str) -> Path:
        _validate_arm(arm)
        return self.generic_root if arm == "generic" else self.configured_root

    def other_workspace_for(self, arm: str) -> Path:
        _validate_arm(arm)
        return self.configured_root if arm == "generic" else self.generic_root


@dataclass(frozen=True)
class ArmRunBoundary:
    """Snapshots captured immediately before one agent receives control."""

    pair: PreparedCodeDevelopmentPair
    arm: str
    workspace_pre: PackageSnapshot
    source_public_pre: PackageSnapshot
    private_pre: PackageSnapshot
    other_arm_pre: PackageSnapshot
    outside_assigned_pre: PackageSnapshot
    started_monotonic: float

    @property
    def workspace(self) -> Path:
        return self.pair.workspace_for(self.arm)


def _validate_arm(arm: str) -> None:
    if arm not in ARMS:
        raise HarnessError(f"unknown arm: {arm!r}")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _snapshot_from_records(records: list[FileFingerprint]) -> PackageSnapshot:
    records_tuple = tuple(sorted(records, key=lambda item: item.path))
    digest = stable_hash_text(
        _canonical_json(
            {
                "schema": "poc6c-package-snapshot-v1",
                "files": [record.canonical_record() for record in records_tuple],
            }
        )
    )
    return PackageSnapshot(files=records_tuple, sha256=digest)


def _snapshot_from_dict(value: Mapping[str, Any]) -> PackageSnapshot:
    files = tuple(
        FileFingerprint(
            path=record["path"],
            size_bytes=record["size_bytes"],
            sha256=record["sha256"],
        )
        for record in value["files"]
    )
    return PackageSnapshot(files=files, sha256=value["sha256"])


def _outside_assigned_snapshot(pair_root: Path, assigned_root: Path) -> PackageSnapshot:
    """Snapshot every paired-run file except the assigned arm workspace."""

    pair_root = Path(pair_root).resolve()
    assigned_root = Path(assigned_root).resolve()
    try:
        assigned_root.relative_to(pair_root)
    except ValueError as exc:
        raise HarnessError("assigned workspace is outside paired run root") from exc
    records: list[FileFingerprint] = []
    for path in sorted(pair_root.rglob("*"), key=lambda item: item.as_posix()):
        resolved = path.resolve()
        if resolved == assigned_root or assigned_root in resolved.parents:
            continue
        relative = path.relative_to(pair_root).as_posix()
        if path.is_symlink():
            raise HarnessError(f"paired run contains a symlink: {relative}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise HarnessError(f"paired run contains a non-regular file: {relative}")
        content = path.read_bytes()
        records.append(
            FileFingerprint(
                path=relative,
                size_bytes=len(content),
                sha256=stable_hash_bytes(content),
            )
        )
    return _snapshot_from_records(records)


def load_code_development_fixtures(
    fixture_root: Path = FIXTURE_ROOT,
) -> tuple[FixtureTask, ...]:
    """Load the five sealed pilot fixtures without exposing private contents."""

    root = Path(fixture_root)
    tasks: list[FixtureTask] = []
    for task_root in sorted(root.glob("DEV-P*")):
        if not task_root.is_dir():
            continue
        task_id = task_root.name
        canary_path = task_root / "private" / "canary.txt"
        if not canary_path.is_file():
            raise HarnessError(f"{task_id} has no private canary")
        token = canary_path.read_text(encoding="utf-8").strip()
        tasks.append(
            FixtureTask(
                task_id=task_id,
                workload="code_development",
                split="pilot",
                public=FixturePackage("public", task_root / "public"),
                private=FixturePackage("private", task_root / "private"),
                canaries=(LeakageCanary(f"canary-{task_id}", token),),
            )
        )
    if len(tasks) != 5:
        raise HarnessError(f"expected five code-development fixtures, found {len(tasks)}")
    return tuple(tasks)


def prepare_matched_pair(
    task: FixtureTask,
    run_root: Path,
    *,
    matched_conditions: Mapping[str, Any] | None = None,
) -> PreparedCodeDevelopmentPair:
    """Create fresh generic/configured copies and lock their starting hashes.

    ``run_root / task_id`` must not already exist.  Refusing reuse prevents an
    earlier patch or evaluator artifact from contaminating a new paired run.
    """

    errors = validate_fixture_task(task)
    if errors:
        raise HarnessError("fixture integrity failed: " + "; ".join(errors))
    run_root = Path(run_root).resolve()
    pair_root = run_root / task.task_id
    fixture_roots = (task.public.root.resolve(), task.private.root.resolve())
    for fixture_root in fixture_roots:
        if pair_root == fixture_root or pair_root in fixture_root.parents:
            raise HarnessError("paired run directory cannot contain a fixture package")
        if fixture_root == pair_root or fixture_root in pair_root.parents:
            raise HarnessError("paired run directory cannot be inside a fixture package")
    if pair_root.exists():
        raise HarnessError(f"fresh paired run directory already exists: {pair_root}")

    generic_root = pair_root / "generic"
    configured_root = pair_root / "configured"
    try:
        pair_root.mkdir(parents=True, exist_ok=False)
        shutil.copytree(task.public.root, generic_root)
        shutil.copytree(task.public.root, configured_root)
    except Exception:
        if pair_root.exists():
            shutil.rmtree(pair_root)
        raise

    copy_errors = validate_matched_public_copies(
        task.public.root,
        generic_root,
        configured_root,
    )
    if copy_errors:
        shutil.rmtree(pair_root)
        raise HarnessError("matched-copy validation failed: " + "; ".join(copy_errors))
    source_snapshot = snapshot_package(task.public.root)
    generic_snapshot = snapshot_package(generic_root)
    configured_snapshot = snapshot_package(configured_root)
    if len({source_snapshot.sha256, generic_snapshot.sha256, configured_snapshot.sha256}) != 1:
        shutil.rmtree(pair_root)
        raise HarnessError("arms are not byte-identical at start")

    return PreparedCodeDevelopmentPair(
        task=task,
        pair_root=pair_root,
        generic_root=generic_root,
        configured_root=configured_root,
        source_public_snapshot=source_snapshot,
        private_snapshot=snapshot_package(task.private.root),
        arm_start_snapshot=generic_snapshot,
        matched_conditions=dict(matched_conditions or {}),
    )


def begin_arm_run(pair: PreparedCodeDevelopmentPair, arm: str) -> ArmRunBoundary:
    """Verify the assigned arm is fresh and capture the pre-agent boundary."""

    _validate_arm(arm)
    workspace = pair.workspace_for(arm)
    current = snapshot_package(workspace)
    if current.sha256 != pair.arm_start_snapshot.sha256:
        raise HarnessError(f"{arm} workspace is not at its locked starting state")
    source = snapshot_package(pair.task.public.root)
    private = snapshot_package(pair.task.private.root)
    if source.sha256 != pair.source_public_snapshot.sha256:
        raise HarnessError("fixture public source changed before agent run")
    if private.sha256 != pair.private_snapshot.sha256:
        raise HarnessError("private evaluator package changed before agent run")
    return ArmRunBoundary(
        pair=pair,
        arm=arm,
        workspace_pre=current,
        source_public_pre=source,
        private_pre=private,
        other_arm_pre=snapshot_package(pair.other_workspace_for(arm)),
        outside_assigned_pre=_outside_assigned_snapshot(pair.pair_root, workspace),
        started_monotonic=time.monotonic(),
    )


def save_arm_boundary(boundary: ArmRunBoundary, path: Path) -> None:
    """Persist a manual-run boundary outside the agent workspace.

    This bridges the human/sub-agent execution path where the harness process
    cannot remain alive while an agent edits the copied workspace.
    """

    path = Path(path)
    assigned = boundary.workspace.resolve()
    destination = path.resolve()
    if destination == assigned or assigned in destination.parents:
        raise HarnessError("boundary record cannot be stored in agent workspace")
    value = {
        "schema": "poc6c-code-development-boundary-v1",
        "task_id": boundary.pair.task.task_id,
        "arm": boundary.arm,
        "pair_root": str(boundary.pair.pair_root.resolve()),
        "matched_conditions": dict(boundary.pair.matched_conditions),
        "source_public_snapshot": boundary.pair.source_public_snapshot.as_dict(),
        "private_snapshot": boundary.pair.private_snapshot.as_dict(),
        "arm_start_snapshot": boundary.pair.arm_start_snapshot.as_dict(),
        "workspace_pre": boundary.workspace_pre.as_dict(),
        "source_public_pre": boundary.source_public_pre.as_dict(),
        "private_pre": boundary.private_pre.as_dict(),
        "other_arm_pre": boundary.other_arm_pre.as_dict(),
        "outside_assigned_pre": boundary.outside_assigned_pre.as_dict(),
        "started_monotonic": boundary.started_monotonic,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_arm_boundary(
    path: Path,
    *,
    fixture_root: Path = FIXTURE_ROOT,
) -> ArmRunBoundary:
    """Load a boundary created by :func:`save_arm_boundary`."""

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("schema") != "poc6c-code-development-boundary-v1":
        raise HarnessError("unsupported boundary record")
    tasks = {
        task.task_id: task
        for task in load_code_development_fixtures(fixture_root)
    }
    task_id = value.get("task_id")
    if task_id not in tasks:
        raise HarnessError("boundary task is not a sealed fixture")
    arm = value.get("arm")
    _validate_arm(arm)
    pair_root = Path(value["pair_root"]).resolve()
    pair = PreparedCodeDevelopmentPair(
        task=tasks[task_id],
        pair_root=pair_root,
        generic_root=pair_root / "generic",
        configured_root=pair_root / "configured",
        source_public_snapshot=_snapshot_from_dict(
            value["source_public_snapshot"]
        ),
        private_snapshot=_snapshot_from_dict(value["private_snapshot"]),
        arm_start_snapshot=_snapshot_from_dict(value["arm_start_snapshot"]),
        matched_conditions=dict(value.get("matched_conditions", {})),
    )
    return ArmRunBoundary(
        pair=pair,
        arm=arm,
        workspace_pre=_snapshot_from_dict(value["workspace_pre"]),
        source_public_pre=_snapshot_from_dict(value["source_public_pre"]),
        private_pre=_snapshot_from_dict(value["private_pre"]),
        other_arm_pre=_snapshot_from_dict(value["other_arm_pre"]),
        outside_assigned_pre=_snapshot_from_dict(
            value["outside_assigned_pre"]
        ),
        started_monotonic=float(value["started_monotonic"]),
    )


def _snapshot_changes(before: PackageSnapshot, after: PackageSnapshot) -> list[str]:
    before_files = {item.path: item for item in before.files}
    after_files = {item.path: item for item in after.files}
    changes: list[str] = []
    changes.extend(f"deleted:{path}" for path in sorted(before_files.keys() - after_files.keys()))
    changes.extend(f"created:{path}" for path in sorted(after_files.keys() - before_files.keys()))
    changes.extend(
        f"modified:{path}"
        for path in sorted(before_files.keys() & after_files.keys())
        if before_files[path] != after_files[path]
    )
    return changes


def _workspace_leakage_ids(
    root: Path,
    canaries: tuple[LeakageCanary, ...],
) -> tuple[str, ...]:
    leaked: set[str] = set()
    snapshot = snapshot_package(root)
    for record in snapshot.files:
        leaked.update(detect_canary_leakage(record.path, canaries))
        leaked.update(detect_canary_leakage((root / record.path).read_bytes(), canaries))
    return tuple(sorted(leaked))


def _redact_text(value: str, canaries: tuple[LeakageCanary, ...]) -> str:
    redacted = value
    for canary in canaries:
        redacted = redacted.replace(
            canary.token,
            f"[REDACTED-CANARY:{canary.canary_id}]",
        )
    return redacted


def _sanitize_value(value: Any, canaries: tuple[LeakageCanary, ...]) -> Any:
    """Return JSON-safe evidence with any canary token redacted."""

    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, bytes):
        return _redact_text(value.decode("utf-8", errors="replace"), canaries)
    if isinstance(value, str):
        return _redact_text(value, canaries)
    if isinstance(value, Mapping):
        return {
            _redact_text(str(key), canaries): _sanitize_value(item, canaries)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(item, canaries) for item in value]
    return _redact_text(repr(value), canaries)


def _payload_leakage_ids(
    value: Any,
    canaries: tuple[LeakageCanary, ...],
) -> tuple[str, ...]:
    """Recursively scan arbitrary adapter output without requiring JSON types."""

    leaked: set[str] = set()
    if isinstance(value, (str, bytes)):
        leaked.update(detect_canary_leakage(value, canaries))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            leaked.update(_payload_leakage_ids(str(key), canaries))
            leaked.update(_payload_leakage_ids(item, canaries))
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            leaked.update(_payload_leakage_ids(item, canaries))
    elif value is not None:
        leaked.update(detect_canary_leakage(repr(value), canaries))
    return tuple(sorted(leaked))


def _safe_output(
    value: str,
    canaries: tuple[LeakageCanary, ...],
    *,
    max_chars: int,
) -> tuple[str, bool]:
    redacted = _redact_text(value, canaries)
    if len(redacted) <= max_chars:
        return redacted, False
    return redacted[:max_chars] + "\n...[truncated]", True


def _parse_unittest_counts(output: str, returncode: int | None) -> dict[str, int | None]:
    ran = _RAN_RE.search(output)
    if ran is None:
        return {
            "total": None,
            "passed": None,
            "failures": None,
            "errors": None,
            "skipped": None,
        }
    total = int(ran.group(1))
    counts = {"failures": 0, "errors": 0, "skipped": 0}
    for name, value in _COUNT_RE.findall(output):
        counts[name.lower()] = int(value)
    # A non-zero exit without a parsed FAILED summary is conservatively an
    # unclassified evaluator error, not a passing test.
    if returncode not in (0, None) and counts["failures"] == counts["errors"] == 0:
        counts["errors"] = max(1, total)
    passed = max(
        0,
        total - counts["failures"] - counts["errors"] - counts["skipped"],
    )
    return {"total": total, "passed": passed, **counts}


def _run_private_evaluator(
    pair: PreparedCodeDevelopmentPair,
    arm: str,
    *,
    timeout_seconds: float,
    max_output_chars: int,
) -> dict[str, Any]:
    """Run the trusted evaluator after the agent, pointed only at its arm copy."""

    evaluator = pair.task.private.root / "evaluator_tests.py"
    if not evaluator.is_file():
        raise HarnessError(f"private evaluator is missing: {evaluator}")
    environment = os.environ.copy()
    environment["POC6C_PUBLIC_ROOT"] = str(pair.workspace_for(arm).resolve())
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, str(evaluator.resolve())],
            cwd=pair.workspace_for(arm),
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
        elapsed_ms = round((time.monotonic() - started) * 1000)
        combined = completed.stdout + "\n" + completed.stderr
        counts = _parse_unittest_counts(combined, completed.returncode)
        stdout, stdout_truncated = _safe_output(
            completed.stdout, pair.task.canaries, max_chars=max_output_chars
        )
        stderr, stderr_truncated = _safe_output(
            completed.stderr, pair.task.canaries, max_chars=max_output_chars
        )
        leakage = detect_canary_leakage(combined, pair.task.canaries)
        return {
            "executed": True,
            "timed_out": False,
            "returncode": completed.returncode,
            "duration_ms": elapsed_ms,
            **counts,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "leakage_canary_ids": list(leakage),
        }
    except subprocess.TimeoutExpired as exc:
        elapsed_ms = round((time.monotonic() - started) * 1000)
        raw_stdout = exc.stdout or ""
        raw_stderr = exc.stderr or ""
        if isinstance(raw_stdout, bytes):
            raw_stdout = raw_stdout.decode("utf-8", errors="replace")
        if isinstance(raw_stderr, bytes):
            raw_stderr = raw_stderr.decode("utf-8", errors="replace")
        stdout, stdout_truncated = _safe_output(
            raw_stdout, pair.task.canaries, max_chars=max_output_chars
        )
        stderr, stderr_truncated = _safe_output(
            raw_stderr, pair.task.canaries, max_chars=max_output_chars
        )
        return {
            "executed": True,
            "timed_out": True,
            "returncode": None,
            "duration_ms": elapsed_ms,
            "total": None,
            "passed": None,
            "failures": None,
            "errors": None,
            "skipped": None,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "leakage_canary_ids": list(
                detect_canary_leakage(
                    raw_stdout + "\n" + raw_stderr,
                    pair.task.canaries,
                )
            ),
        }


def _skipped_evaluator(reason: str) -> dict[str, Any]:
    return {
        "executed": False,
        "skip_reason": reason,
        "timed_out": False,
        "returncode": None,
        "duration_ms": 0,
        "total": None,
        "passed": None,
        "failures": None,
        "errors": None,
        "skipped": None,
        "stdout": "",
        "stderr": "",
        "stdout_truncated": False,
        "stderr_truncated": False,
        "leakage_canary_ids": [],
    }


def _provider_record(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize telemetry without inventing provider observations."""

    record = {
        "provider": None,
        "model_id": None,
        "model_version": None,
        "model_calls": None,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "cost_amount": None,
        "cost_currency": None,
    }
    if metadata:
        for key in record:
            if key in metadata:
                record[key] = metadata[key]
    for key in ("model_calls", "input_tokens", "output_tokens", "total_tokens"):
        value = record[key]
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or value < 0
        ):
            raise HarnessError(f"provider {key} must be null or non-negative integer")
    cost = record["cost_amount"]
    if cost is not None and (
        not isinstance(cost, (int, float))
        or isinstance(cost, bool)
        or cost < 0
    ):
        raise HarnessError("provider cost_amount must be null or non-negative")
    return record


def complete_arm_run(
    boundary: ArmRunBoundary,
    *,
    agent_result: Any = None,
    agent_error: Any = None,
    provider_metadata: Mapping[str, Any] | None = None,
    evaluator_timeout_seconds: float = 10.0,
    max_output_chars: int = 20_000,
) -> dict[str, Any]:
    """Validate the boundary, evaluate the arm, and return diagnostic JSON."""

    if evaluator_timeout_seconds <= 0:
        raise HarnessError("evaluator timeout must be positive")
    if max_output_chars <= 0:
        raise HarnessError("max output size must be positive")
    pair = boundary.pair
    arm = boundary.arm
    canaries = pair.task.canaries

    workspace_post_agent = snapshot_package(boundary.workspace)
    source_post_agent = snapshot_package(pair.task.public.root)
    private_post_agent = snapshot_package(pair.task.private.root)
    other_post_agent = snapshot_package(pair.other_workspace_for(arm))
    outside_post_agent = _outside_assigned_snapshot(pair.pair_root, boundary.workspace)

    violations: list[str] = []
    if source_post_agent.sha256 != boundary.source_public_pre.sha256:
        violations.append("fixture public source changed during agent run")
    if private_post_agent.sha256 != boundary.private_pre.sha256:
        violations.append("private evaluator package changed during agent run")
    if other_post_agent.sha256 != boundary.other_arm_pre.sha256:
        violations.append("other arm workspace changed during agent run")
    if outside_post_agent.sha256 != boundary.outside_assigned_pre.sha256:
        violations.append("path outside assigned workspace changed during agent run")

    agent_payload = {
        "result": agent_result,
        "error": agent_error,
    }
    leakage_ids = set(_payload_leakage_ids(agent_payload, canaries))
    leakage_ids.update(_workspace_leakage_ids(boundary.workspace, canaries))

    if private_post_agent.sha256 != boundary.private_pre.sha256:
        # Never execute evaluator code that may have been altered by the
        # untrusted agent adapter.
        evaluator = _skipped_evaluator(
            "private evaluator integrity changed during agent run"
        )
    else:
        evaluator = _run_private_evaluator(
            pair,
            arm,
            timeout_seconds=evaluator_timeout_seconds,
            max_output_chars=max_output_chars,
        )
    leakage_ids.update(evaluator["leakage_canary_ids"])
    workspace_post_evaluator = snapshot_package(boundary.workspace)
    if workspace_post_evaluator.sha256 != workspace_post_agent.sha256:
        violations.append("trusted evaluator changed the arm workspace")

    source_final = snapshot_package(pair.task.public.root)
    private_final = snapshot_package(pair.task.private.root)
    other_final = snapshot_package(pair.other_workspace_for(arm))
    outside_final = _outside_assigned_snapshot(pair.pair_root, boundary.workspace)
    if source_final.sha256 != source_post_agent.sha256:
        violations.append("fixture public source changed during evaluation")
    if private_final.sha256 != private_post_agent.sha256:
        violations.append("private evaluator package changed during evaluation")
    if other_final.sha256 != other_post_agent.sha256:
        violations.append("other arm workspace changed during evaluation")
    if outside_final.sha256 != outside_post_agent.sha256:
        violations.append("path outside assigned workspace changed during evaluation")

    if leakage_ids:
        violations.append("leakage canary detected")
    violations = list(dict.fromkeys(violations))
    return {
        "schema": SCHEMA,
        "diagnostic_only": True,
        "valid_run": not violations and agent_error is None,
        "task_id": pair.task.task_id,
        "workload": pair.task.workload,
        "split": pair.task.split,
        "arm": arm,
        "instruction": {
            "sha256": stable_hash_text(
                INSTRUCTION_PATHS[arm].read_text(encoding="utf-8")
            ),
            "decision_architecture": (
                None
                if arm == "generic"
                else "hypothesis-voi-minimal-patch-test-critic-stop"
            ),
        },
        "matched_conditions": _sanitize_value(pair.matched_conditions, canaries),
        "provider": _sanitize_value(_provider_record(provider_metadata), canaries),
        "agent": {
            "duration_ms": round(
                (time.monotonic() - boundary.started_monotonic) * 1000
            ),
            "result": _sanitize_value(agent_result, canaries),
            "error": _sanitize_value(agent_error, canaries),
        },
        "integrity": {
            "arms_byte_identical_at_start": True,
            "source_public_sha256_pre": boundary.source_public_pre.sha256,
            "source_public_sha256_post": source_final.sha256,
            "private_sha256_pre": boundary.private_pre.sha256,
            "private_sha256_post": private_final.sha256,
            "workspace_sha256_pre": boundary.workspace_pre.sha256,
            "workspace_sha256_post_agent": workspace_post_agent.sha256,
            "workspace_sha256_post_evaluator": workspace_post_evaluator.sha256,
            "workspace_changes": _sanitize_value(
                _snapshot_changes(
                    boundary.workspace_pre,
                    workspace_post_agent,
                ),
                canaries,
            ),
            "protected_roots_unchanged": not any(
                "changed" in violation for violation in violations
            ),
            "unauthorized_edit_detected": any(
                "changed" in violation for violation in violations
            ),
            "guard_scope": [
                "fixture public package",
                "fixture private package",
                "other arm workspace",
                "all other files inside paired run directory",
            ],
            "guard_limitation": (
                "The harness detects changes only in declared guarded roots; "
                "OS-level sandboxing is required to prevent arbitrary external writes."
            ),
            "leakage_canary_ids": sorted(leakage_ids),
            "violations": violations,
        },
        "evaluator": evaluator,
    }


def run_arm(
    pair: PreparedCodeDevelopmentPair,
    arm: str,
    agent_runner: Callable[[Path, str], Any],
    *,
    provider_metadata: Mapping[str, Any] | None = None,
    evaluator_timeout_seconds: float = 10.0,
    max_output_chars: int = 20_000,
) -> dict[str, Any]:
    """Run a provider adapter with only the assigned workspace and prompt."""

    boundary = begin_arm_run(pair, arm)
    instruction_text = INSTRUCTION_PATHS[arm].read_text(encoding="utf-8")
    result: Any = None
    error: Any = None
    try:
        result = agent_runner(boundary.workspace, instruction_text)
    except Exception as exc:  # adapter errors are evidence, not harness crashes
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
    return complete_arm_run(
        boundary,
        agent_result=result,
        agent_error=error,
        provider_metadata=provider_metadata,
        evaluator_timeout_seconds=evaluator_timeout_seconds,
        max_output_chars=max_output_chars,
    )


def summarize_code_development_reports(
    reports: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return paired pilot descriptives without inferential claims."""

    by_task: dict[str, dict[str, Mapping[str, Any]]] = {}
    for report in reports:
        if report.get("schema") != SCHEMA:
            raise HarnessError("unexpected code-development report schema")
        arm = report.get("arm")
        _validate_arm(arm)
        task_id = report.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise HarnessError("report lacks task_id")
        if arm in by_task.setdefault(task_id, {}):
            raise HarnessError(f"duplicate report for {task_id}/{arm}")
        by_task[task_id][arm] = report
    incomplete = [
        task_id
        for task_id, arms in by_task.items()
        if set(arms) != ARMS
    ]
    if incomplete:
        raise HarnessError(f"incomplete matched pairs: {sorted(incomplete)}")

    def success(report: Mapping[str, Any]) -> bool:
        evaluator = report["evaluator"]
        return bool(
            report["valid_run"]
            and evaluator["executed"]
            and not evaluator["timed_out"]
            and evaluator["returncode"] == 0
            and evaluator["failures"] == 0
            and evaluator["errors"] == 0
        )

    arm_summary: dict[str, Any] = {}
    for arm in sorted(ARMS):
        arm_reports = [arms[arm] for arms in by_task.values()]
        passed = [success(report) for report in arm_reports]
        arm_summary[arm] = {
            "task_count": len(arm_reports),
            "successful_tasks": sum(passed),
            "success_rate": sum(passed) / len(passed),
            "invalid_runs": sum(
                not report["valid_run"] for report in arm_reports
            ),
            "mean_evaluator_tests_passed": sum(
                report["evaluator"]["passed"] for report in arm_reports
            )
            / len(arm_reports),
            "mean_agent_duration_ms": sum(
                report["agent"]["duration_ms"] for report in arm_reports
            )
            / len(arm_reports),
            "provider_usage_complete": all(
                report["provider"]["total_tokens"] is not None
                and report["provider"]["cost_amount"] is not None
                for report in arm_reports
            ),
        }

    paired = {
        "both_succeeded": 0,
        "generic_only_succeeded": 0,
        "configured_only_succeeded": 0,
        "neither_succeeded": 0,
    }
    for arms in by_task.values():
        generic_success = success(arms["generic"])
        configured_success = success(arms["configured"])
        if generic_success and configured_success:
            paired["both_succeeded"] += 1
        elif generic_success:
            paired["generic_only_succeeded"] += 1
        elif configured_success:
            paired["configured_only_succeeded"] += 1
        else:
            paired["neither_succeeded"] += 1

    return {
        "status": "instrumentation_only_no_efficacy_claim",
        "workload": "code_development",
        "task_count": len(by_task),
        "arm_descriptives": arm_summary,
        "paired_outcomes": paired,
        "limitations": [
            "Five seen pilot tasks are not a confirmation sample.",
            "Provider token and cost telemetry may be unavailable.",
            "Agent duration includes orchestration and queue delay in manual "
            "sub-agent runs and is not provider latency.",
            "Host-level isolation is instructed and audited at guarded roots, "
            "not enforced by an OS sandbox.",
        ],
    }
