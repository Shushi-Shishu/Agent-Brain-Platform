"""Deterministic integrity checks for the frozen search confirmation tasks."""

from __future__ import annotations

import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


EXPECTED_IDS = [f"C{index:03d}" for index in range(1, 33)]
EXPECTED_MANIFEST = (
    "6BBA908F43640349937E94AEC9054E0DB16E9561265057099FBDFFEE8C6A8B3F"
)
EXPECTED_CONTENT = (
    "F8B2787816BC5F7E84EC3E26A50ED94C6A9CAE735357A3FD11B23F4824F46823"
)
EXPECTED_INDEXED_CONTENT = (
    "E7EE682DCE4175752FF38861E49EE5EA6836D7830AE37E1353640638657D084A"
)
EXPECTED_BUDGET = {"max_search_queries": 4, "max_documents_read": 6}
EXPECTED_COVERAGE = {"answerable_likely": 24, "partial_likely": 8}
EXPECTED_TOPIC_FAMILIES = {
    "agent_information_systems": 4,
    "ml_math_foundations": 4,
    "decision_search_alignment": 4,
    "compute_model_architecture": 4,
    "engineering_organization_design": 4,
    "business_finance_security": 4,
    "gap_sensitive_specialist_requests": 8,
}
PUBLIC_ROOT_KEYS = {
    "version",
    "status",
    "access_mode",
    "corpus",
    "per_case_budget",
    "cases",
}
PUBLIC_CASE_KEYS = {"id", "question"}
TOKEN_SIMILARITY_LIMIT = 0.62
SEQUENCE_SIMILARITY_LIMIT = 0.84

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "before",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "should",
    "that",
    "the",
    "their",
    "to",
    "what",
    "when",
    "which",
    "while",
    "with",
}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def normalized_tokens(text: str) -> frozenset[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return frozenset(token for token in tokens if token not in STOP_WORDS)


def lexical_similarity(left: str, right: str) -> tuple[float, float]:
    left_tokens = normalized_tokens(left)
    right_tokens = normalized_tokens(right)
    union = left_tokens | right_tokens
    token_jaccard = (
        len(left_tokens & right_tokens) / len(union) if union else 1.0
    )
    normalized_left = " ".join(sorted(left_tokens))
    normalized_right = " ".join(sorted(right_tokens))
    sequence_ratio = SequenceMatcher(
        None, normalized_left, normalized_right, autojunk=False
    ).ratio()
    return token_jaccard, sequence_ratio


def _question_rows(payload: dict[str, Any], source: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    cases = payload.get("cases")
    if not isinstance(cases, list):
        return rows
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            continue
        case_id = case.get("id")
        question = case.get("question")
        if isinstance(case_id, str) and isinstance(question, str):
            rows.append((f"{source}:{case_id or index}", question))
    return rows


def validate_payloads(
    tasks: dict[str, Any],
    batch1: dict[str, Any],
    design: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    if set(tasks) != PUBLIC_ROOT_KEYS:
        errors.append("public task root fields drifted")
    if tasks.get("version") != 1:
        errors.append("task version drifted")
    if tasks.get("status") != "frozen_candidate_not_activated":
        errors.append("task status drifted")
    if tasks.get("access_mode") != "vault_only":
        errors.append("access mode must remain vault_only")
    if tasks.get("per_case_budget") != EXPECTED_BUDGET:
        errors.append("per-case budget drifted")

    corpus = tasks.get("corpus")
    if not isinstance(corpus, dict):
        errors.append("corpus lock is missing")
    else:
        if corpus.get("project008_manifest_sha256") != EXPECTED_MANIFEST:
            errors.append("manifest hash drifted")
        if corpus.get("project008_content_commitment_sha256") != EXPECTED_CONTENT:
            errors.append("content commitment drifted")
        if (
            corpus.get("project008_indexed_content_commitment_sha256")
            != EXPECTED_INDEXED_CONTENT
        ):
            errors.append("indexed content commitment drifted")

    cases = tasks.get("cases")
    if not isinstance(cases, list):
        errors.append("cases must be a list")
        cases = []
    if len(cases) != 32:
        errors.append("task file must contain exactly 32 cases")

    ids: list[str] = []
    questions: list[tuple[str, str]] = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"case {index} is not an object")
            continue
        if set(case) != PUBLIC_CASE_KEYS:
            errors.append(f"case {index} contains non-public fields")
        case_id = case.get("id")
        question = case.get("question")
        if not isinstance(case_id, str) or not re.fullmatch(r"C\d{3}", case_id):
            errors.append(f"case {index} has malformed ID")
        else:
            ids.append(case_id)
        if (
            not isinstance(question, str)
            or len(question.strip()) < 20
            or not question.strip().endswith("?")
        ):
            errors.append(f"case {index} has malformed question")
        elif isinstance(case_id, str):
            questions.append((case_id, question.strip()))

    if ids != EXPECTED_IDS:
        errors.append("case IDs must be exactly C001-C032 in order")
    if len(ids) != len(set(ids)):
        errors.append("duplicate case IDs detected")

    normalized = [normalized_tokens(question) for _, question in questions]
    if len(normalized) != len(set(normalized)):
        errors.append("duplicate confirmation questions detected")

    batch_rows = _question_rows(batch1, "batch1")
    batch_normalized = {
        normalized_tokens(question): label for label, question in batch_rows
    }
    for case_id, question in questions:
        if normalized_tokens(question) in batch_normalized:
            errors.append(
                f"{case_id} duplicates excluded {batch_normalized[normalized_tokens(question)]}"
            )

    all_comparisons: list[tuple[str, str, str, str]] = []
    for index, (left_id, left_question) in enumerate(questions):
        for right_id, right_question in questions[index + 1 :]:
            all_comparisons.append(
                (left_id, left_question, right_id, right_question)
            )
        for batch_id, batch_question in batch_rows:
            all_comparisons.append(
                (left_id, left_question, batch_id, batch_question)
            )
    for left_id, left_question, right_id, right_question in all_comparisons:
        token_score, sequence_score = lexical_similarity(
            left_question, right_question
        )
        if (
            token_score >= TOKEN_SIMILARITY_LIMIT
            or sequence_score >= SEQUENCE_SIMILARITY_LIMIT
        ):
            errors.append(
                f"too-high lexical similarity: {left_id} vs {right_id} "
                f"(token={token_score:.3f}, sequence={sequence_score:.3f})"
            )

    labels = design.get("labels")
    if not isinstance(labels, list):
        errors.append("sealed design labels must be a list")
        labels = []
    label_ids: list[str] = []
    coverage: Counter[str] = Counter()
    families: Counter[str] = Counter()
    for index, label in enumerate(labels):
        if not isinstance(label, dict):
            errors.append(f"sealed label {index} is malformed")
            continue
        label_id = label.get("id")
        likelihood = label.get("coverage_likelihood")
        family = label.get("topic_family")
        if isinstance(label_id, str):
            label_ids.append(label_id)
        if isinstance(likelihood, str):
            coverage[likelihood] += 1
        if isinstance(family, str):
            families[family] += 1
    if sorted(label_ids) != EXPECTED_IDS or len(label_ids) != len(set(label_ids)):
        errors.append("sealed design IDs do not map one-to-one to tasks")
    if dict(coverage) != EXPECTED_COVERAGE:
        errors.append("coverage-likelihood balance drifted")
    if dict(families) != EXPECTED_TOPIC_FAMILIES:
        errors.append("topic-family balance drifted")
    expected_balance = design.get("expected_balance")
    if expected_balance != {
        "coverage_likelihood": EXPECTED_COVERAGE,
        "topic_family": EXPECTED_TOPIC_FAMILIES,
    }:
        errors.append("declared sealed balance does not match the lock")

    return errors


def validate_files(
    tasks_path: Path,
    batch1_path: Path,
    design_path: Path,
) -> list[str]:
    return validate_payloads(
        _load(tasks_path),
        _load(batch1_path),
        _load(design_path),
    )


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    project_root = base.parents[1]
    validation_errors = validate_files(
        base / "tasks_v1.json",
        project_root / "poc6c" / "pilot" / "tasks_batch1.json",
        base / "sealed" / "design_labels_v1.json",
    )
    if validation_errors:
        raise SystemExit("\n".join(validation_errors))
    print("confirmation task lock validated: 32 cases")
