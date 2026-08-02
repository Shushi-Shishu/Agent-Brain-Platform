"""Generate blind pilot artifacts or deblind validated evaluator scores."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from corpus import FrozenCorpus
from evaluation import (
    deblind_score_rows,
    evaluator_agreement,
    pilot_descriptive_summary,
    validate_blind_scores,
)
from pilot import blinded_cases, operational_summary, validate_pilot_output


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def arm_mapping(case_ids: list[str], salt: str) -> dict[str, str]:
    mapping = {}
    for case_id in case_ids:
        for arm in ("generic", "configured"):
            digest = hashlib.sha256(
                f"{salt}\0{case_id}\0{arm}".encode("utf-8")
            ).hexdigest()
            mapping["B-" + digest[:16].upper()] = arm
    return mapping


def blind(args) -> int:
    salt = os.environ.get("POC6C_BLIND_SALT")
    if not salt or len(salt) < 16:
        raise RuntimeError("POC6C_BLIND_SALT must contain at least 16 characters")
    corpus = FrozenCorpus()
    generic = read_json(args.generic)
    configured = read_json(args.configured)
    generic_errors = validate_pilot_output(generic, corpus)
    configured_errors = validate_pilot_output(configured, corpus)
    if generic_errors or configured_errors:
        print(
            json.dumps(
                {
                    "generic_errors": generic_errors,
                    "configured_errors": configured_errors,
                },
                indent=2,
            )
        )
        return 2
    blind_payload = blinded_cases(generic, configured, salt=salt)
    mapping = arm_mapping(
        [case["case_id"] for case in blind_payload],
        salt,
    )
    write_json(args.blind_output, blind_payload)
    write_json(args.mapping_output, mapping)
    if args.instrumentation_output is not None:
        write_json(
            args.instrumentation_output,
            operational_summary(generic, configured),
        )
    print(f"validated and blinded {len(blind_payload)} paired cases")
    return 0


def score(args) -> int:
    blind_payload = read_json(args.blind_input)
    scores = read_json(args.scores)
    errors = validate_blind_scores(scores, blind_payload)
    if errors:
        print(json.dumps({"score_errors": errors}, indent=2))
        return 2
    mapping = read_json(args.mapping_input)
    rows = deblind_score_rows(scores, mapping)
    report = {
        "summary": pilot_descriptive_summary(rows),
        "rows": rows,
    }
    write_json(args.report_output, report)
    print("validated scores and wrote diagnostic report")
    return 0


def agree(args) -> int:
    blind_payload = read_json(args.blind_input)
    first = read_json(args.first_scores)
    second = read_json(args.second_scores)
    errors = {
        "first_score_errors": validate_blind_scores(first, blind_payload),
        "second_score_errors": validate_blind_scores(second, blind_payload),
    }
    if any(errors.values()):
        print(json.dumps(errors, indent=2))
        return 2
    write_json(args.report_output, evaluator_agreement(first, second))
    print("validated both evaluators and wrote agreement report")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(required=True)
    blind_command = commands.add_parser("blind")
    blind_command.add_argument("--generic", type=Path, required=True)
    blind_command.add_argument("--configured", type=Path, required=True)
    blind_command.add_argument("--blind-output", type=Path, required=True)
    blind_command.add_argument("--mapping-output", type=Path, required=True)
    blind_command.add_argument("--instrumentation-output", type=Path)
    blind_command.set_defaults(function=blind)
    score_command = commands.add_parser("score")
    score_command.add_argument("--blind-input", type=Path, required=True)
    score_command.add_argument("--mapping-input", type=Path, required=True)
    score_command.add_argument("--scores", type=Path, required=True)
    score_command.add_argument("--report-output", type=Path, required=True)
    score_command.set_defaults(function=score)
    agree_command = commands.add_parser("agree")
    agree_command.add_argument("--blind-input", type=Path, required=True)
    agree_command.add_argument("--first-scores", type=Path, required=True)
    agree_command.add_argument("--second-scores", type=Path, required=True)
    agree_command.add_argument("--report-output", type=Path, required=True)
    agree_command.set_defaults(function=agree)
    return root


def main() -> int:
    args = parser().parse_args()
    return args.function(args)


if __name__ == "__main__":
    raise SystemExit(main())
