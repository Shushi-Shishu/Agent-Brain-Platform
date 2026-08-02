"""Frozen Project 008 corpus facade and budgeted search tools for POC 6c."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POC6A = ROOT / "poc6a"
sys.path.insert(0, str(POC6A))

from experiment import (  # noqa: E402
    BM25Index,
    EXPECTED_MANIFEST_SHA256,
    MANIFEST_PATH,
    arm_for_path,
    load_documents,
    manifest_sha256,
    query_tokens,
)

from trace import sha256_text  # noqa: E402


MAX_EXCERPT_CHARS = 700


class CorpusError(RuntimeError):
    """Raised when corpus integrity or access restrictions fail."""


class BudgetExhausted(CorpusError):
    """Raised before a search/read operation would exceed the locked budget."""


@dataclass(frozen=True)
class SearchHit:
    path: str
    arm: str
    score: float
    excerpt: str
    content_sha256: str


def manifest_content_commitment() -> str:
    """Hash the manifest's path/content pairs as a corpus commitment."""

    if manifest_sha256() != EXPECTED_MANIFEST_SHA256:
        raise CorpusError("Project 008 manifest does not match locked snapshot")
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    notes = payload.get("notes")
    if not isinstance(notes, dict) or not notes:
        raise CorpusError("identity manifest contains no notes")
    rows: list[str] = []
    for record in notes.values():
        if not isinstance(record, dict):
            raise CorpusError("invalid identity manifest record")
        path = record.get("current_path")
        content_hash = record.get("content_hash_at_assignment")
        if not isinstance(path, str) or not isinstance(content_hash, str):
            raise CorpusError("manifest record lacks path/content hash")
        rows.append(f"{path.replace(chr(92), '/')}\0{content_hash.lower()}")
    return sha256_text("\n".join(sorted(rows)))


def indexed_content_commitment(documents: Any) -> str:
    """Commit to the exact note bodies exposed by the benchmark.

    The identity manifest's assignment hashes prove which note identities were
    locked.  This second commitment covers the post-frontmatter text actually
    searchable and readable by either arm, closing the gap between identity
    metadata and benchmark-visible bytes.
    """

    rows = [
        f"{document.path}\0{sha256_text(document.indexed_text)}"
        for document in documents
    ]
    if not rows:
        raise CorpusError("indexed corpus contains no documents")
    return sha256_text("\n".join(sorted(rows)))


def _best_excerpt(text: str, terms: tuple[str, ...]) -> str:
    paragraphs = [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]
    if not paragraphs:
        return ""

    def score(paragraph: str) -> tuple[int, int, int]:
        lowered = paragraph.lower()
        return (
            sum(term in lowered for term in set(terms)),
            sum(lowered.count(term) for term in terms),
            min(len(paragraph), MAX_EXCERPT_CHARS),
        )

    selected = max(paragraphs, key=score)
    if len(selected) > MAX_EXCERPT_CHARS:
        return selected[: MAX_EXCERPT_CHARS - 1].rstrip() + "…"
    return selected


class FrozenCorpus:
    """Read-only deterministic search over the locked Project 008 snapshot."""

    def __init__(self) -> None:
        if manifest_sha256() != EXPECTED_MANIFEST_SHA256:
            raise CorpusError("Project 008 manifest no longer matches snapshot")
        documents, integrity = load_documents()
        self.documents = tuple(documents)
        self.integrity = integrity
        self.index = BM25Index(documents)
        self.by_path = {document.path: document for document in documents}
        self.content_commitment = manifest_content_commitment()
        self.indexed_content_commitment = indexed_content_commitment(
            self.documents
        )

    def search(
        self,
        query: str,
        *,
        directory: str | None = None,
        limit: int = 5,
    ) -> list[SearchHit]:
        if not isinstance(query, str) or not query.strip():
            raise CorpusError("search query must be non-empty")
        if not isinstance(limit, int) or not 1 <= limit <= 20:
            raise CorpusError("search limit must be between 1 and 20")
        if directory is not None and (
            not isinstance(directory, str)
            or "/" in directory
            or "\\" in directory
            or directory in {".", ".."}
        ):
            raise CorpusError("directory filter must be one top-level arm")

        terms = query_tokens(query)
        ranked = sorted(
            self.documents,
            key=lambda document: (
                -self.index.score(document, terms),
                document.path,
            ),
        )
        if directory is not None:
            ranked = [
                document
                for document in ranked
                if arm_for_path(document.path) == directory
            ]
        hits: list[SearchHit] = []
        for document in ranked[:limit]:
            hits.append(
                SearchHit(
                    path=document.path,
                    arm=document.arm,
                    score=self.index.score(document, terms),
                    excerpt=_best_excerpt(document.indexed_text, terms),
                    content_sha256=sha256_text(document.indexed_text),
                )
            )
        return hits

    def read_note(self, relative_path: str) -> dict[str, str]:
        if not isinstance(relative_path, str) or not relative_path:
            raise CorpusError("note path must be non-empty")
        candidate = Path(relative_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise CorpusError("note path escapes the frozen corpus")
        normalized = relative_path.replace("\\", "/")
        document = self.by_path.get(normalized)
        if document is None:
            raise CorpusError("note is not in the indexed frozen corpus")
        return {
            "path": document.path,
            "arm": document.arm,
            "content": document.indexed_text,
            "content_sha256": sha256_text(document.indexed_text),
        }


class SearchSession:
    """Budget-enforcing tool session shared by either experimental arm."""

    def __init__(
        self,
        corpus: FrozenCorpus,
        *,
        max_search_calls: int,
        max_read_calls: int,
    ) -> None:
        if max_search_calls < 0 or max_read_calls < 0:
            raise ValueError("budgets must be non-negative")
        self.corpus = corpus
        self.max_search_calls = max_search_calls
        self.max_read_calls = max_read_calls
        self.search_calls = 0
        self.read_calls = 0
        self.events: list[dict[str, Any]] = []

    def _record(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append(
            {
                "sequence": len(self.events) + 1,
                "type": event_type,
                **payload,
            }
        )

    def search(
        self,
        query: str,
        *,
        directory: str | None = None,
        limit: int = 5,
    ) -> list[SearchHit]:
        if self.search_calls >= self.max_search_calls:
            raise BudgetExhausted("search-call budget exhausted")
        self.search_calls += 1
        hits = self.corpus.search(query, directory=directory, limit=limit)
        self._record(
            "vault_search",
            {
                "query": query,
                "directory": directory,
                "limit": limit,
                "result_paths": [hit.path for hit in hits],
            },
        )
        return hits

    def read_note(self, relative_path: str) -> dict[str, str]:
        if self.read_calls >= self.max_read_calls:
            raise BudgetExhausted("read-call budget exhausted")
        note = self.corpus.read_note(relative_path)
        self.read_calls += 1
        self._record(
            "document_read",
            {
                "path": note["path"],
                "content_sha256": note["content_sha256"],
            },
        )
        return note

    def remaining_budget(self) -> dict[str, int]:
        return {
            "search_calls": self.max_search_calls - self.search_calls,
            "read_calls": self.max_read_calls - self.read_calls,
        }
