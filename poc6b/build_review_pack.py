"""Build the draft POC 6b gold-set review package from Project 008."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POC6A = ROOT / "poc6a"
sys.path.insert(0, str(POC6A))

from experiment import (  # noqa: E402
    BM25Index,
    EXPECTED_MANIFEST_SHA256,
    load_documents,
    manifest_sha256,
    query_tokens,
)


HERE = Path(__file__).resolve().parent
SEED_PATH = HERE / "cases_seed.json"
JSON_OUTPUT = HERE / "cases.draft.json"
MARKDOWN_OUTPUT = HERE / "GOLD_SET_REVIEW.md"
BATCH_DIRECTORY = HERE / "review_batches"
MAX_EXCERPT_CHARS = 700


def score_documents(index: BM25Index, terms: tuple[str, ...]):
    return sorted(
        index.documents,
        key=lambda document: (-index.score(document, terms), document.path),
    )


def best_excerpt(text: str, terms: tuple[str, ...]) -> str:
    paragraphs = [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]
    if not paragraphs:
        return ""

    def paragraph_score(paragraph: str):
        lowered = paragraph.lower()
        distinct = sum(term in lowered for term in set(terms))
        occurrences = sum(lowered.count(term) for term in terms)
        return distinct, occurrences, min(len(paragraph), MAX_EXCERPT_CHARS)

    selected = max(paragraphs, key=paragraph_score)
    if len(selected) > MAX_EXCERPT_CHARS:
        selected = selected[: MAX_EXCERPT_CHARS - 1].rstrip() + "…"
    return selected


def candidate_record(document, terms, index, source: str):
    return {
        "path": document.path,
        "arm": document.arm,
        "bm25_score": index.score(document, terms),
        "excerpt": best_excerpt(document.indexed_text, terms),
        "candidate_source": source,
        "human_relevance": None,
        "human_evidence_quality": None,
        "reviewer_notes": "",
    }


def build_cases():
    if manifest_sha256() != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError("Project 008 manifest no longer matches locked snapshot")

    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    documents, integrity = load_documents()
    index = BM25Index(documents)
    available_tags = {
        tag for document in documents for tag in document.tags
    }
    built_cases = []

    for seed_case in seed["cases"]:
        terms = query_tokens(seed_case["question"])
        ranked = score_documents(index, terms)
        seed_tags = set(seed_case["seed_tags"])
        missing_tags = seed_tags - available_tags
        if missing_tags:
            raise RuntimeError(
                f"{seed_case['id']} has unavailable tags: {sorted(missing_tags)}"
            )

        if seed_case["expected_behavior"] == "answer":
            positives = [
                document
                for document in ranked
                if seed_tags.intersection(document.tags)
            ][:3]
            negatives = [
                document
                for document in ranked
                if not seed_tags.intersection(document.tags)
            ][:2]
            candidate_relevant = [
                candidate_record(
                    document,
                    terms,
                    index,
                    "metadata_positive",
                )
                for document in positives
            ]
            hard_negatives = [
                candidate_record(
                    document,
                    terms,
                    index,
                    "bm25_hard_negative",
                )
                for document in negatives
            ]
        else:
            candidate_relevant = []
            hard_negatives = [
                candidate_record(
                    document,
                    terms,
                    index,
                    "abstention_challenge",
                )
                for document in ranked[:5]
            ]

        built_cases.append(
            {
                **seed_case,
                "status": "draft_requires_human_review",
                "candidate_relevant": candidate_relevant,
                "hard_negatives_or_abstention_challenges": hard_negatives,
                "required_answer_points": [],
                "forbidden_or_unsupported_claims": [],
                "review": {
                    "question_is_realistic": None,
                    "expected_behavior_confirmed": None,
                    "candidate_set_complete_enough": None,
                    "reviewer": "",
                    "reviewed_at": None,
                    "notes": "",
                },
            }
        )

    package = {
        "version": 1,
        "status": "DRAFT_NOT_GROUND_TRUTH",
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "document_count": integrity["document_count"],
        "instructions": (
            "Human review is required. Metadata positives and BM25 negatives "
            "are candidates, not accepted relevance judgments."
        ),
        "cases": built_cases,
    }
    return package


def render_candidate(candidate: dict, index: int) -> list[str]:
    return [
        f"{index}. `{candidate['path']}`",
        f"   - Arm: `{candidate['arm']}`",
        f"   - Candidate source: `{candidate['candidate_source']}`",
        f"   - BM25: `{candidate['bm25_score']:.3f}`",
        f"   - Excerpt: {candidate['excerpt']}",
        "   - Relevance: [ ] relevant  [ ] partially relevant  [ ] irrelevant",
        "   - Evidence quality: [ ] strong  [ ] usable  [ ] weak",
        "   - Reviewer note:",
        "",
    ]


def render_markdown(package: dict) -> str:
    lines = [
        "# POC 6b — Gold-Set Human Review",
        "",
        "> **Status: DRAFT — not ground truth.** Do not run the POC 6b verdict",
        "> until every included case has been reviewed and approved.",
        "",
        "## How to review",
        "",
        "For each case:",
        "",
        "1. Confirm that the question represents something you would genuinely ask.",
        "2. Confirm whether the system should answer or abstain.",
        "3. Mark every candidate note relevant, partially relevant, or irrelevant.",
        "4. Add missing relevant notes if the candidate set is incomplete.",
        "5. Write 2–5 required answer points supported by exact notes/passages.",
        "6. Record claims the system must not make without evidence.",
        "7. Mark the case approved only after the above fields are complete.",
        "",
        "A metadata-positive note is only a suggestion. A hard negative is a",
        "high-ranking lexical result without the seed tag; it may still be relevant.",
        "",
        "## Review summary",
        "",
        "| Case | Domain | Expected | Approved |",
        "|---|---|---|---|",
    ]
    for case in package["cases"]:
        lines.append(
            f"| {case['id']} | {case['domain']} | "
            f"{case['expected_behavior']} | [ ] |"
        )

    for case in package["cases"]:
        lines.extend(
            [
                "",
                "---",
                "",
                f"## {case['id']} — {case['domain']}",
                "",
                f"**Question:** {case['question']}",
                "",
                f"**Draft expected behavior:** `{case['expected_behavior']}`",
                "",
                f"**Seed tags:** "
                f"`{', '.join(case['seed_tags']) if case['seed_tags'] else 'none'}`",
                "",
                "### Case review",
                "",
                "- [ ] Question is realistic",
                "- [ ] Expected answer/abstention behavior is correct",
                "- [ ] Candidate set is complete enough",
                "- [ ] Required answer points are written",
                "- [ ] Unsupported claims are written",
                "- [ ] **Case approved**",
                "",
                "Reviewer:",
                "",
                "Review notes:",
                "",
                "### Candidate relevant notes",
                "",
            ]
        )
        if case["candidate_relevant"]:
            for index, candidate in enumerate(
                case["candidate_relevant"],
                start=1,
            ):
                lines.extend(render_candidate(candidate, index))
        else:
            lines.append(
                "_None proposed. This is a draft abstention case; review the "
                "challenge results below._"
            )
            lines.append("")

        lines.extend(
            [
                "### Hard negatives / abstention challenges",
                "",
            ]
        )
        for index, candidate in enumerate(
            case["hard_negatives_or_abstention_challenges"],
            start=1,
        ):
            lines.extend(render_candidate(candidate, index))

        lines.extend(
            [
                "### Required answer points",
                "",
                "1. ",
                "2. ",
                "3. ",
                "",
                "### Forbidden or unsupported claims",
                "",
                "- ",
                "",
                "### Missing relevant notes or passages",
                "",
                "- ",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    package = build_cases()
    JSON_OUTPUT.write_text(
        json.dumps(package, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    MARKDOWN_OUTPUT.write_text(render_markdown(package), encoding="utf-8")
    BATCH_DIRECTORY.mkdir(exist_ok=True)
    batch_paths = []
    for start in range(0, len(package["cases"]), 10):
        batch_cases = package["cases"][start : start + 10]
        batch_number = start // 10 + 1
        batch_path = BATCH_DIRECTORY / (
            f"BATCH_{batch_number:02d}_"
            f"{batch_cases[0]['id']}_{batch_cases[-1]['id']}.md"
        )
        batch_package = {**package, "cases": batch_cases}
        batch_path.write_text(
            render_markdown(batch_package),
            encoding="utf-8",
        )
        batch_paths.append(batch_path)
    answer_count = sum(
        case["expected_behavior"] == "answer"
        for case in package["cases"]
    )
    abstain_count = len(package["cases"]) - answer_count
    print(
        f"built {len(package['cases'])} draft cases "
        f"({answer_count} answer, {abstain_count} abstain)"
    )
    print(f"json: {JSON_OUTPUT}")
    print(f"review: {MARKDOWN_OUTPUT}")
    for batch_path in batch_paths:
        print(f"batch: {batch_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
