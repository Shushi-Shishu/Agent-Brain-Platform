"""POC 6a historical Project 008 corpus-transfer experiment.

The protocol and verdict rules are locked in PREREGISTRATION.md. This is
historical metadata replay, not live-LLM transfer.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
POC2B = ROOT / "poc2b"
import os as _os
PROJECT008 = Path(
    _os.environ.get(
        "PROJECT008_PATH",
        r"C:\Users\C5332030\Shubham - Work\My_Projects\08. Project_ID_008_Obsidian_Knowledge_Files",
    )
)
MANIFEST_PATH = (
    PROJECT008
    / "0. Exploration & Applicability Engine"
    / "state"
    / "identity-manifest.json"
)
EXPECTED_MANIFEST_SHA256 = (
    "6BBA908F43640349937E94AEC9054E0DB16E9561265057099FBDFFEE8C6A8B3F"
)
POC3_RESULTS = ROOT / "poc3" / "results.json"

sys.path.insert(0, str(POC2B))

from environment import PotentialOutcomeEnv  # noqa: E402
from policies import (  # noqa: E402
    DiscountedThompson,
    EpsilonGreedy,
    ExploreThenCommit,
    RoundRobin,
    ThompsonSampling,
    UCB1,
)


BUDGET = 48
K = 12
BM25_K1 = 1.5
BM25_B = 0.75
Z_95 = 1.96
CORRELATION_THRESHOLD = 0.60
MIN_TAG_FREQUENCY = 5
MAX_TAG_FREQUENCY = 80
CONCENTRATION_THRESHOLD = 0.70
EXPECTED_ELIGIBLE_QUERIES = 240

ARM_NAMES = (
    "AI & SDLC",
    "raw",
    "Learning",
    "Business",
    "Mathematics",
    "Indian Stocks",
    "Physics",
    "Synthesis",
    "Frontend",
    "Chemistry",
    "Biology",
    "Other",
)
DIRECT_ARMS = set(ARM_NAMES[:-1])

POLICY_CLASSES = (
    RoundRobin,
    ExploreThenCommit,
    EpsilonGreedy,
    UCB1,
    ThompsonSampling,
    DiscountedThompson,
)
DISPLAY_NAMES = {
    RoundRobin: "RoundRobin",
    ExploreThenCommit: "ExploreThenCommit",
    EpsilonGreedy: "EpsilonGreedy(e=0.1)",
    UCB1: "UCB1(c=2.0)",
    ThompsonSampling: "ThompsonSampling(prior=1.0)",
    DiscountedThompson: "DiscountedThompson(g=0.9)",
}
POLICY_BY_NAME = {DISPLAY_NAMES[policy]: policy for policy in POLICY_CLASSES}
POLICY_INDEX = {policy: index for index, policy in enumerate(POLICY_CLASSES)}

NON_CONTROL_POC3_SHAPES = (
    "stationary_needle",
    "depleting_needle",
    "deceptive_depleting",
    "heterogeneous_depleting",
)

TOKEN_RE = re.compile(r"[a-z0-9]+")
TAGS_RE = re.compile(r"^tags:\s*\[(.*)\]\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class Document:
    path: str
    arm: str
    tags: frozenset[str]
    indexed_text: str
    tokens: tuple[str, ...]
    term_counts: Counter[str]


@dataclass(frozen=True)
class QueryCase:
    tag: str
    query_tokens: tuple[str, ...]
    stratum: str
    split: str
    relevant_count: int
    relevant_arm_count: int
    maximum_arm_share: float


def normalize_tag(raw: str) -> str:
    return raw.strip().strip("\"'").lower()


def query_tokens(tag: str) -> tuple[str, ...]:
    return tuple(TOKEN_RE.findall(tag.replace("-", " ").replace("_", " ")))


def arm_for_path(relative_path: str) -> str:
    top = relative_path.replace("\\", "/").split("/", 1)[0]
    return top if top in DIRECT_ARMS else "Other"


def split_frontmatter(content: str) -> tuple[str | None, str]:
    normalized = content.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return None, normalized
    end = normalized.find("\n---\n", 4)
    if end < 0:
        return None, normalized
    frontmatter = normalized[4:end]
    body = normalized[end + 5 :]
    return frontmatter, body


def parse_tags(frontmatter: str | None) -> frozenset[str]:
    if frontmatter is None:
        return frozenset()
    match = TAGS_RE.search(frontmatter)
    if match is None:
        return frozenset()
    return frozenset(
        tag
        for tag in (
            normalize_tag(raw_tag)
            for raw_tag in match.group(1).split(",")
        )
        if tag
    )


def manifest_sha256() -> str:
    return hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest().upper()


def load_documents() -> tuple[list[Document], dict[str, object]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    manifest_notes = manifest["notes"]
    documents: list[Document] = []
    missing_files: list[str] = []
    duplicate_paths: list[str] = []
    seen_paths: set[str] = set()

    for note in manifest_notes.values():
        relative_path = str(note["current_path"]).replace("\\", "/")
        if relative_path in seen_paths:
            duplicate_paths.append(relative_path)
            continue
        seen_paths.add(relative_path)
        if not relative_path.lower().endswith(".md"):
            continue
        if relative_path.startswith("0. Exploration & Applicability Engine/"):
            continue
        absolute_path = PROJECT008 / Path(relative_path)
        if not absolute_path.exists():
            missing_files.append(relative_path)
            continue
        content = absolute_path.read_text(encoding="utf-8-sig")
        frontmatter, body = split_frontmatter(content)
        tags = parse_tags(frontmatter)
        if not tags or not body.strip():
            continue
        tokens = tuple(TOKEN_RE.findall(body.lower()))
        if not tokens:
            continue
        documents.append(
            Document(
                path=relative_path,
                arm=arm_for_path(relative_path),
                tags=tags,
                indexed_text=body,
                tokens=tokens,
                term_counts=Counter(tokens),
            )
        )

    documents.sort(key=lambda document: document.path)
    integrity = {
        "manifest_note_count": len(manifest_notes),
        "document_count": len(documents),
        "missing_manifest_files": missing_files,
        "duplicate_manifest_paths": duplicate_paths,
        "all_indexed_frontmatter_removed": bool(
            documents
            and all(
                not document.indexed_text.replace("\r\n", "\n").startswith(
                    "---\n"
                )
                for document in documents
            )
        ),
        "arm_document_counts": {
            arm: sum(document.arm == arm for document in documents)
            for arm in ARM_NAMES
        },
    }
    return documents, integrity


def build_query_cases(documents: list[Document]) -> list[QueryCase]:
    tag_documents: dict[str, list[Document]] = defaultdict(list)
    for document in documents:
        for tag in document.tags:
            tag_documents[tag].append(document)

    cases: list[QueryCase] = []
    for tag, relevant_documents in tag_documents.items():
        count = len(relevant_documents)
        arm_counts = Counter(document.arm for document in relevant_documents)
        if (
            count < MIN_TAG_FREQUENCY
            or count > MAX_TAG_FREQUENCY
            or len(arm_counts) < 2
        ):
            continue
        maximum_share = max(arm_counts.values()) / count
        stratum = (
            "concentrated"
            if maximum_share >= CONCENTRATION_THRESHOLD
            else "diffuse"
        )
        digest = hashlib.sha256(tag.encode("utf-8")).digest()
        split = "selection" if digest[0] % 5 < 2 else "confirmation"
        cases.append(
            QueryCase(
                tag=tag,
                query_tokens=query_tokens(tag),
                stratum=stratum,
                split=split,
                relevant_count=count,
                relevant_arm_count=len(arm_counts),
                maximum_arm_share=maximum_share,
            )
        )
    return sorted(cases, key=lambda case: case.tag)


class BM25Index:
    def __init__(self, documents: list[Document]):
        self.documents = documents
        self.n = len(documents)
        self.average_length = float(
            np.mean([len(document.tokens) for document in documents])
        )
        self.document_frequency: Counter[str] = Counter()
        for document in documents:
            self.document_frequency.update(document.term_counts.keys())
        self.by_arm = {
            arm: [document for document in documents if document.arm == arm]
            for arm in ARM_NAMES
        }

    def score(self, document: Document, terms: tuple[str, ...]) -> float:
        score = 0.0
        length = len(document.tokens)
        length_normalizer = BM25_K1 * (
            1.0 - BM25_B + BM25_B * length / self.average_length
        )
        for term in terms:
            frequency = document.term_counts.get(term, 0)
            if frequency == 0:
                continue
            df = self.document_frequency[term]
            idf = math.log(
                1.0 + (self.n - df + 0.5) / (df + 0.5)
            )
            score += idf * (
                frequency * (BM25_K1 + 1.0)
                / (frequency + length_normalizer)
            )
        return score

    def ranked_arm_outcomes(self, case: QueryCase) -> np.ndarray:
        semantic_outcomes = np.zeros((K, BUDGET), dtype=np.int8)
        for arm_index, arm in enumerate(ARM_NAMES):
            ranked = sorted(
                self.by_arm[arm],
                key=lambda document: (
                    -self.score(document, case.query_tokens),
                    document.path,
                ),
            )
            for rank, document in enumerate(ranked[:BUDGET]):
                semantic_outcomes[arm_index, rank] = int(
                    case.tag in document.tags
                )

        digest = hashlib.sha256(case.tag.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "big", signed=False)
        permutation = np.random.default_rng(seed).permutation(K)
        return semantic_outcomes[permutation]


def policy_seed(case: QueryCase, policy_class: type) -> int:
    payload = f"{case.tag}\0{DISPLAY_NAMES[policy_class]}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def run_policy(
    policy_class: type,
    outcomes: np.ndarray,
    seed: int,
) -> int:
    env = PotentialOutcomeEnv(outcomes, BUDGET)
    policy = policy_class(K, np.random.default_rng(seed), BUDGET)
    total = 0
    while not env.done:
        arm = policy.select()
        reward = env.pull(arm)
        policy.update(arm, reward)
        total += reward
    return total


def evaluate_cases(
    cases: list[QueryCase],
    index: BM25Index,
) -> dict[str, dict[str, int]]:
    scores: dict[str, dict[str, int]] = {}
    for case_index, case in enumerate(cases, start=1):
        outcomes = index.ranked_arm_outcomes(case)
        scores[case.tag] = {
            DISPLAY_NAMES[policy_class]: run_policy(
                policy_class,
                outcomes,
                policy_seed(case, policy_class),
            )
            for policy_class in POLICY_CLASSES
        }
        if case_index % 25 == 0 or case_index == len(cases):
            print(f"  evaluated {case_index}/{len(cases)} queries")
    return scores


def lock_references(
    selection_cases: list[QueryCase],
    scores: dict[str, dict[str, int]],
) -> tuple[dict[str, str], dict[str, dict[str, float]]]:
    order = list(POLICY_BY_NAME)
    means: dict[str, dict[str, float]] = {}
    references: dict[str, str] = {}
    for stratum in ("concentrated", "diffuse"):
        tags = [case.tag for case in selection_cases if case.stratum == stratum]
        means[stratum] = {
            policy_name: float(
                np.mean([scores[tag][policy_name] for tag in tags])
            )
            for policy_name in order
        }
        references[stratum] = max(
            order,
            key=lambda name: (
                means[stratum][name],
                -order.index(name),
            ),
        )
    return references, means


def mean_ci(values: np.ndarray) -> tuple[float, float, float]:
    mean = float(values.mean())
    half = Z_95 * float(values.std(ddof=1)) / math.sqrt(len(values))
    return mean, mean - half, mean + half


def classify(
    candidate: np.ndarray,
    reference: np.ndarray,
) -> dict[str, object]:
    viable_mean, viable_low, viable_high = mean_ci(
        candidate - 0.95 * reference
    )
    disqual_mean, disqual_low, disqual_high = mean_ci(
        candidate - 0.80 * reference
    )
    if viable_low >= 0:
        status = "viable"
    elif disqual_high < 0:
        status = "disqualified"
    else:
        status = "uncertain"
    return {
        "status": status,
        "relative_to_locked_reference_pct": (
            100.0 * float(candidate.mean()) / float(reference.mean())
        ),
        "viability_stat": {
            "mean": viable_mean,
            "ci95": [viable_low, viable_high],
        },
        "disqualification_stat": {
            "mean": disqual_mean,
            "ci95": [disqual_low, disqual_high],
        },
    }


def descending_average_ranks(values: dict[str, float]) -> dict[str, float]:
    sorted_items = sorted(values.items(), key=lambda item: -item[1])
    ranks: dict[str, float] = {}
    position = 1
    index = 0
    while index < len(sorted_items):
        end = index + 1
        while (
            end < len(sorted_items)
            and math.isclose(
                sorted_items[end][1],
                sorted_items[index][1],
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            end += 1
        average_rank = (position + (position + end - index - 1)) / 2.0
        for name, _ in sorted_items[index:end]:
            ranks[name] = average_rank
        position += end - index
        index = end
    return ranks


def spearman(values_a: dict[str, float], values_b: dict[str, float]) -> float:
    names = list(POLICY_BY_NAME)
    ranks_a = descending_average_ranks(values_a)
    ranks_b = descending_average_ranks(values_b)
    a = np.asarray([ranks_a[name] for name in names], dtype=float)
    b = np.asarray([ranks_b[name] for name in names], dtype=float)
    return float(np.corrcoef(a, b)[0, 1])


def simulation_means() -> dict[str, float]:
    results = json.loads(POC3_RESULTS.read_text(encoding="utf-8"))
    means: dict[str, float] = {}
    for policy_name in POLICY_BY_NAME:
        means[policy_name] = float(
            np.mean(
                [
                    results["primary_cells"][
                        f"k12_b4_{shape}"
                    ]["policies"][policy_name]["mean"]
                    for shape in NON_CONTROL_POC3_SHAPES
                ]
            )
        )
    return means


def main() -> int:
    print("=" * 94)
    print("POC 6a - historical Project 008 corpus transfer")
    print("=" * 94)
    observed_hash = manifest_sha256()
    documents, corpus_integrity = load_documents()
    cases = build_query_cases(documents)
    selection_cases = [case for case in cases if case.split == "selection"]
    confirmation_cases = [
        case for case in cases if case.split == "confirmation"
    ]
    split_counts = {
        split: {
            stratum: sum(
                case.split == split and case.stratum == stratum
                for case in cases
            )
            for stratum in ("concentrated", "diffuse")
        }
        for split in ("selection", "confirmation")
    }

    print(
        f"manifest={len(json.loads(MANIFEST_PATH.read_text(encoding='utf-8-sig'))['notes'])} "
        f"indexed_docs={len(documents)} eligible_queries={len(cases)}"
    )
    print(
        "selection="
        f"{len(selection_cases)} confirmation={len(confirmation_cases)} "
        f"confirmation_strata={split_counts['confirmation']}"
    )

    index = BM25Index(documents)
    print("selection replay")
    selection_scores = evaluate_cases(selection_cases, index)
    references, selection_means = lock_references(
        selection_cases,
        selection_scores,
    )
    print(f"locked references: {references}")

    print("confirmation replay")
    confirmation_scores = evaluate_cases(confirmation_cases, index)

    statuses: dict[str, dict[str, str]] = {
        policy_name: {} for policy_name in POLICY_BY_NAME
    }
    stratum_results: dict[str, object] = {}
    positive_reference_means = True
    for stratum in ("concentrated", "diffuse"):
        stratum_cases = [
            case for case in confirmation_cases if case.stratum == stratum
        ]
        tags = [case.tag for case in stratum_cases]
        reference_name = references[stratum]
        reference = np.asarray(
            [confirmation_scores[tag][reference_name] for tag in tags],
            dtype=float,
        )
        positive_reference_means = (
            positive_reference_means and float(reference.mean()) > 0
        )
        policy_results: dict[str, object] = {}
        for policy_name in POLICY_BY_NAME:
            values = np.asarray(
                [confirmation_scores[tag][policy_name] for tag in tags],
                dtype=float,
            )
            classification = classify(values, reference)
            statuses[policy_name][stratum] = classification["status"]
            relevant_counts = np.asarray(
                [case.relevant_count for case in stratum_cases],
                dtype=float,
            )
            policy_results[policy_name] = {
                **classification,
                "mean_findings": float(values.mean()),
                "mean_recall": float(np.mean(values / relevant_counts)),
            }
        ranking = sorted(
            POLICY_BY_NAME,
            key=lambda name: policy_results[name]["mean_findings"],
            reverse=True,
        )
        etc = np.asarray(
            [
                confirmation_scores[tag]["ExploreThenCommit"]
                for tag in tags
            ],
            dtype=float,
        )
        ref_vs_etc_mean, ref_vs_etc_low, ref_vs_etc_high = mean_ci(
            reference - etc
        )
        stratum_results[stratum] = {
            "query_count": len(tags),
            "locked_reference": reference_name,
            "reference_mean_findings": float(reference.mean()),
            "confirmation_ranking": ranking,
            "policies": policy_results,
            "reference_vs_explore_then_commit": {
                "mean_difference": ref_vs_etc_mean,
                "difference_ci95": [ref_vs_etc_low, ref_vs_etc_high],
                "raw_uplift_pct": (
                    100.0 * (float(reference.mean()) / float(etc.mean()) - 1.0)
                    if float(etc.mean()) > 0
                    else None
                ),
            },
        }

    historical_means = {
        policy_name: float(
            np.mean(
                [
                    confirmation_scores[case.tag][policy_name]
                    for case in confirmation_cases
                ]
            )
        )
        for policy_name in POLICY_BY_NAME
    }
    locked_simulation_means = simulation_means()
    rank_correlation = spearman(
        locked_simulation_means,
        historical_means,
    )
    swinging_policies = [
        policy_name
        for policy_name, by_stratum in statuses.items()
        if "viable" in by_stratum.values()
        and "disqualified" in by_stratum.values()
    ]
    etc_viable = "viable" in statuses["ExploreThenCommit"].values()

    integrity_passed = bool(
        observed_hash == EXPECTED_MANIFEST_SHA256
        and len(cases) == EXPECTED_ELIGIBLE_QUERIES
        and split_counts["confirmation"]["concentrated"] >= 60
        and split_counts["confirmation"]["diffuse"] >= 60
        and corpus_integrity["all_indexed_frontmatter_removed"]
        and not corpus_integrity["missing_manifest_files"]
        and not corpus_integrity["duplicate_manifest_paths"]
    )
    conditions = {
        "snapshot_and_benchmark_integrity": integrity_passed,
        "usable_relevance_signal": bool(positive_reference_means),
        "simulation_ranking_transfers": bool(
            rank_correlation > CORRELATION_THRESHOLD
        ),
        "regime_dependence_transfers": bool(swinging_policies),
        "simple_baseline_credible": bool(etc_viable),
    }
    passed = all(conditions.values())

    query_audit = [
        {
            "tag": case.tag,
            "stratum": case.stratum,
            "split": case.split,
            "relevant_count": case.relevant_count,
            "relevant_arm_count": case.relevant_arm_count,
            "maximum_arm_share": case.maximum_arm_share,
            "scores": (
                selection_scores[case.tag]
                if case.split == "selection"
                else confirmation_scores[case.tag]
            ),
        }
        for case in cases
    ]
    results = {
        "design": {
            "vault": str(PROJECT008),
            "expected_manifest_sha256": EXPECTED_MANIFEST_SHA256,
            "observed_manifest_sha256": observed_hash,
            "k": K,
            "budget": BUDGET,
            "bm25": {"k1": BM25_K1, "b": BM25_B},
            "tag_frequency": [MIN_TAG_FREQUENCY, MAX_TAG_FREQUENCY],
            "concentration_threshold": CONCENTRATION_THRESHOLD,
            "policies": tuple(POLICY_BY_NAME),
            "preregistration": "PREREGISTRATION.md",
        },
        "corpus": {
            **corpus_integrity,
            "eligible_query_count": len(cases),
            "split_counts": split_counts,
        },
        "selection": {
            "locked_references": references,
            "mean_findings": selection_means,
        },
        "confirmation": {
            "strata": stratum_results,
            "statuses": statuses,
            "swinging_policies": swinging_policies,
            "historical_mean_findings": historical_means,
            "simulation_mean_findings": locked_simulation_means,
            "spearman_rank_correlation": rank_correlation,
        },
        "query_audit": query_audit,
        "verdict": {
            "conditions": conditions,
            "passed": bool(passed),
        },
    }

    print("\n" + "=" * 94)
    print("PRE-REGISTERED VERDICT")
    print("=" * 94)
    for condition, value in conditions.items():
        print(f"{condition}: {value}")
    print(f"Spearman simulation->historical: {rank_correlation:.3f}")
    print(f"swinging policies: {', '.join(swinging_policies) or 'none'}")
    print(f"POC 6a: {'PASS' if passed else 'FAIL'}")

    destination = Path(__file__).with_name("results.json")
    destination.write_text(
        json.dumps(results, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"results: {destination}")
    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main())
