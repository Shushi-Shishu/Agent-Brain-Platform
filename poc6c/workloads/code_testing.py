"""Provider-independent scoring for POC 6c code-testing fixtures."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Mapping, Sequence


_RAN_RE = re.compile(r"Ran (\d+) tests?")
_TIME_RE = re.compile(r"in \d+(?:\.\d+)?s")


@dataclass(frozen=True)
class TestRun:
    returncode: int
    test_count: int | None
    timed_out: bool
    elapsed_seconds: float
    signature: str


def _test_count(tree: ast.AST) -> int:
    return sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.walk(tree)
    )


def implementation_coupling_findings(source: str) -> tuple[str, ...]:
    """Identify test techniques that inspect implementation rather than behavior."""

    tree = ast.parse(source)
    findings: set[str] = set()
    banned_imports = {"ast", "dis", "importlib", "inspect"}
    banned_calls = {"compile", "eval", "exec", "open"}
    banned_attributes = {
        "__code__",
        "__file__",
        "__source__",
        "read_bytes",
        "read_text",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".", 1)[0] in banned_imports:
                    findings.add(f"import:{alias.name.split('.', 1)[0]}")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".", 1)[0] in banned_imports:
                findings.add(f"import:{(node.module or '').split('.', 1)[0]}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in banned_calls:
                findings.add(f"call:{node.func.id}")
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in banned_attributes
            ):
                findings.add(f"attribute:{node.func.attr}")
        elif isinstance(node, ast.Attribute) and node.attr in banned_attributes:
            findings.add(f"attribute:{node.attr}")
    return tuple(sorted(findings))


def _normalized_signature(completed: subprocess.CompletedProcess[str]) -> str:
    text = completed.stdout + "\n" + completed.stderr
    return _TIME_RE.sub("in <time>s", text).strip()


def _run_suite(
    public_root: Path,
    module_filename: str,
    candidate_source: str,
    replacement_source: str | None,
    timeout_seconds: float,
) -> TestRun:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="poc6c-code-testing-") as temp_name:
        work = Path(temp_name)
        for item in public_root.iterdir():
            if item.is_file():
                shutil.copy2(item, work / item.name)
        (work / "test_candidate.py").write_text(candidate_source, encoding="utf-8")
        if replacement_source is not None:
            (work / module_filename).write_text(replacement_source, encoding="utf-8")
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "unittest", "-v", "test_candidate"],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return TestRun(
                returncode=124,
                test_count=None,
                timed_out=True,
                elapsed_seconds=time.perf_counter() - started,
                signature="TIMEOUT",
            )
    output = completed.stdout + completed.stderr
    match = _RAN_RE.search(output)
    return TestRun(
        returncode=completed.returncode,
        test_count=int(match.group(1)) if match else None,
        timed_out=False,
        elapsed_seconds=time.perf_counter() - started,
        signature=_normalized_signature(completed),
    )


def score_candidate(
    *,
    task_id: str,
    public_root: Path,
    module_filename: str,
    candidate_test: Path,
    faults: Sequence[Mapping[str, str]],
    max_tests: int = 8,
    timeout_seconds: float = 3.0,
) -> dict:
    """Score one unittest submission against a sealed deterministic fault set."""

    candidate_source = Path(candidate_test).read_text(encoding="utf-8")
    invalid_reasons: list[str] = []
    try:
        tree = ast.parse(candidate_source)
        declared_count = _test_count(tree)
        coupling = implementation_coupling_findings(candidate_source)
    except SyntaxError as exc:
        tree = None
        declared_count = 0
        coupling = ()
        invalid_reasons.append(f"syntax_error:{exc.lineno}")

    if declared_count == 0:
        invalid_reasons.append("no_tests_declared")
    if declared_count > max_tests:
        invalid_reasons.append("test_count_budget_exceeded")
    if coupling:
        invalid_reasons.append("implementation_coupled")

    baseline_runs = [
        _run_suite(
            Path(public_root),
            module_filename,
            candidate_source,
            None,
            timeout_seconds,
        )
        for _ in range(2)
    ]
    if any(run.timed_out for run in baseline_runs):
        invalid_reasons.append("baseline_timeout")
    if any(run.returncode != 0 for run in baseline_runs):
        invalid_reasons.append("baseline_failure")
    stable = (
        baseline_runs[0].returncode == baseline_runs[1].returncode
        and baseline_runs[0].test_count == baseline_runs[1].test_count
        and baseline_runs[0].signature == baseline_runs[1].signature
    )
    if not stable:
        invalid_reasons.append("unstable_baseline")

    exposed: list[str] = []
    fault_runs: list[TestRun] = []
    if not invalid_reasons:
        for fault in faults:
            run = _run_suite(
                Path(public_root),
                module_filename,
                candidate_source,
                fault["source"],
                timeout_seconds,
            )
            fault_runs.append(run)
            if run.timed_out or run.returncode != 0:
                exposed.append(fault["fault_id"])

    total_runtime = sum(
        run.elapsed_seconds for run in baseline_runs + fault_runs
    )
    return {
        "schema_version": 1,
        "task_id": task_id,
        "valid": not invalid_reasons,
        "invalid_reasons": sorted(set(invalid_reasons)),
        "declared_test_count": declared_count,
        "max_tests": max_tests,
        "timeout_seconds_per_run": timeout_seconds,
        "baseline_passes": all(run.returncode == 0 for run in baseline_runs),
        "stable": stable,
        "implementation_coupling_findings": list(coupling),
        "faults_exposed": exposed,
        "fault_count": len(faults),
        "distinct_faults_exposed": len(exposed),
        "fault_exposure_rate": (
            round(len(exposed) / len(faults), 6) if faults else 0.0
        ),
        "runtime_seconds": round(total_runtime, 6),
        "runtime_within_budget": not any(
            run.timed_out for run in baseline_runs + fault_runs
        ),
    }
