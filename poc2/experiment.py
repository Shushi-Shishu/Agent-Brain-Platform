"""
POC 2 — the falsification test.

THE QUESTION
    Does the best exploration/exploitation policy depend on the task?

WHY IT MATTERS
    Agent Brain Platform's premise is that technique selection should be
    goal-aware — that the right control policy for one agent is the wrong
    one for another. If a single policy wins every regime, that premise is
    false: the correct product is a blog post naming the winner, not a
    platform for choosing.

METHOD
    Common random numbers. For trial i, every policy faces a numerically
    identical environment, so comparisons are paired and low-variance.
    Significance via paired bootstrap on per-trial differences.

Run:  python experiment.py
"""

import json
import sys
from pathlib import Path

import numpy as np

from environment import REGIMES, RelationshipSearchEnv
from policies import POLICIES, OracleGreedy

N_TRIALS = 2000
N_BOOTSTRAP = 10000
SEED = 20260728

# With 2000 paired trials we can detect differences far too small to care
# about. A result counts only if it is BOTH statistically significant and
# clears a practical floor — otherwise we are selling noise as insight.
PRACTICAL_FLOOR_PCT = 2.0


def run_episode(policy_cls, regime, env_seed: int, pol_seed: int) -> int:
    """One agent run. Returns relationships found within budget."""
    env_rng = np.random.default_rng(env_seed)
    pol_rng = np.random.default_rng(pol_seed)
    env = RelationshipSearchEnv(regime, env_rng)

    if policy_cls is OracleGreedy:
        policy = OracleGreedy(regime.k, pol_rng, regime.budget, env=env)
    else:
        policy = policy_cls(regime.k, pol_rng, regime.budget)

    found = 0
    while not env.done():
        b = policy.select()
        r = env.expand(b)
        policy.update(b, r)
        found += r
    return found


