"""CLI for manual/sub-agent POC 6c code-development pilot runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from workloads.code_development import (
    PreparedCodeDevelopmentPair,
    begin_arm_run,
    complete_arm_run,
    load_arm_boundary,
    load_code_development_fixtures,
    prepare_matched_pair,
    save_arm_boundary,
    summarize_code_development_reports,
)
from workloads.fixture_integrity import snapshot_package


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _task(task_id: str):
    tasks = {
        task.task_id: task for task in load_code_development_fixtures()
    }
    if task_id not in tasks:
        raise ValueError(f"unknown task: {task_id}")
    return tasks[task_id]


def _existing_pair(task_id: str, run_root: Path) -> PreparedCodeDevelopmentPair:
    task = _task(task_id)
    pair_root = run_root.resolve() / task_id
    return PreparedCodeDevelopmentPair(
        task=task,
        pair_root=pair_root,
        generic_root=pair_root / "generic",
        configured_root=pair_root / "configured",
        source_public_snapshot=snapshot_package(task.public.root),
        private_snapshot=snapshot_package(task.private.root),
        arm_start_snapshot=snapshot_package(task.public.root),
        matched_conditions={
            "model_id": "same_collaboration_runtime_unaudited",
            "tools": "same_workspace_tools",
            "network": "not_required",
            "task_budget": "one_subagent_turn",
            "provider_usage": None,
        },
    )


def prepare(args) -> int:
    prepared = []
    for task in load_code_development_fixtures():
        pair = prepare_matched_pair(
            task,
            args.run_root,
            matched_conditions={
                "model_id": "same_collaboration_runtime_unaudited",
                "tools": "same_workspace_tools",
                "network": "not_required",
                "task_budget": "one_subagent_turn",
                "provider_usage": None,
            },
        )
        prepared.append(
            {
                "task_id": task.task_id,
                "pair_root": str(pair.pair_root),
                "start_sha256": pair.arm_start_snapshot.sha256,
            }
        )
    _write_json(args.manifest_output, {"pairs": prepared})
    print(f"prepared {len(prepared)} matched code-development pairs")
    return 0


def begin(args) -> int:
    boundary = begin_arm_run(
        _existing_pair(args.task_id, args.run_root),
        args.arm,
    )
    save_arm_boundary(boundary, args.boundary_output)
    print(str(boundary.workspace))
    return 0


def complete(args) -> int:
    boundary = load_arm_boundary(args.boundary_input)
    report = complete_arm_run(
        boundary,
        agent_result=args.agent_result,
        provider_metadata=None,
    )
    _write_json(args.report_output, report)
    print(
        f"{report['task_id']} {report['arm']}: "
        f"valid={report['valid_run']} "
        f"passed={report['evaluator']['passed']}/"
        f"{report['evaluator']['total']}"
    )
    return 0 if report["valid_run"] else 2


def summarize(args) -> int:
    reports = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(args.reports_root.glob("DEV-P*-*.json"))
    ]
    summary = summarize_code_development_reports(reports)
    _write_json(args.report_output, summary)
    print(f"summarized {len(reports)} arm reports")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(required=True)

    prepare_command = commands.add_parser("prepare")
    prepare_command.add_argument("--run-root", type=Path, required=True)
    prepare_command.add_argument("--manifest-output", type=Path, required=True)
    prepare_command.set_defaults(function=prepare)

    begin_command = commands.add_parser("begin")
    begin_command.add_argument("--run-root", type=Path, required=True)
    begin_command.add_argument("--task-id", required=True)
    begin_command.add_argument(
        "--arm",
        choices=("generic", "configured"),
        required=True,
    )
    begin_command.add_argument("--boundary-output", type=Path, required=True)
    begin_command.set_defaults(function=begin)

    complete_command = commands.add_parser("complete")
    complete_command.add_argument("--boundary-input", type=Path, required=True)
    complete_command.add_argument("--report-output", type=Path, required=True)
    complete_command.add_argument(
        "--agent-result",
        default="agent completed assigned workspace task",
    )
    complete_command.set_defaults(function=complete)

    summarize_command = commands.add_parser("summarize")
    summarize_command.add_argument("--reports-root", type=Path, required=True)
    summarize_command.add_argument("--report-output", type=Path, required=True)
    summarize_command.set_defaults(function=summarize)
    return root


def main() -> int:
    args = parser().parse_args()
    return args.function(args)


if __name__ == "__main__":
    raise SystemExit(main())
