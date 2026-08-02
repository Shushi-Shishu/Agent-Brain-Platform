"""CLI for manual or sub-agent POC 6c code-review pilot runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from workloads.code_review import (
    PreparedCodeReviewPair,
    begin_arm_run,
    complete_arm_run,
    load_arm_boundary,
    load_code_review_fixtures,
    prepare_matched_pair,
    save_arm_boundary,
    summarize_code_review_reports,
)
from workloads.fixture_integrity import snapshot_package


MATCHED_CONDITIONS = {
    "model_id": "same_collaboration_runtime_unaudited",
    "tools": "same_workspace_tools",
    "network": "not_required",
    "task_budget": "one_subagent_turn",
    "max_findings": 6,
}


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _task(task_id: str):
    tasks = {task.task_id: task for task in load_code_review_fixtures()}
    if task_id not in tasks:
        raise ValueError(f"unknown task: {task_id}")
    return tasks[task_id]


def _existing_pair(task_id: str, run_root: Path) -> PreparedCodeReviewPair:
    task = _task(task_id)
    pair_root = run_root.resolve() / task_id
    return PreparedCodeReviewPair(
        task=task,
        pair_root=pair_root,
        generic_root=pair_root / "generic",
        configured_root=pair_root / "configured",
        source_public_snapshot=snapshot_package(task.public.root),
        private_snapshot=snapshot_package(task.private.root),
        arm_start_snapshot=snapshot_package(task.public.root),
        matched_conditions=MATCHED_CONDITIONS,
    )


def prepare(args) -> int:
    pairs = []
    for task in load_code_review_fixtures():
        pair = prepare_matched_pair(
            task, args.run_root, matched_conditions=MATCHED_CONDITIONS
        )
        pairs.append(
            {
                "task_id": task.task_id,
                "pair_root": str(pair.pair_root),
                "start_sha256": pair.arm_start_snapshot.sha256,
            }
        )
    _write_json(args.manifest_output, {"pairs": pairs})
    print(f"prepared {len(pairs)} matched code-review pairs")
    return 0


def begin(args) -> int:
    boundary = begin_arm_run(
        _existing_pair(args.task_id, args.run_root), args.arm
    )
    save_arm_boundary(boundary, args.boundary_output)
    print(str(boundary.workspace))
    return 0


def complete(args) -> int:
    report = complete_arm_run(
        load_arm_boundary(args.boundary_input),
        agent_result=args.agent_result,
        provider_metadata=None,
    )
    _write_json(args.report_output, report)
    metrics = report["evaluator"]["metrics"] or {}
    print(
        f"{report['task_id']} {report['arm']}: valid={report['valid_run']} "
        f"recall={metrics.get('severity_weighted_recall')} "
        f"precision={metrics.get('precision')} "
        f"false_positives={metrics.get('false_positive_count')}"
    )
    return 0 if report["valid_run"] else 2


def summarize(args) -> int:
    reports = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(args.reports_root.glob("CRV-P*-*.json"))
    ]
    _write_json(args.report_output, summarize_code_review_reports(reports))
    print(f"summarized {len(reports)} arm reports")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(required=True)

    command = commands.add_parser("prepare")
    command.add_argument("--run-root", type=Path, required=True)
    command.add_argument("--manifest-output", type=Path, required=True)
    command.set_defaults(function=prepare)

    command = commands.add_parser("begin")
    command.add_argument("--run-root", type=Path, required=True)
    command.add_argument("--task-id", required=True)
    command.add_argument(
        "--arm", choices=("generic", "configured"), required=True
    )
    command.add_argument("--boundary-output", type=Path, required=True)
    command.set_defaults(function=begin)

    command = commands.add_parser("complete")
    command.add_argument("--boundary-input", type=Path, required=True)
    command.add_argument("--report-output", type=Path, required=True)
    command.add_argument(
        "--agent-result", default="agent completed assigned review"
    )
    command.set_defaults(function=complete)

    command = commands.add_parser("summarize")
    command.add_argument("--reports-root", type=Path, required=True)
    command.add_argument("--report-output", type=Path, required=True)
    command.set_defaults(function=summarize)
    return root


def main() -> int:
    args = parser().parse_args()
    return args.function(args)


if __name__ == "__main__":
    raise SystemExit(main())

