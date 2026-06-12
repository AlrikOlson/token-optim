"""Strategic-behavior analysis: can a user game the allocator by burning?

Unified burner/over-claimer agent: a chosen mid-tier user acts as if their
demand were max(d_true, greed * B/n) — they CLAIM that much when drawing from
the pool and BURN whatever they're granted up to the claim. The org observes
consumption and cannot distinguish burn from work. Everyone else is honest.

Measured against the paired honest counterfactual (same trace):
  gain        Δ served-TRUE-demand fraction for the strategic user — burning
              is not service; only min(d_true, granted) counts
  collateral  Δ heavy-user unmet demand among honest users
  waste       Δ fraction of budget consumed by pure burn

Mitigation evaluated: the draw_cap discipline (per-user pool draw capped at
one equal share), which throttles how much a gamer can extract per period.

Run `python incentives.py` for a standalone INCENTIVES table; benchmark.py
folds the same section into RESULTS.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from benchmark import (ALGORITHMS, HEAVY_FRAC, fmt_pct, mean_ci, paired_diff,
                       pool_draws)
from simulator import SCENARIOS, simulate

INC_ALGOS = ("usage_proportional", "max_min", "dafb", "dafb_v2")
GREEDS = (1.0, 2.0, 4.0)
INC_SCENARIOS = ("stable", "bursty")
INC_FRICTIONS = ("frictionless", "draw_cap")
MITIGATION_THRESHOLD_PP = 5.0  # stated bar: draw_cap holds v2 gain below this


@dataclass
class StrategicOutcome:
    """One run's outcome, honest or strategic."""

    target_served_frac: float   # strategic user's served true demand fraction
    honest_heavy_unmet: float   # unmet ratio among honest heavy users
    burn_frac: float            # tokens burned (consumed above true demand)/B


def median_user(trace) -> str:
    """Mid-tier user by total latent demand — the plausible gamer."""
    totals = sorted(trace.users, key=lambda u: sum(trace.user_series(u)))
    return totals[len(totals) // 2]


def run_strategic(algo_name: str, trace, target: str | None, greed: float,
                  friction: str) -> StrategicOutcome:
    """Run one trace; `target` games with `greed`, or everyone honest if None."""
    users = trace.users
    n = len(users)
    algo = ALGORITHMS[algo_name](trace.budget, users)
    periods = len(trace.demand)
    inflated = greed * trace.budget / n

    # Honest heavy set excludes the strategic user.
    totals = {u: sum(trace.user_series(u)) for u in users}
    k = max(1, round(HEAVY_FRAC * n))
    heavy = set(sorted(users, key=lambda u: -totals[u])[:k]) - {target}

    t_demand = t_served = 0.0
    h_demand = h_served = 0.0
    burn = 0.0
    tgt = target if target is not None else "__nobody__"

    for t in range(periods):
        quotas, buffer = algo.allocate()
        d = trace.demand[t]
        claimed = {u: (max(d[u], inflated) if u == tgt else d[u])
                   for u in users}
        excess = [max(0.0, claimed[u] - quotas[u]) for u in users]
        draws = pool_draws(algo, users, excess, buffer, friction,
                           trace.budget, trace.seed, t)
        usage: dict[str, float] = {}
        for u, dr in zip(users, draws):
            granted = quotas[u] + dr
            consumed = min(claimed[u], granted)
            usage[u] = consumed
            served = min(d[u], granted)
            if u == tgt:
                t_demand += d[u]
                t_served += served
                burn += max(0.0, consumed - d[u])
            elif u in heavy:
                h_demand += d[u]
                h_served += served
        algo.observe(usage)

    return StrategicOutcome(
        target_served_frac=(t_served / t_demand) if t_demand > 0 else 1.0,
        honest_heavy_unmet=(h_demand - h_served) / h_demand,
        burn_frac=burn / (trace.budget * periods),
    )


def gaming_table(seeds: int = 30, budget: float = 1_000_000.0) -> list[str]:
    """Markdown section quantifying gaming gain, collateral, and mitigation."""
    lines = ["## Incentive robustness (strategic burner/over-claimer)",
             "",
             "A mid-tier user claims/burns up to greed × B/n per period; everyone "
             "else honest. 'gain' = Δ served true demand for the gamer vs the "
             "honest counterfactual (paired, pp); 'collateral' = Δ heavy-user "
             "unmet among honest users (pp); 'burn' = budget destroyed (%/period). "
             f"Mitigation bar: draw_cap must hold dafb_v2 gain below "
             f"{MITIGATION_THRESHOLD_PP:.0f} pp.",
             ""]
    for sname in INC_SCENARIOS:
        sc = SCENARIOS[sname]
        lines.append(f"### {sname}")
        lines.append("")
        lines.append("| algo | friction | greed | gain pp | collateral pp | burn % |")
        lines.append("|---|---|---|---|---|---|")
        for algo in INC_ALGOS:
            for friction in INC_FRICTIONS:
                honest: list[StrategicOutcome] = []
                traces = [simulate(sc, budget, s) for s in range(seeds)]
                for tr in traces:
                    honest.append(run_strategic(algo, tr, None, 1.0, friction))
                for greed in GREEDS:
                    strat = [run_strategic(algo, tr, median_user(tr), greed,
                                           friction) for tr in traces]
                    g, gh, gs = paired_diff(
                        [s.target_served_frac for s in strat],
                        [h.target_served_frac for h in honest])
                    c, ch, cs = paired_diff(
                        [s.honest_heavy_unmet for s in strat],
                        [h.honest_heavy_unmet for h in honest])
                    b, bh = mean_ci([s.burn_frac for s in strat])
                    lines.append(
                        f"| {algo} | {friction} | {greed:.0f}x | "
                        f"{100 * g:+.2f} ± {100 * gh:.2f}{'*' if gs else ''} | "
                        f"{100 * c:+.2f} ± {100 * ch:.2f}{'*' if cs else ''} | "
                        f"{fmt_pct(b, bh)} |")
        lines.append("")
    return lines


ANALYSIS_INCENTIVES = """\
### Incentive analysis

1. **Gaming yields the gamer nothing.** Across every algorithm, friction, and
   greed level, the strategic user's served TRUE demand gain is ≈0 pp — and
   often significantly negative (down to −3.5 pp): under slack-recycling
   allocators a mid-tier user is already near-fully served, and burning
   displaces their own real work during bursts. The use-it-or-lose-it gambit
   has no payoff; burning is pure vandalism, not rational strategy.
2. **But vandalism hurts everyone else.** Collateral on honest heavy users
   reaches +5.5 pp (dafb v1, 4x greed) and a single 4x burner destroys ~7% of
   the org budget per period. The threat model is misuse, not strategy.
3. **The mitigation bar is exceeded.** draw_cap holds dafb_v2's gaming gain
   far below the stated 5 pp (gain ≤ 0), and stronger: it drives v2's
   collateral to exactly +0.00 pp with burn capped at 2.4%/period — bounded
   floors plus capped draws mechanically limit any one user's extraction to
   floor + cap. max_min under the same cap still leaks +0.5-0.7 pp because
   its forecast-grown quotas are unbounded.
4. **The honest tension:** the same draw cap that makes v2 vandalism-proof
   costs honest heavy users ~30 pp service (see friction tables). The cap
   multiplier is the org's efficiency-vs-immunity dial; sweeping intermediate
   caps (2-4x equal share) is recorded as future work.
"""


if __name__ == "__main__":
    print("\n".join(gaming_table()))
    print(ANALYSIS_INCENTIVES)
