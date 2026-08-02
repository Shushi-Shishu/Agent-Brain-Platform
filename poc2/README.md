# POC 2 — Falsification Test

**Date**: 2026-07-28
**Run**: `python experiment.py` (needs only numpy; ~30s)

---

## What this tests

POC 1 assumed that technique selection should be goal-aware — that the right
control policy for one agent is the wrong one for another — and expressed
that as ★ ratings per technique.

POC 2 tests the assumption instead of asserting it.

**Problem**: a relationship-search agent with `K=12` branches and a fixed
expansion budget. Branch yields are hidden and branches **deplete** as they
are mined, so the problem is non-stationary — the real shape of search.

**Design**: 5 task regimes × 6 control policies × 2000 paired trials.
Common random numbers — every policy faces a numerically identical
environment on trial *i*, so comparisons are paired. Significance by paired
bootstrap (10k resamples). `Greedy(LLM-proxy)` stands in for an unguided
LLM loop: sweep each branch once, then commit to the best so far.

---

## Results

| Regime | Winner | #1 vs #2 | Best vs worst | Uplift over naive loop |
|---|---|---|---|---|
| uniform | RoundRobin | +0.7% | 8% | **+7.9%** |
| needle | Greedy (naive) | +3.6% | **149%** | +0.0% |
| deceptive | ThompsonSampling | +0.6% | 21% | +2.8% |
| scarce | Greedy (naive) | +2.6% | 12% | +0.0% |
| rich | ThompsonSampling | +1.6% | 82% | **+11.1%** |

### Viability by regime

`viable` = within 5% of best · `weak` = 80–95% · `DISQUAL` = below 80%

| Policy | uniform | needle | deceptive | scarce | rich |
|---|---|---|---|---|---|
| RoundRobin | viable | **DISQUAL** | weak | weak | **DISQUAL** |
| UCB1 | viable | **DISQUAL** | weak | weak | weak |
| DiscountedThompson | viable | **DISQUAL** | weak | weak | **DISQUAL** |
| ThompsonSampling | viable | **DISQUAL** | viable | viable | viable |
| EpsilonGreedy | weak | viable | viable | viable | viable |
| Greedy (naive) | weak | viable | viable | viable | weak |

---

## Three findings

### 1. Ranking the top of the field is selling noise

Margins between the #1 and #2 technique run **0.6%–3.6%** in every regime.
The top two or three options are practically tied everywhere.

POC 1's core UI — Thompson Sampling ★★★★★ next to UCB ★★★★☆ — asserts a
difference the data does not support. **Star ratings are the wrong
abstraction.**

### 2. Disqualification is real, large, and goal-dependent

Four of six techniques swing from **viable to disqualified** depending on
the task. RoundRobin is the *best* policy under `uniform` and loses 60% of
findings under `needle`. Thompson Sampling is viable in four regimes and
disqualified in the fifth.

The signal is not "which is best" — it is **"which will destroy your
agent."** That is worth 149% in the worst case, and it is exactly what a
practitioner cannot work out unaided.

### 3. Sophistication pays 0–11%, and sometimes not at all

In `needle` and `scarce`, the naive loop is already optimal — a principled
controller adds nothing. In `rich` it adds 11.1%.

A platform that always recommends sophistication is wrong 40% of the time
on this problem. **It has to be able to say "your simple loop is fine."**

---

## What this means for the platform

| POC 1 assumed | POC 2 shows |
|---|---|
| Rank techniques by goal fit | Ranking the top is meaningless; **disqualify the bad ones** |
| ★ ratings communicate the answer | Ratings imply precision that does not exist |
| More technique = better agent | Naive is optimal in 2 of 5 regimes |
| Validator confirms "Valid" | Validator's job is **"this will fail, and here is the cost"** |

**The product is a linter, not a recommender.** POC 2 is empirical support
for that, from this project's own domain.

---

## Limitations — read before quoting any number

1. **Simulated, not LLM-in-the-loop.** This isolates the control-policy
   question deliberately. Whether it transfers to a live agent is untested.
2. **Regimes are hand-designed.** That winners differ across them is partly
   by construction. Findings 1 and 3 were *not* engineered — they emerged.
3. **One decision point only** (branch selection). Whether the pattern holds
   for stopping rules or tool routing is unknown.
4. **The naive baseline is generous** — it does a systematic sweep before
   committing, which a real LLM loop typically will not. Real-world uplift
   is likely **higher** than the 0–11% measured here.
5. **No cost asymmetry.** Every policy pays 1 unit per expansion. Tree
   search methods with per-node LLM calls would look far worse.
6. **Oracle is greedy on true yields** — a strong reference line, not a
   provable optimum.
7. **Single parameterisation** (K=12). Sensitivity to K and budget is not
   yet tested.

---

## Files

| File | Purpose |
|---|---|
| `environment.py` | Depleting multi-branch search env + 5 task regimes |
| `policies.py` | 6 control policies + oracle reference |
| `experiment.py` | Paired-trial runner, bootstrap stats, verdict |
| `results.json` | Full numeric output |
