"""Integrity and access tests for the frozen Project 008 search facade."""

from __future__ import annotations

import unittest

from corpus import BudgetExhausted, CorpusError, FrozenCorpus, SearchSession


class FrozenCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = FrozenCorpus()

    def test_snapshot_and_content_commitment_are_stable(self):
        self.assertEqual(
            self.corpus.content_commitment,
            "F8B2787816BC5F7E84EC3E26A50ED94C6A9CAE735357A3FD11B23F4824F46823",
        )
        self.assertEqual(
            self.corpus.indexed_content_commitment,
            "E7EE682DCE4175752FF38861E49EE5EA6836D7830AE37E1353640638657D084A",
        )
        self.assertEqual(len(self.corpus.documents), 957)

    def test_search_is_deterministic(self):
        first = self.corpus.search("agent observability", limit=5)
        second = self.corpus.search("agent observability", limit=5)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 5)

    def test_search_hides_frontmatter(self):
        hit = self.corpus.search("agent observability", limit=1)[0]
        note = self.corpus.read_note(hit.path)
        self.assertFalse(note["content"].startswith("---\n"))

    def test_path_traversal_and_unindexed_files_are_rejected(self):
        with self.assertRaises(CorpusError):
            self.corpus.read_note("../VISION.md")
        with self.assertRaises(CorpusError):
            self.corpus.read_note("0. Exploration & Applicability Engine/plan.md")

    def test_directory_filter_is_restricted(self):
        with self.assertRaises(CorpusError):
            self.corpus.search("agent", directory="../raw")
        hits = self.corpus.search("agent", directory="AI & SDLC", limit=3)
        self.assertTrue(all(hit.arm == "AI & SDLC" for hit in hits))

    def test_budget_blocks_operation_before_execution(self):
        session = SearchSession(
            self.corpus,
            max_search_calls=1,
            max_read_calls=1,
        )
        hit = session.search("agent observability", limit=1)[0]
        session.read_note(hit.path)
        with self.assertRaises(BudgetExhausted):
            session.search("another query", limit=1)
        with self.assertRaises(BudgetExhausted):
            session.read_note(hit.path)
        self.assertEqual(session.remaining_budget(), {"search_calls": 0, "read_calls": 0})
        self.assertEqual(len(session.events), 2)


if __name__ == "__main__":
    unittest.main()
