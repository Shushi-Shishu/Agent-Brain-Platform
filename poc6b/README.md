# POC 6b — Reviewed Real-Case Transfer

## Current status

**Preparation only — reframed as search-task and evidence fixtures.**

POC 6a showed that simulation predicted broad policy ranking on Project 008,
but its metadata labels were too weak to establish workload-dependent policy
selection. POC 6b supplies realistic questions, evidence candidates, hard
negatives, and incomplete-corpus cases for a matched agent comparison.

Project 008 is not presumed to contain a complete answer. The primary question
is whether a configured Agent Brain agent searches, stops, cites, detects
missing evidence, and controls cost better than a normal general-purpose
sub-agent with the same model, tools, data, and budget.

## Package contents

- `cases_seed.json` — 30 proposed real questions
- `build_review_pack.py` — deterministic candidate-note and excerpt builder
- `cases.draft.json` — machine-readable draft review state
- `GOLD_SET_REVIEW.md` — human-friendly review worksheet
- `review_batches/` — the same worksheet split into three ten-case batches
- `assistant_pre_review/` — non-authoritative assistant recommendations that
  leave all formal human labels and approval fields untouched

The package contains:

- 25 answerable candidate cases;
- 5 deliberate abstention cases;
- 3 metadata-supported candidate notes per answer case;
- 2 BM25 hard negatives per answer case;
- 5 BM25 challenge results per abstention case.

## Important rule

Nothing in `cases.draft.json` is accepted ground truth yet.

Tags, lexical scores, and generated excerpts only reduce reviewer effort. A
case becomes eligible for POC 6b only after a human confirms:

- the question is realistic;
- answer versus abstention behavior;
- relevant and irrelevant notes;
- exact supporting passages;
- required answer points;
- unsupported claims;
- final case approval.

## How the fixtures will be used

Cases will be split before execution into configuration-selection and untouched
confirmation sets. The first paired run will compare:

- a generic sub-agent control; and
- a configured Agent Brain agent.

Both arms receive identical access. Vault-only and vault-plus-web modes are
reported separately; web search is a shared tool, not the answer key. The
final preregistration will lock the controller configuration, retrieval budget,
blinded evaluator, quality/cost metrics, split, and pass/fail conditions.

The cross-workload plan covering search, code development, code review, code
testing, and transaction economics is in [`../poc6c/PLAN.md`](../poc6c/PLAN.md).

## Rebuild the draft

The builder requires the locked Project 008 manifest snapshot.

```bash
cd poc6b
python build_review_pack.py
```

Rebuilding overwrites the draft JSON and Markdown review worksheet. Do not
rebuild after review has begun unless review changes have first been preserved.
