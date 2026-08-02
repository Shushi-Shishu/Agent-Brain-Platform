"""Provider-independent matched code-testing instrumentation for POC 6c.

Both arms receive fresh byte-identical public task packages and the same
eight-test/tool/runtime constraints.  The only substantive arm difference is
the configured prompt's explicit risk/value decision architecture.

An agent may create only ``test_candidate.py`` plus interpreter-generated
``__pycache__/*.pyc`` files in its assigned workspace.  A
persisted boundary separates manual/sub-agent control from trusted completion.
Only after agent control ends does the harness invoke the sealed private scorer.
Declared-root audits and canaries detect violations but are not an OS sandbox,
so all reports remain diagnostic.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import shutil
import time
from typing import Any, Callable, Mapping

from .code_development import (
    _outside_assigned_snapshot,
    _payload_leakage_ids,
    _provider_record,
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


SCHEMA = "poc6c-code-testing-run-v1"
BOUNDARY_SCHEMA = "poc6c-code-testing-boundary-v1"
ARMS = frozenset({"generic", "configured"})
MAX_TESTS = 8
OUTPUT_NAME = "test_candidate.py"
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "code_testing"
INSTRUCTION_PATHS = {
    "generic": Path(__file__).parent / "GENERIC_CODE_TESTING_AGENT.md",
    "configured": Path(__file__).parent / "CONFIGURED_CODE_TESTING_AGENT.md",
}


class TestingHarnessError(ValueError):
    """Raised when a code-testing run cannot be instrumented safely."""


@dataclass(frozen=True)
class PreparedCodeTestingPair:
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
class TestingArmBoundary:
    pair: PreparedCodeTestingPair
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
        raise TestingHarnessError(f"unknown arm: {arm!r}")


def load_code_testing_fixtures(
    fixture_root: Path = FIXTURE_ROOT,
) -> tuple[FixtureTask, ...]:
    """Load five sealed pilot fixtures without exposing their private contents."""

    root = Path(fixture_root)
    tasks: list[FixtureTask] = []
    for task_root in sorted(root.glob("TST-P*")):
        if not task_root.is_dir():
            continue
        task_id = task_root.name
        canary_path = task_root / "private" / "canary.txt"
        if not canary_path.is_file():
            raise TestingHarnessError(f"{task_id} has no private canary")
        tasks.append(
            FixtureTask(
                task_id=task_id,
                workload="code_testing",
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
        raise TestingHarnessError(
            f"expected five code-testing fixtures, found {len(tasks)}"
        )
    return tuple(tasks)


def prepare_matched_pair(
    task: FixtureTask,
    run_root: Path,
    *,
    matched_conditions: Mapping[str, Any] | None = None,
) -> PreparedCodeTestingPair:
    """Create and lock fresh byte-identical generic/configured workspaces."""

    errors = validate_fixture_task(task)
    if errors:
        raise TestingHarnessError(
            "fixture integrity failed: " + "; ".join(errors)
        )
    run_root = Path(run_root).resolve()
    pair_root = run_root / task.task_id
    for fixture_root in (task.public.root.resolve(), task.private.root.resolve()):
        if (
            pair_root == fixture_root
            or pair_root in fixture_root.parents
            or fixture_root in pair_root.parents
        ):
            raise TestingHarnessError(
                "paired run and fixture package roots cannot overlap"
            )
    if pair_root.exists():
        raise TestingHarnessError(
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
            raise TestingHarnessError(
                "matched-copy validation failed: " + "; ".join(copy_errors)
            )
        source = snapshot_package(task.public.root)
        generic = snapshot_package(generic_root)
        configured = snapshot_package(configured_root)
        if len({source.sha256, generic.sha256, configured.sha256}) != 1:
            raise TestingHarnessError("arms are not byte-identical at start")
        return PreparedCodeTestingPair(
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
    pair: PreparedCodeTestingPair, arm: str
) -> TestingArmBoundary:
    """Verify freshness and record the pre-agent trust boundary."""

    _validate_arm(arm)
    workspace = pair.workspace_for(arm)
    current = snapshot_package(workspace)
    if current.sha256 != pair.arm_start_snapshot.sha256:
        raise TestingHarnessError(f"{arm} workspace is not fresh")
    source = snapshot_package(pair.task.public.root)
    private = snapshot_package(pair.task.private.root)
    if source.sha256 != pair.source_public_snapshot.sha256:
        raise TestingHarnessError("fixture public source changed before agent run")
    if private.sha256 != pair.private_snapshot.sha256:
        raise TestingHarnessError("private scorer changed before agent run")
    return TestingArmBoundary(
        pair=pair,
        arm=arm,
        workspace_pre=current,
        source_public_pre=source,
        private_pre=private,
        other_arm_pre=snapshot_package(pair.other_workspace_for(arm)),
        outside_assigned_pre=_outside_assigned_snapshot(
            pair.pair_root, workspace
        ),
        started_monotonic=time.monotonic(),
    )


def save_arm_boundary(boundary: TestingArmBoundary, path: Path) -> None:
    """Persist a manual/sub-agent boundary outside the assigned workspace."""

    path = Path(path)
    assigned = boundary.workspace.resolve()
    destination = path.resolve()
    if destination == assigned or assigned in destination.parents:
        raise TestingHarnessError(
            "boundary record cannot be stored in agent workspace"
        )
    value = {
        "schema": BOUNDARY_SCHEMA,
        "task_id": boundary.pair.task.task_id,
        "arm": boundary.arm,
        "pair_root": str(boundary.pair.pair_root.resolve()),
        "matched_conditions": dict(boundary.pair.matched_conditions),
        "source_public_snapshot": (
            boundary.pair.source_public_snapshot.as_dict()
        ),
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
    path: Path, *, fixture_root: Path = FIXTURE_ROOT
) -> TestingArmBoundary:
    """Load a boundary created before an external agent was given control."""

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("schema") != BOUNDARY_SCHEMA:
        raise TestingHarnessError("unsupported boundary record")
    tasks = {
        task.task_id: task for task in load_code_testing_fixtures(fixture_root)
    }
    task_id = value.get("task_id")
    if task_id not in tasks:
        raise TestingHarnessError("boundary task is not a sealed fixture")
    arm = value.get("arm")
    _validate_arm(arm)
    pair_root = Path(value["pair_root"]).resolve()
    pair = PreparedCodeTestingPair(
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
    return TestingArmBoundary(
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


def _load_private_scorer(task: FixtureTask):
    scorer_path = task.private.root / "score_tests.py"
    if not scorer_path.is_file():
        raise TestingHarnessError(f"private scorer is missing: {scorer_path}")
    spec = importlib.util.spec_from_file_location(
        f"poc6c_sealed_scorer_{task.task_id.lower()}",
        scorer_path,
    )
    if spec is None or spec.loader is None:
        raise TestingHarnessError("cannot load private scorer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "evaluate", None)):
        raise TestingHarnessError("private scorer lacks evaluate()")
    return module


def _skipped_evaluator(reason: str) -> dict[str, Any]:
    return {
        "executed": False,
        "skip_reason": reason,
        "timed_out": False,
        "returncode": None,
        "duration_ms": 0,
        "metrics": None,
        "leakage_canary_ids": [],
    }


def _run_private_evaluator(
    boundary: TestingArmBoundary,
) -> dict[str, Any]:
    """Invoke the sealed scorer only from trusted completion control."""

    started = time.monotonic()
    try:
        metrics = _load_private_scorer(boundary.pair.task).evaluate(
            boundary.workspace / OUTPUT_NAME,
            boundary.workspace,
        )
    except Exception as exc:
        return {
            "executed": True,
            "timed_out": False,
            "returncode": 1,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "metrics": None,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
            "leakage_canary_ids": list(
                _payload_leakage_ids(
                    {"type": type(exc).__name__, "message": str(exc)},
                    boundary.pair.task.canaries,
                )
            ),
        }
    required = {
        "valid",
        "invalid_reasons",
        "declared_test_count",
        "max_tests",
        "baseline_passes",
        "stable",
        "implementation_coupling_findings",
        "fault_count",
        "distinct_faults_exposed",
        "fault_exposure_rate",
        "runtime_seconds",
        "runtime_within_budget",
    }
    if not isinstance(metrics, dict) or not required <= set(metrics):
        return {
            "executed": True,
            "timed_out": False,
            "returncode": 2,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "metrics": None,
            "error": {"type": "SchemaError", "message": "scorer output mismatch"},
            "leakage_canary_ids": [],
        }
    metrics = dict(metrics)
    metrics["flaky"] = not metrics["stable"]
    metrics["implementation_coupled"] = bool(
        metrics["implementation_coupling_findings"]
    )
    leakage_ids = _payload_leakage_ids(
        metrics, boundary.pair.task.canaries
    )
    return {
        "executed": True,
        "timed_out": False,
        "returncode": 0,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "metrics": _sanitize_value(metrics, boundary.pair.task.canaries),
        "leakage_canary_ids": list(leakage_ids),
    }


def complete_arm_run(
    boundary: TestingArmBoundary,
    *,
    agent_result: Any = None,
    agent_error: Any = None,
    provider_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """End agent control, audit roots, then score the tests it added."""

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
            "private scorer package changed during agent run",
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
    def allowed_change(change: str) -> bool:
        if change == f"created:{OUTPUT_NAME}":
            return True
        if not change.startswith("created:"):
            return False
        relative = change.removeprefix("created:")
        parts = Path(relative).parts
        return "__pycache__" in parts and Path(relative).suffix == ".pyc"

    unexpected_changes = [
        change for change in workspace_changes if not allowed_change(change)
    ]
    if unexpected_changes:
        violations.append(
            "agent changed files other than the candidate test output"
        )
    candidate = boundary.workspace / OUTPUT_NAME
    if not candidate.is_file():
        violations.append(f"missing {OUTPUT_NAME}")

    leakage_ids = set(
        _payload_leakage_ids(
            [agent_result, agent_error], canaries
        )
    )
    leakage_ids.update(_workspace_leakage_ids(boundary.workspace, canaries))

    if private_post_agent.sha256 != boundary.private_pre.sha256:
        evaluator = _skipped_evaluator(
            "private scorer integrity changed during agent run"
        )
    elif not candidate.is_file():
        evaluator = _skipped_evaluator("candidate test output is missing")
    else:
        evaluator = _run_private_evaluator(boundary)
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
            "private scorer package changed during evaluation",
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
    metrics = evaluator.get("metrics")
    valid_metrics = isinstance(metrics, dict) and metrics.get("valid") is True
    return {
        "schema": SCHEMA,
        "diagnostic_only": True,
        "valid_run": (
            not violations
            and agent_error is None
            and evaluator["executed"]
            and evaluator["returncode"] == 0
            and valid_metrics
        ),
        "task_id": pair.task.task_id,
        "workload": "code_testing",
        "split": pair.task.split,
        "arm": boundary.arm,
        "instruction": {
            "sha256": stable_hash_text(
                INSTRUCTION_PATHS[boundary.arm].read_text(encoding="utf-8")
            ),
            "decision_architecture": (
                None
                if boundary.arm == "generic"
                else "risk-value-schedule-budget-allocator-test-critic-marginal-value-stop"
            ),
            "max_candidate_tests": MAX_TESTS,
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
        "candidate_tests": {
            "output_file": OUTPUT_NAME,
            "created": candidate.is_file(),
            "declared_test_count": (
                metrics.get("declared_test_count")
                if isinstance(metrics, dict)
                else None
            ),
            "max_tests": MAX_TESTS,
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
                "assigned files (test_candidate.py creation only)",
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
    pair: PreparedCodeTestingPair,
    arm: str,
    agent_runner: Callable[[Path, str], Any],
    *,
    provider_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a provider adapter, then score only after it relinquishes control."""

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


