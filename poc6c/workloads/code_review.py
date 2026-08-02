"""Provider-independent matched code-review instrumentation for POC 6c.

The generic and configured arms receive fresh, byte-identical copies of only a
fixture's public package.  They must write a bounded ``REVIEW_FINDINGS.json``.
Private inventories, canaries, and evaluators are opened only by
``complete_arm_run`` after agent control has ended.

The harness audits declared roots but is not an OS sandbox.  Reports therefore
remain diagnostic when host-level isolation and provider telemetry are absent.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping

from .code_development import (
    _outside_assigned_snapshot,
    _payload_leakage_ids,
    _provider_record,
    _safe_output,
    _sanitize_value,
    _snapshot_changes,
    _snapshot_from_dict,
    _workspace_leakage_ids,
)
from .fixture_integrity import (
    FixturePackage,
    FixtureTask,
    LeakageCanary,
    PackageSnapshot,
    snapshot_package,
    stable_hash_text,
    validate_fixture_task,
    validate_matched_public_copies,
)


SCHEMA = "poc6c-code-review-run-v1"
BOUNDARY_SCHEMA = "poc6c-code-review-boundary-v1"
ARMS = frozenset({"generic", "configured"})
MAX_FINDINGS = 6
OUTPUT_NAME = "REVIEW_FINDINGS.json"
FINDING_KEYS = frozenset(
    {"file", "line", "category", "severity", "explanation"}
)
SEVERITIES = frozenset({"low", "medium", "high", "critical"})
_CATEGORY_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "code_review"
INSTRUCTION_PATHS = {
    "generic": Path(__file__).parent / "GENERIC_CODE_REVIEW_AGENT.md",
    "configured": Path(__file__).parent / "CONFIGURED_CODE_REVIEW_AGENT.md",
}


class ReviewHarnessError(ValueError):
    """Raised when a review run cannot be instrumented safely."""


@dataclass(frozen=True)
class PreparedCodeReviewPair:
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
class ReviewArmBoundary:
    pair: PreparedCodeReviewPair
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
        raise ReviewHarnessError(f"unknown arm: {arm!r}")


def load_code_review_fixtures(
    fixture_root: Path = FIXTURE_ROOT,
) -> tuple[FixtureTask, ...]:
    root = Path(fixture_root)
    tasks: list[FixtureTask] = []
    for task_root in sorted(root.glob("CRV-P*")):
        if not task_root.is_dir():
            continue
        task_id = task_root.name
        canary_path = task_root / "private" / "canary.txt"
        if not canary_path.is_file():
            raise ReviewHarnessError(f"{task_id} has no private canary")
        tasks.append(
            FixtureTask(
                task_id=task_id,
                workload="code_review",
                split="pilot",
                public=FixturePackage("public", task_root / "public"),
                private=FixturePackage("private", task_root / "private"),
                canaries=(
                    LeakageCanary(
                        f"canary-{task_id}",
                        canary_path.read_text(encoding="utf-8").strip(),
                    ),
                ),
            )
        )
    if len(tasks) != 5:
        raise ReviewHarnessError(
            f"expected five code-review fixtures, found {len(tasks)}"
        )
    return tuple(tasks)


def prepare_matched_pair(
    task: FixtureTask,
    run_root: Path,
    *,
    matched_conditions: Mapping[str, Any] | None = None,
) -> PreparedCodeReviewPair:
    errors = validate_fixture_task(task)
    if errors:
        raise ReviewHarnessError("fixture integrity failed: " + "; ".join(errors))
    run_root = Path(run_root).resolve()
    pair_root = run_root / task.task_id
    for fixture_root in (task.public.root.resolve(), task.private.root.resolve()):
        if (
            pair_root == fixture_root
            or pair_root in fixture_root.parents
            or fixture_root in pair_root.parents
        ):
            raise ReviewHarnessError(
                "paired run and fixture package roots cannot overlap"
            )
    if pair_root.exists():
        raise ReviewHarnessError(
            f"fresh paired run directory already exists: {pair_root}"
        )
    generic_root = pair_root / "generic"
    configured_root = pair_root / "configured"
    try:
        pair_root.mkdir(parents=True, exist_ok=False)
        shutil.copytree(task.public.root, generic_root)
        shutil.copytree(task.public.root, configured_root)
        copy_errors = validate_matched_public_copies(
            task.public.root, generic_root, configured_root
        )
        if copy_errors:
            raise ReviewHarnessError(
                "matched-copy validation failed: " + "; ".join(copy_errors)
            )
        source = snapshot_package(task.public.root)
        generic = snapshot_package(generic_root)
        configured = snapshot_package(configured_root)
        if len({source.sha256, generic.sha256, configured.sha256}) != 1:
            raise ReviewHarnessError("arms are not byte-identical at start")
        return PreparedCodeReviewPair(
            task=task,
            pair_root=pair_root,
            generic_root=generic_root,
            configured_root=configured_root,
            source_public_snapshot=source,
            private_snapshot=snapshot_package(task.private.root),
            arm_start_snapshot=generic,
            matched_conditions=dict(matched_conditions or {}),
        )
    except Exception:
        if pair_root.exists():
            shutil.rmtree(pair_root)
        raise


def begin_arm_run(
    pair: PreparedCodeReviewPair, arm: str
) -> ReviewArmBoundary:
    _validate_arm(arm)
    workspace = pair.workspace_for(arm)
    current = snapshot_package(workspace)
    if current.sha256 != pair.arm_start_snapshot.sha256:
        raise ReviewHarnessError(f"{arm} workspace is not fresh")
    source = snapshot_package(pair.task.public.root)
    private = snapshot_package(pair.task.private.root)
    if source.sha256 != pair.source_public_snapshot.sha256:
        raise ReviewHarnessError("fixture public source changed before agent run")
    if private.sha256 != pair.private_snapshot.sha256:
        raise ReviewHarnessError("private evaluator changed before agent run")
    return ReviewArmBoundary(
        pair=pair,
        arm=arm,
        workspace_pre=current,
        source_public_pre=source,
        private_pre=private,
        other_arm_pre=snapshot_package(pair.other_workspace_for(arm)),
        outside_assigned_pre=_outside_assigned_snapshot(pair.pair_root, workspace),
        started_monotonic=time.monotonic(),
    )


def save_arm_boundary(boundary: ReviewArmBoundary, path: Path) -> None:
    path = Path(path)
    assigned = boundary.workspace.resolve()
    destination = path.resolve()
    if destination == assigned or assigned in destination.parents:
        raise ReviewHarnessError(
            "boundary record cannot be stored in agent workspace"
        )
    value = {
        "schema": BOUNDARY_SCHEMA,
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
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def load_arm_boundary(
    path: Path, *, fixture_root: Path = FIXTURE_ROOT
) -> ReviewArmBoundary:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("schema") != BOUNDARY_SCHEMA:
        raise ReviewHarnessError("unsupported boundary record")
    tasks = {
        task.task_id: task for task in load_code_review_fixtures(fixture_root)
    }
    task_id = value.get("task_id")
    if task_id not in tasks:
        raise ReviewHarnessError("boundary task is not a sealed fixture")
    arm = value.get("arm")
    _validate_arm(arm)
    pair_root = Path(value["pair_root"]).resolve()
    pair = PreparedCodeReviewPair(
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
    return ReviewArmBoundary(
        pair=pair,
        arm=arm,
        workspace_pre=_snapshot_from_dict(value["workspace_pre"]),
        source_public_pre=_snapshot_from_dict(value["source_public_pre"]),
        private_pre=_snapshot_from_dict(value["private_pre"]),
        other_arm_pre=_snapshot_from_dict(value["other_arm_pre"]),
        outside_assigned_pre=_snapshot_from_dict(value["outside_assigned_pre"]),
        started_monotonic=float(value["started_monotonic"]),
    )


def validate_findings(
    value: Any, workspace: Path
) -> tuple[list[dict[str, Any]] | None, list[str]]:
    """Strictly validate the shared, bounded findings contract."""

    if not isinstance(value, list):
        return None, ["top-level JSON must be an array"]
    errors: list[str] = []
    if len(value) > MAX_FINDINGS:
        errors.append(f"finding count exceeds shared budget of {MAX_FINDINGS}")
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    workspace = Path(workspace).resolve()
    for index, finding in enumerate(value):
        prefix = f"finding[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{prefix} must be an object")
            continue
        keys = set(finding)
        if keys != FINDING_KEYS:
            errors.append(
                f"{prefix} must contain exactly {sorted(FINDING_KEYS)}"
            )
            continue
        file_value = finding["file"]
        source: Path | None = None
        if not isinstance(file_value, str) or not file_value:
            errors.append(f"{prefix}.file must be a non-empty string")
        else:
            candidate = Path(file_value)
            if candidate.is_absolute() or ".." in candidate.parts:
                errors.append(f"{prefix}.file must be a safe relative path")
            else:
                source = (workspace / candidate).resolve()
                try:
                    source.relative_to(workspace)
                except ValueError:
                    errors.append(f"{prefix}.file escapes the workspace")
                    source = None
                if source is not None and (
                    not source.is_file() or source.suffix != ".py"
                ):
                    errors.append(f"{prefix}.file must name an existing Python file")
                    source = None
        line = finding["line"]
        if isinstance(line, bool) or not isinstance(line, int) or line < 1:
            errors.append(f"{prefix}.line must be a positive integer")
        elif source is not None:
            line_count = len(
                source.read_text(encoding="utf-8").splitlines()
            )
            if line > line_count:
                errors.append(f"{prefix}.line exceeds the source length")
        category = finding["category"]
        if not isinstance(category, str) or not _CATEGORY_RE.fullmatch(category):
            errors.append(f"{prefix}.category must be lowercase_snake_case")
        severity = finding["severity"]
        if severity not in SEVERITIES:
            errors.append(f"{prefix}.severity is invalid")
        explanation = finding["explanation"]
        if (
            not isinstance(explanation, str)
            or explanation != explanation.strip()
            or not 20 <= len(explanation) <= 600
        ):
            errors.append(
                f"{prefix}.explanation must be 20-600 trimmed characters"
            )
        # Schema validation rejects exact duplicates. Distinct actionable
        # defects may legitimately share a line and category; the private
        # scorer, not the JSON contract, decides whether those are redundant.
        identity = (
            file_value,
            line,
            category,
            severity,
            explanation,
        )
        if identity in seen:
            errors.append(f"{prefix} duplicates an earlier finding")
        seen.add(identity)
        normalized.append(dict(finding))
    return (normalized if not errors else None), errors


def _load_findings(
    workspace: Path,
) -> tuple[list[dict[str, Any]] | None, list[str], str]:
    path = Path(workspace) / OUTPUT_NAME
    if not path.is_file():
        return None, [f"missing {OUTPUT_NAME}"], ""
    raw = path.read_text(encoding="utf-8")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON: {exc.msg}"], raw
    findings, errors = validate_findings(value, workspace)
    return findings, errors, raw


def _run_private_evaluator(
    boundary: ReviewArmBoundary,
    findings: list[dict[str, Any]],
    *,
    timeout_seconds: float,
    max_output_chars: int,
) -> dict[str, Any]:
    evaluator = boundary.pair.task.private.root / "evaluate_review.py"
    if not evaluator.is_file():
        raise ReviewHarnessError(f"private evaluator is missing: {evaluator}")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="poc6c-review-eval-") as temp:
        input_path = Path(temp) / "findings.json"
        input_path.write_text(json.dumps(findings), encoding="utf-8")
        try:
            completed = subprocess.run(
                [sys.executable, str(evaluator.resolve()), str(input_path)],
                cwd=boundary.pair.task.private.root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
                env={"PYTHONDONTWRITEBYTECODE": "1"},
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            safe_stdout, stdout_truncated = _safe_output(
                stdout,
                boundary.pair.task.canaries,
                max_chars=max_output_chars,
            )
            safe_stderr, stderr_truncated = _safe_output(
                stderr,
                boundary.pair.task.canaries,
                max_chars=max_output_chars,
            )
            return {
                "executed": True,
                "timed_out": True,
                "returncode": None,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "metrics": None,
                "stdout": safe_stdout,
                "stderr": safe_stderr,
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
                "leakage_canary_ids": list(
                    set(
                        _payload_leakage_ids(
                            [stdout, stderr], boundary.pair.task.canaries
                        )
                    )
                ),
            }
    safe_stdout, stdout_truncated = _safe_output(
        completed.stdout,
        boundary.pair.task.canaries,
        max_chars=max_output_chars,
    )
    safe_stderr, stderr_truncated = _safe_output(
        completed.stderr,
        boundary.pair.task.canaries,
        max_chars=max_output_chars,
    )
    metrics = None
    if completed.returncode == 0:
        try:
            candidate = json.loads(completed.stdout)
            required = {
                "task_id",
                "true_positive_count",
                "missed_count",
                "false_positive_count",
                "matched_defect_ids",
                "false_positive_indexes",
                "severity_weighted_recall",
            }
            if not isinstance(candidate, dict) or not required <= set(candidate):
                raise ValueError("evaluator output schema mismatch")
            tp = candidate["true_positive_count"]
            fp = candidate["false_positive_count"]
            candidate["precision"] = tp / (tp + fp) if tp + fp else 1.0
            metrics = candidate
        except (json.JSONDecodeError, TypeError, ValueError, ZeroDivisionError):
            metrics = None
    return {
        "executed": True,
        "timed_out": False,
        "returncode": completed.returncode,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "metrics": metrics,
        "stdout": safe_stdout,
        "stderr": safe_stderr,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "leakage_canary_ids": list(
            _payload_leakage_ids(
                [completed.stdout, completed.stderr],
                boundary.pair.task.canaries,
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
        "metrics": None,
        "stdout": "",
        "stderr": "",
        "stdout_truncated": False,
        "stderr_truncated": False,
        "leakage_canary_ids": [],
    }


def complete_arm_run(
    boundary: ReviewArmBoundary,
    *,
    agent_result: Any = None,
    agent_error: Any = None,
    provider_metadata: Mapping[str, Any] | None = None,
    evaluator_timeout_seconds: float = 10.0,
    max_output_chars: int = 20_000,
) -> dict[str, Any]:
    """End agent control, validate its JSON, then invoke the sealed scorer."""

    if evaluator_timeout_seconds <= 0 or max_output_chars <= 0:
        raise ReviewHarnessError("evaluator limits must be positive")
    pair = boundary.pair
    canaries = pair.task.canaries
    workspace_post_agent = snapshot_package(boundary.workspace)
    source_post_agent = snapshot_package(pair.task.public.root)
    private_post_agent = snapshot_package(pair.task.private.root)
    other_post_agent = snapshot_package(pair.other_workspace_for(boundary.arm))
    outside_post_agent = _outside_assigned_snapshot(
        pair.pair_root, boundary.workspace
    )
    violations: list[str] = []
    guarded = (
        (
            source_post_agent.sha256 != boundary.source_public_pre.sha256,
            "fixture public source changed during agent run",
        ),
        (
            private_post_agent.sha256 != boundary.private_pre.sha256,
            "private evaluator package changed during agent run",
        ),
        (
            other_post_agent.sha256 != boundary.other_arm_pre.sha256,
            "other arm workspace changed during agent run",
        ),
        (
            outside_post_agent.sha256 != boundary.outside_assigned_pre.sha256,
            "path outside assigned workspace changed during agent run",
        ),
    )
    violations.extend(message for changed, message in guarded if changed)
    workspace_changes = _snapshot_changes(
        boundary.workspace_pre, workspace_post_agent
    )
    unexpected_changes = [
        change
        for change in workspace_changes
        if change != f"created:{OUTPUT_NAME}"
    ]
    if unexpected_changes:
        violations.append("agent modified files outside the review output")

    findings, schema_errors, raw_findings = _load_findings(boundary.workspace)
    if schema_errors:
        violations.append("review findings schema invalid")
    leakage_ids = set(
        _payload_leakage_ids(
            [agent_result, agent_error, raw_findings], canaries
        )
    )
    leakage_ids.update(_workspace_leakage_ids(boundary.workspace, canaries))
    if private_post_agent.sha256 != boundary.private_pre.sha256:
        evaluator = _skipped_evaluator(
            "private evaluator integrity changed during agent run"
        )
    elif findings is None:
        evaluator = _skipped_evaluator("review findings failed schema validation")
    else:
        evaluator = _run_private_evaluator(
            boundary,
            findings,
            timeout_seconds=evaluator_timeout_seconds,
            max_output_chars=max_output_chars,
        )
    leakage_ids.update(evaluator["leakage_canary_ids"])

    workspace_post_evaluator = snapshot_package(boundary.workspace)
    source_final = snapshot_package(pair.task.public.root)
    private_final = snapshot_package(pair.task.private.root)
    other_final = snapshot_package(pair.other_workspace_for(boundary.arm))
    outside_final = _outside_assigned_snapshot(
        pair.pair_root, boundary.workspace
    )
    final_checks = (
        (
            workspace_post_evaluator.sha256 != workspace_post_agent.sha256,
            "trusted evaluator changed the arm workspace",
        ),
        (
            source_final.sha256 != source_post_agent.sha256,
            "fixture public source changed during evaluation",
        ),
        (
            private_final.sha256 != private_post_agent.sha256,
            "private evaluator package changed during evaluation",
        ),
        (
            other_final.sha256 != other_post_agent.sha256,
            "other arm workspace changed during evaluation",
        ),
        (
            outside_final.sha256 != outside_post_agent.sha256,
            "path outside assigned workspace changed during evaluation",
        ),
    )
    violations.extend(message for changed, message in final_checks if changed)
    if leakage_ids:
        violations.append("leakage canary detected")
    violations = list(dict.fromkeys(violations))
    return {
        "schema": SCHEMA,
        "diagnostic_only": True,
        "valid_run": (
            not violations
            and agent_error is None
            and evaluator["executed"]
            and not evaluator["timed_out"]
            and evaluator["returncode"] == 0
            and evaluator["metrics"] is not None
        ),
        "task_id": pair.task.task_id,
        "workload": "code_review",
        "split": pair.task.split,
        "arm": boundary.arm,
        "instruction": {
            "sha256": stable_hash_text(
                INSTRUCTION_PATHS[boundary.arm].read_text(encoding="utf-8")
            ),
            "decision_architecture": (
                None
                if boundary.arm == "generic"
                else "risk-schedule-evidence-ledger-critic-voi-stop"
            ),
            "max_findings": MAX_FINDINGS,
        },
        "matched_conditions": _sanitize_value(
            pair.matched_conditions, canaries
        ),
        "provider": _sanitize_value(
            _provider_record(provider_metadata), canaries
        ),
        "agent": {
            "duration_ms": round(
                (time.monotonic() - boundary.started_monotonic) * 1000
            ),
            "result": _sanitize_value(agent_result, canaries),
            "error": _sanitize_value(agent_error, canaries),
        },
        "findings": {
            "output_file": OUTPUT_NAME,
            "count": len(findings) if findings is not None else None,
            "schema_valid": findings is not None,
            "schema_errors": schema_errors,
            "max_findings": MAX_FINDINGS,
        },
        "integrity": {
            "arms_byte_identical_at_start": True,
            "source_public_sha256_pre": boundary.source_public_pre.sha256,
            "source_public_sha256_post": source_final.sha256,
            "private_sha256_pre": boundary.private_pre.sha256,
            "private_sha256_post": private_final.sha256,
            "workspace_sha256_pre": boundary.workspace_pre.sha256,
            "workspace_sha256_post_agent": workspace_post_agent.sha256,
            "workspace_sha256_post_evaluator": (
                workspace_post_evaluator.sha256
            ),
            "workspace_changes": _sanitize_value(workspace_changes, canaries),
            "protected_roots_unchanged": not any(
                "changed" in item for item in violations
            ),
            "unauthorized_edit_detected": bool(unexpected_changes)
            or any("changed" in item for item in violations),
            "guard_scope": [
                "fixture public package",
                "fixture private package",
                "other arm workspace",
                "all other files inside paired run directory",
                "assigned source files (output file creation only)",
            ],
            "guard_limitation": (
                "Declared roots are audited; OS-level sandboxing is required "
                "to prevent arbitrary external writes."
            ),
            "leakage_canary_ids": sorted(leakage_ids),
            "violations": violations,
        },
        "evaluator": evaluator,
    }


def run_arm(
    pair: PreparedCodeReviewPair,
    arm: str,
    agent_runner: Callable[[Path, str], Any],
    *,
    provider_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    boundary = begin_arm_run(pair, arm)
    result: Any = None
    error: Any = None
    try:
        result = agent_runner(
            boundary.workspace,
            INSTRUCTION_PATHS[arm].read_text(encoding="utf-8"),
        )
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
    return complete_arm_run(
        boundary,
        agent_result=result,
        agent_error=error,
        provider_metadata=provider_metadata,
    )


def summarize_code_review_reports(
    reports: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Summarize matched task-level descriptives without an efficacy claim."""

    by_task: dict[str, dict[str, Mapping[str, Any]]] = {}
    for report in reports:
        if report.get("schema") != SCHEMA:
            raise ReviewHarnessError("unexpected code-review report schema")
        arm = report.get("arm")
        _validate_arm(arm)
        task_id = report.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise ReviewHarnessError("report lacks task_id")
        if arm in by_task.setdefault(task_id, {}):
            raise ReviewHarnessError(f"duplicate report for {task_id}/{arm}")
        by_task[task_id][arm] = report
    incomplete = [
        task_id for task_id, arms in by_task.items() if set(arms) != ARMS
    ]
    if incomplete:
        raise ReviewHarnessError(f"incomplete matched pairs: {incomplete}")

    def metrics(report: Mapping[str, Any]) -> Mapping[str, Any] | None:
        if not report.get("valid_run"):
            return None
        return report["evaluator"].get("metrics")

    arm_descriptives: dict[str, Any] = {}
    for arm in sorted(ARMS):
        arm_reports = [arms[arm] for arms in by_task.values()]
        valid_metrics = [
            value
            for value in (metrics(report) for report in arm_reports)
            if value is not None
        ]
        tp = sum(value["true_positive_count"] for value in valid_metrics)
        fp = sum(value["false_positive_count"] for value in valid_metrics)
        arm_descriptives[arm] = {
            "task_count": len(arm_reports),
            "valid_task_count": len(valid_metrics),
            "invalid_runs": len(arm_reports) - len(valid_metrics),
            "mean_severity_weighted_recall": (
                sum(
                    value["severity_weighted_recall"]
                    for value in valid_metrics
                )
                / len(valid_metrics)
                if valid_metrics
                else None
            ),
            "micro_precision": (
                tp / (tp + fp) if valid_metrics and tp + fp else (
                    1.0 if valid_metrics else None
                )
            ),
            "total_false_positives": (
                fp if valid_metrics else None
            ),
            "provider_usage_complete": all(
                report["provider"]["total_tokens"] is not None
                and report["provider"]["cost_amount"] is not None
                for report in arm_reports
            ),
        }

    deltas = []
    for task_id, arms in sorted(by_task.items()):
        generic = metrics(arms["generic"])
        configured = metrics(arms["configured"])
        if generic is None or configured is None:
            continue
        deltas.append(
            {
                "task_id": task_id,
                "configured_minus_generic_severity_weighted_recall": (
                    configured["severity_weighted_recall"]
                    - generic["severity_weighted_recall"]
                ),
                "configured_minus_generic_precision": (
                    configured["precision"] - generic["precision"]
                ),
                "generic_minus_configured_false_positives": (
                    generic["false_positive_count"]
                    - configured["false_positive_count"]
                ),
            }
        )
    return {
        "status": "instrumentation_only_no_efficacy_claim",
        "workload": "code_review",
        "task_count": len(by_task),
        "valid_pair_count": len(deltas),
        "arm_descriptives": arm_descriptives,
        "paired_task_deltas": deltas,
        "mean_paired_deltas": {
            key: (
                sum(item[key] for item in deltas) / len(deltas)
                if deltas
                else None
            )
            for key in (
                "configured_minus_generic_severity_weighted_recall",
                "configured_minus_generic_precision",
                "generic_minus_configured_false_positives",
            )
        },
        "limitations": [
            "Five seen pilot fixtures are not a confirmation sample.",
            "Provider usage and cost remain null when the adapter cannot expose them.",
            "Root guards detect violations but do not replace an OS sandbox.",
        ],
    }
