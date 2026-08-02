# POC 6a — Historical Project 008 Corpus Transfer

## Verdict

**FAIL under the rules locked before the first replay.**

The overall policy ranking transferred strongly from simulation to a real
corpus, but workload-dependent viability/disqualification did not transfer
across the two historical query strata.

## Objective

POC 6a asked:

> Do the branch-selection results from our simulation predict policy behavior
> when searching the actual Project 008 knowledge vault?

This was a historical metadata replay. It was not a live LLM test.

## Historical benchmark

The locked Project 008 snapshot contained:

- 1,030 manifest notes;
- 957 tagged, non-empty indexed documents;
- 240 eligible tag queries;
- 12 retrieval arms;
- 95 selection queries;
- 145 untouched confirmation queries.

Existing tag metadata defined which documents were relevant. All YAML
frontmatter, including the tags, was removed from searchable text. BM25 ranked
the remaining title/body content inside each vault arm.

Queries were divided into:

- 72 concentrated confirmation queries, where at least 70% of relevant notes
  were in one arm;
- 73 diffuse confirmation queries.

Each policy could retrieve 48 documents and received immediate offline
relevance feedback.

## Locked result

| Condition | Result |
|---|---|
| Snapshot and benchmark integrity | PASS |
| Positive relevance signal | PASS |
| Simulation ranking correlation >0.60 | **PASS — 0.943** |
| Policy swings between viable and disqualified | **FAIL — none** |
| ExploreThenCommit viable somewhere | PASS |

Every condition was required, so the POC failed.

## Policy ranking transfer

| Rank | Simulation | Historical corpus |
|---:|---|---|
| 1 | ExploreThenCommit | Epsilon Greedy |
| 2 | Epsilon Greedy | ExploreThenCommit |
| 3 | Thompson Sampling | Thompson Sampling |
| 4 | UCB | UCB |
| 5 | Discounted Thompson | Discounted Thompson |
| 6 | Round Robin | Round Robin |

Only the top two policies exchanged position. Spearman rank correlation was
`0.943`.

That is meaningful partial transfer: simulation was useful for prioritizing
which policies to test on the corpus.

## Concentrated queries

The selection split locked Epsilon Greedy as the reference.

| Policy | Status | Findings | Recall | Reference % |
|---|---|---:|---:|---:|
| Epsilon Greedy | viable | 5.278 | 50.0% | 100.0% |
| ExploreThenCommit | viable | 5.153 | 48.3% | 97.6% |
| Thompson Sampling | uncertain | 4.847 | 47.4% | 91.8% |
| Discounted Thompson | uncertain | 4.347 | 44.1% | 82.4% |
| UCB | uncertain | 4.306 | 43.5% | 81.6% |
| Round Robin | **disqualified** | 3.194 | 34.4% | 60.5% |

Epsilon Greedy improved over ExploreThenCommit by 2.43%. The paired 95%
interval for the difference was `[0.009, 0.241]` findings.

## Diffuse queries

The selection split locked Thompson Sampling as the reference.

| Policy | Status | Findings | Recall | Reference % |
|---|---|---:|---:|---:|
| Epsilon Greedy | uncertain | 5.014 | 51.7% | 102.8% |
| Thompson Sampling | viable | 4.877 | 54.5% | 100.0% |
| ExploreThenCommit | uncertain | 4.658 | 47.8% | 95.5% |
| UCB | uncertain | 4.589 | 52.5% | 94.1% |
| Discounted Thompson | uncertain | 4.466 | 51.5% | 91.6% |
| Round Robin | uncertain | 3.945 | 46.7% | 80.9% |

Epsilon Greedy had the highest confirmation mean even though selection had
locked Thompson. Differences were too uncertain to disqualify any policy.

## Why the gate failed

The gate required at least one policy to be viable in one stratum and
disqualified in the other.

Round Robin was disqualified for concentrated queries, but was uncertain—not
viable—for diffuse queries. The remaining policies were viable or uncertain
in both strata.

Therefore, the historical corpus did not support choosing controllers from
the concentrated/diffuse label.

## Product meaning

Supported:

- simulation can prioritize candidate policies before corpus testing;
- historical replay can reject a clearly harmful policy;
- Epsilon Greedy and ExploreThenCommit are strong defaults here;
- effect sizes and uncertainty can be measured without running an LLM.

Not supported:

- a static mapping from concentration to policy;
- the simulation's regime-dependent swing on this corpus;
- live-agent transfer;
- metadata tags as production-quality reviewed relevance judgments;
- automatic reward generation.

The best current workflow is:

```text
Use simulation to shortlist candidates
        ↓
Replay them on the actual corpus or historical tasks
        ↓
Reject clear failures
        ↓
Keep a robust default when differences remain uncertain
```

## Important limitations

The labels are historical metadata, not independently reviewed judgments. The
query is derived from the same tag used as the label, although tags were
hidden from searchable text.

The vault is also highly imbalanced:

- `AI & SDLC`: 491 indexed documents;
- `raw`: 254;
- `Learning`: 102;
- several arms contain fewer than ten documents;
- `Synthesis` contains no eligible tagged indexed document.

This real imbalance is valuable for transfer testing, but differs substantially
from the balanced simulation.

## Reproduce

The replay is valid only while the locked Project 008 manifest hash matches.

```bash
cd poc6a
python -m unittest -v
python experiment.py
```

The runner exits with code `2` because the locked verdict is FAIL. Full
machine-readable results, including per-query scores, are in `results.json`.