def summarize_code_testing_reports(
    reports: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return paired task descriptives without an efficacy claim."""

    by_task: dict[str, dict[str, Mapping[str, Any]]] = {}
    for report in reports:
        if report.get("schema") != SCHEMA:
            raise TestingHarnessError("unexpected code-testing report schema")
        arm = report.get("arm")
        _validate_arm(arm)
        task_id = report.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise TestingHarnessError("report lacks task_id")
        if arm in by_task.setdefault(task_id, {}):
            raise TestingHarnessError(
                f"duplicate report for {task_id}/{arm}"
            )
        by_task[task_id][arm] = report
    incomplete = [
        task_id for task_id, arms in by_task.items() if set(arms) != ARMS
    ]
    if incomplete:
        raise TestingHarnessError(
            f"incomplete matched pairs: {sorted(incomplete)}"
        )

    def metrics(report: Mapping[str, Any]) -> Mapping[str, Any] | None:
        if not report.get("valid_run"):
            return None
        return report["evaluator"].get("metrics")

    arm_descriptives: dict[str, Any] = {}
    for arm in sorted(ARMS):
        arm_reports = [arms[arm] for arms in by_task.values()]
        valid = [
            value
            for value in (metrics(report) for report in arm_reports)
            if value is not None
        ]
        arm_descriptives[arm] = {
            "task_count": len(arm_reports),
            "valid_task_count": len(valid),
            "invalid_runs": len(arm_reports) - len(valid),
            "mean_fault_exposure_rate": (
                sum(item["fault_exposure_rate"] for item in valid) / len(valid)
                if valid
                else None
            ),
            "mean_distinct_faults_exposed": (
                sum(item["distinct_faults_exposed"] for item in valid)
                / len(valid)
                if valid
                else None
            ),
            "total_runtime_seconds": (
                sum(item["runtime_seconds"] for item in valid)
                if valid
                else None
            ),
            "coupled_run_count": sum(
                bool(
                    (report["evaluator"].get("metrics") or {}).get(
                        "implementation_coupling_findings"
                    )
                )
                for report in arm_reports
            ),
            "unstable_run_count": sum(
                (report["evaluator"].get("metrics") or {}).get("stable")
                is False
                for report in arm_reports
            ),
            "provider_usage_complete": all(
                report["provider"]["total_tokens"] is not None
                and report["provider"]["cost_amount"] is not None
                for report in arm_reports
            ),
        }

    deltas: list[dict[str, Any]] = []
    for task_id, arms in sorted(by_task.items()):
        generic = metrics(arms["generic"])
        configured = metrics(arms["configured"])
        if generic is None or configured is None:
            continue
        deltas.append(
            {
                "task_id": task_id,
                "configured_minus_generic_fault_exposure_rate": (
                    configured["fault_exposure_rate"]
                    - generic["fault_exposure_rate"]
                ),
                "configured_minus_generic_distinct_faults_exposed": (
                    configured["distinct_faults_exposed"]
                    - generic["distinct_faults_exposed"]
                ),
                "generic_minus_configured_runtime_seconds": (
                    generic["runtime_seconds"]
                    - configured["runtime_seconds"]
                ),
                "generic_minus_configured_declared_tests": (
                    generic["declared_test_count"]
                    - configured["declared_test_count"]
                ),
            }
        )
    delta_keys = (
        "configured_minus_generic_fault_exposure_rate",
        "configured_minus_generic_distinct_faults_exposed",
        "generic_minus_configured_runtime_seconds",
        "generic_minus_configured_declared_tests",
    )
    return {
        "status": "instrumentation_only_no_efficacy_claim",
        "workload": "code_testing",
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
            for key in delta_keys
        },
        "limitations": [
            "Five seen pilot fixtures are not a confirmation sample.",
            "Provider usage and cost remain null when the adapter cannot expose them.",
            "Root guards detect violations but do not replace an OS sandbox.",
            "Runtime includes local scorer subprocess overhead and is descriptive.",
        ],
    }