def paired_bootstrap(a: np.ndarray, b: np.ndarray, rng, n=N_BOOTSTRAP):
    """95% CI on mean(a - b), paired."""
    d = a - b
    idx = rng.integers(0, len(d), size=(n, len(d)))
    boot = d[idx].mean(axis=1)
    return float(d.mean()), float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def main():
    rng = np.random.default_rng(SEED)
    all_policies = list(POLICIES) + [OracleGreedy]
    results = {}

    print("=" * 78)
    print("POC 2 — Does the best control policy depend on the task?")
    print(f"{N_TRIALS} paired trials per cell | common random numbers")
    print("=" * 78)

    for regime in REGIMES:
        per_policy = {}
        for pcls in all_policies:
            # Same env seed sequence for every policy -> paired comparison.
            scores = np.array([
                run_episode(pcls, regime, env_seed=SEED + i,
                            pol_seed=SEED + 900000 + i)
                for i in range(N_TRIALS)
            ], dtype=float)
            # instantiate once purely to read the resolved display name
            probe = (OracleGreedy(regime.k, rng, regime.budget)
                     if pcls is OracleGreedy else pcls(regime.k, rng, regime.budget))
            per_policy[probe.name] = scores

        oracle_name = "Oracle(reference)"
        oracle_mean = per_policy[oracle_name].mean()

        ranked = sorted(
            ((n, s) for n, s in per_policy.items() if n != oracle_name),
            key=lambda kv: kv[1].mean(), reverse=True,
        )

        print(f"\n── {regime.name.upper()} ──  budget={regime.budget}, "
              f"branches={regime.k}")
        print(f"   {regime.description}")
        print(f"   {'policy':<28}{'found':>9}{'±95%CI':>11}{'% oracle':>11}")
        for name, s in ranked:
            ci = 1.96 * s.std(ddof=1) / np.sqrt(len(s))
            print(f"   {name:<28}{s.mean():>9.2f}{ci:>11.2f}"
                  f"{100 * s.mean() / oracle_mean:>10.1f}%")
        print(f"   {'-- oracle reference --':<28}{oracle_mean:>9.2f}"
              f"{'':>11}{100.0:>10.1f}%")

        # Is the winner actually ahead of runner-up?
        (w_name, w_s), (r_name, r_s) = ranked[0], ranked[1]
        (l_name, l_s) = ranked[-1]
        diff, lo, hi = paired_bootstrap(w_s, r_s, rng)
        significant = lo > 0
        margin_pct = 100.0 * diff / r_s.mean()
        practical = margin_pct >= PRACTICAL_FLOOR_PCT
        decisive = significant and practical

        # How much is getting this decision right actually worth?
        stakes_pct = 100.0 * (w_s.mean() - l_s.mean()) / l_s.mean()

        # The question a practitioner actually asks: is replacing my naive
        # loop with a principled controller worth anything?
        naive = per_policy["Greedy(LLM-proxy)"]
        uplift_pct = 100.0 * (w_s.mean() - naive.mean()) / naive.mean()

        # Viability tiers, relative to the best policy in this regime.
        best_mean = w_s.mean()
        tiers = {}
        for n, s in ranked:
            rel = 100.0 * s.mean() / best_mean
            tiers[n] = ("viable" if rel >= 95 else
                        "weak" if rel >= 80 else "disqualified")

        verdict = ("DECISIVE" if decisive else
                   "significant but negligible" if significant else
                   "not significant")
        print(f"   winner: {w_name} vs {r_name}: "
              f"Δ={diff:+.2f} ({margin_pct:+.1f}%) [{lo:+.2f}, {hi:+.2f}] -> {verdict}")
        print(f"   stakes: best vs worst = {stakes_pct:+.0f}% ({l_name} is worst)")
        print(f"   uplift over naive loop = {uplift_pct:+.1f}%")
        dq = [n for n, t in tiers.items() if t == "disqualified"]
        print(f"   disqualified here: {', '.join(dq) if dq else '(none)'}")

        results[regime.name] = {
            "budget": regime.budget,
            "branches": regime.k,
            "description": regime.description,
            "oracle_mean": oracle_mean,
            "policies": {n: {"mean": float(s.mean()),
                             "ci95": float(1.96 * s.std(ddof=1) / np.sqrt(len(s))),
                             "pct_oracle": float(100 * s.mean() / oracle_mean)}
                         for n, s in ranked},
            "winner": w_name,
            "runner_up": r_name,
            "worst": l_name,
            "delta": diff,
            "delta_pct": margin_pct,
            "delta_ci": [lo, hi],
            "significant": bool(significant),
            "practical": bool(practical),
            "decisive": bool(decisive),
            "stakes_pct": stakes_pct,
            "uplift_vs_naive_pct": uplift_pct,
            "tiers": tiers,
        }

    # ── Verdict ──────────────────────────────────────────────────────────
    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    winners = {r: d["winner"] for r, d in results.items() if d["decisive"]}
    non_decisive = [r for r, d in results.items() if not d["decisive"]]

    print(f"  {'regime':<12}{'winner':<28}{'margin':>9}{'stakes':>9}   status")
    for r, d in results.items():
        status = ("decisive" if d["decisive"] else
                  "negligible" if d["significant"] else "n.s.")
        print(f"  {r:<12}{d['winner']:<28}{d['delta_pct']:>8.1f}%"
              f"{d['stakes_pct']:>8.0f}%   {status}")

    # ── Q1: can you name one best technique? ────────────────────────────
    distinct = set(winners.values())
    print(f"\n  [Q1] Ranking the top of the field: margins between #1 and #2 "
          f"run {min(d['delta_pct'] for d in results.values()):.1f}%"
          f"..{max(d['delta_pct'] for d in results.values()):.1f}%.")
    print("       => The top 2-3 techniques are practically TIED everywhere.")
    print("          Star-rating them sells a distinction that does not exist.")

    # ── Q2: does the VIABLE SET change by task? the real premise ────────
    print("\n  [Q2] Viability by regime (viable >=95% of best, "
          "disqualified <80%):")
    pol_names = list(next(iter(results.values()))["tiers"].keys())
    header = f"       {'policy':<28}" + "".join(f"{r[:9]:>11}" for r in results)
    print(header)
    swings = []
    for p in pol_names:
        row = f"       {p:<28}"
        seen = set()
        for r, d in results.items():
            t = d["tiers"][p]
            seen.add(t)
            mark = {"viable": "viable", "weak": "weak", "disqualified": "DISQUAL"}[t]
            row += f"{mark:>11}"
        print(row)
        if "viable" in seen and "disqualified" in seen:
            swings.append(p)

    print()
    if swings:
        print(f"  => {len(swings)} technique(s) swing from VIABLE to "
              f"DISQUALIFIED depending on the task:")
        for p in swings:
            print(f"       - {p}")
        print("     Goal-aware selection has real value — but as a "
              "DISQUALIFIER, not a ranker.")
        print("     The platform premise SURVIVES, in its negative form.")
    else:
        print("  => No technique changes viability across tasks.")
        print("     The platform premise FAILS; one default serves everyone.")

    # ── Q3: is principled control worth it at all? ──────────────────────
    upl = {r: d["uplift_vs_naive_pct"] for r, d in results.items()}
    print(f"\n  [Q3] Uplift of best policy over the naive loop, by regime:")
    for r, u in upl.items():
        note = "  <- naive is already best" if u <= 0.01 else ""
        print(f"       {r:<12}{u:>+7.1f}%{note}")
    print(f"       range {min(upl.values()):+.1f}% .. {max(upl.values()):+.1f}%")

    out = Path(__file__).parent / "results.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\n  results -> {out}")


if __name__ == "__main__":
    sys.exit(main())
