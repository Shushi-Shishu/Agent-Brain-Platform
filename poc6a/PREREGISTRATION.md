# POC 6a — Historical Corpus Transfer Preregistration

**Locked before first execution**: 2026-07-31

## Status and question

POC 6 remains the live-LLM transfer gate and still requires a real task,
reviewed outcomes, and model/tool execution. POC 6a is a narrower precursor:

> Does the branch-selection behavior observed in the simulation transfer to a
> real Project 008 retrieval corpus with pre-existing relevance metadata?

This is **historical metadata replay**, not live-agent transfer.

## Locked corpus snapshot

Source vault:

`C:\XboxGames\My Projects\08. Project_ID_008_Obsidian_Knowledge_Files`

Identity manifest:

`0. Exploration & Applicability Engine/state/identity-manifest.json`

Locked manifest SHA-256:

`6BBA908F43640349937E94AEC9054E0DB16E9561265057099FBDFFEE8C6A8B3F`

The manifest contains 1,030 notes at lock time. A snapshot mismatch fails the
integrity condition; the experiment will not silently substitute a later
vault state.

## Retrieval documents and labels

A document is eligible when:

- it is a manifest-tracked Markdown file outside
  `0. Exploration & Applicability Engine`;
- the file exists in the locked vault;
- it contains one single-line YAML `tags: [...]` field;
- it has non-empty body text after YAML frontmatter.

Tag metadata provides historical weak relevance labels. It is not assumed to
be independently human-reviewed.

For each eligible tag query:

- query text is the tag with hyphens and underscores replaced by spaces;
- relevant documents are documents whose hidden tag list contains that exact
  normalized tag;
- all YAML frontmatter, including tags, is removed from searchable text.

This prevents direct retrieval from the field used as ground truth. Natural
occurrence of the query concept in a title or body is legitimate evidence.

## Twelve retrieval arms

Eleven top-level vault folders are separate arms:

1. `AI & SDLC`
2. `raw`
3. `Learning`
4. `Business`
5. `Mathematics`
6. `Indian Stocks`
7. `Physics`
8. `Synthesis`
9. `Frontend`
10. `Chemistry`
11. `Biology`

Every other top-level location is merged into arm 12, `Other`.

Observed arm labels are deterministically permuted for every query from its
SHA-256 digest. Policies cannot exploit a fixed semantic arm position.

## Query eligibility and strata

A tag becomes a benchmark query when it:

- labels 5–80 documents inclusive;
- appears in at least two retrieval arms.

The locked snapshot produced 240 eligible tags in the pre-run audit.

Each query is classified for evaluation only:

- **concentrated**: at least 70% of its relevant documents are in one arm;
- **diffuse**: otherwise.

The policy does not receive the stratum label.

## Selection and confirmation split

For normalized tag string `t`:

1. compute `SHA256(UTF8(t))`;
2. take the first byte modulo 5;
3. buckets 0–1 are selection; buckets 2–4 are confirmation.

Locked audit counts:

| Stratum | Selection | Confirmation |
|---|---:|---:|
| concentrated | 37 | 72 |
| diffuse | 58 | 73 |
| total | 95 | 145 |

Confirmation queries cannot change policy choices or thresholds.

## Retrieval ranking

Documents are tokenized from title/body text after frontmatter removal using
lowercase ASCII alphanumeric tokens: `[a-z0-9]+`.

Global BM25 parameters are fixed:

- `k1 = 1.5`
- `b = 0.75`
- `idf = ln(1 + (N - df + 0.5)/(df + 0.5))`

Within each arm, documents are ordered by descending BM25 score, then
lexicographic relative path. Pulling an arm returns its next unseen document.
Reward is 1 when that document has the hidden query tag and 0 otherwise.

All policies face identical ranked arm lists. Arms naturally deplete because a
document can be returned only once within a query.

## Fixed decision contract

- Branches: `K = 12`
- Retrieval budget: `48` documents (`4 × K`)
- Immediate binary relevance feedback is available after each retrieval
- Pull cost is equal
- Objective: maximize relevant documents found within budget

Perfect tag feedback is an offline evaluator assumption. POC 6a does not solve
how production relevance feedback is obtained.

## Candidate policies

The exact POC 3 primary configurations are retained:

- `RoundRobin`
- `ExploreThenCommit`
- `EpsilonGreedy(e=0.1)`
- `UCB1(c=2.0)`
- `ThompsonSampling(prior=1.0)`
- `DiscountedThompson(g=0.9)`

Policy randomness uses deterministic query- and policy-specific seeds.

## Historical confirmation

Within each stratum, the highest selection mean becomes the locked reference.
Ties follow the candidate order above.

Against that locked reference on paired confirmation queries:

- **viable** when the lower 95% paired normal confidence bound of
  `policy - 0.95 × reference` is at least zero;
- **disqualified** when the upper 95% paired normal confidence bound of
  `policy - 0.80 × reference` is below zero;
- **uncertain** otherwise.

A policy **swings** when it is viable in one stratum and disqualified in the
other.

## Simulation transfer comparison

The simulation ranking is locked from `poc3/results.json` using the four
non-control cells at exactly `K=12`, `budget/K=4`:

- stationary needle;
- depleting needle;
- deceptive depleting;
- heterogeneous depleting.

For each policy, average its four confirmation means and rank descending.
Compare this with the policy ranking by mean findings across all 145 historical
confirmation queries using Spearman rank correlation with average ranks for
ties.

## Primary pass/fail rules

POC 6a **passes only if all conditions hold**:

1. **Snapshot and benchmark integrity:** manifest hash matches, exactly 240
   eligible queries are produced, confirmation has at least 60 cases in each
   stratum, and no indexed document text contains YAML frontmatter.
2. **Usable relevance signal:** each stratum's locked reference has positive
   mean confirmation findings.
3. **Simulation ranking transfers:** Spearman correlation between the locked
   simulation and historical rankings is greater than `0.60`.
4. **Regime dependence transfers:** at least one fixed policy swings between
   viable and disqualified across concentrated and diffuse queries.
5. **Simple baseline remains credible:** `ExploreThenCommit` is viable in at
   least one stratum.

POC 6a **fails** if any condition fails. Corpus rules, query thresholds,
strata, split, BM25, budget, candidates, classification, and correlation
threshold will not change after the first execution. Corrections require a new
POC identifier.

## Secondary outputs

- Corpus, document, tag, arm, and split counts
- Policy ranking and mean findings
- Per-stratum viability table
- Relevant-document recall within 48 pulls
- Locked-reference improvement over `ExploreThenCommit`
- Best/worst spread
- Per-query results for audit

These outputs explain but cannot alter the verdict.

## Limitations fixed in advance

- Historical metadata replay, not a live LLM agent
- Tags are weak labels and may have been model-generated or inconsistently
  reviewed
- Queries are derived from the same metadata that defines relevance, although
  metadata is hidden from retrieval
- Lexical BM25 only; no embeddings, reranker, or LLM
- Perfect immediate relevance feedback
- One vault snapshot, branch count, and budget
- Only two concentration strata
- No answer generation or final-answer quality
- Duplicate source notes remain separate documents
- No latency, evaluator, token, or monetary cost
- Correlation is across only six policies
