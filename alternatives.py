"""Phase 5 experiments: the draw-cap dial and the team-pooling question.

1. Cap-multiplier sweep: dafb_v2 under draw_cap:<m> for m in {1,2,4,8,inf},
   measuring BOTH honest heavy-user unmet demand and 4x-burner collateral —
   the efficiency-vs-vandalism-immunity dial an org actually sets.

2. Team-pooling mini-simulation: the same 50-user population run as one
   org-wide v2 pool vs five independent 10-user v2 pools with B/5 each —
   quantifies what hierarchical pooling costs (or buys).

Run `python alternatives.py` to print both tables.
"""

from __future__ import annotations

from benchmark import fmt_pct, mean_ci, paired_diff, run_trace
from incentives import median_user, run_strategic
from simulator import SCENARIOS, simulate

CAP_MULTS = (1.0, 2.0, 4.0, 8.0, None)  # None = frictionless (uncapped)
SWEEP_SCENARIOS = ("stable", "bursty")
SEEDS = 30
BUDGET = 1_000_000.0


def _friction(mult: float | None) -> str:
    if mult is None:
        return "frictionless"
    return f"draw_cap:{mult:g}"


def cap_sweep_table(seeds: int = SEEDS, budget: float = BUDGET) -> list[str]:
    lines = ["## Draw-cap multiplier sweep (dafb_v2)",
             "",
             "The org's dial: cap = m × equal share per user per period. "
             "'honest heavy-unmet' from all-honest runs; 'collateral' = Δ "
             "honest-heavy unmet with one 4x burner (paired, pp).",
             ""]
    for sname in SWEEP_SCENARIOS:
        sc = SCENARIOS[sname]
        traces = [simulate(sc, budget, s) for s in range(seeds)]
        lines.append(f"### {sname}")
        lines.append("")
        lines.append("| cap | honest heavy-unmet % | burner collateral pp | burn % |")
        lines.append("|---|---|---|---|")
        for mult in CAP_MULTS:
            fr = _friction(mult)
            honest_unmet = [run_trace("dafb_v2", tr, fr).heavy_unmet
                            for tr in traces]
            honest = [run_strategic("dafb_v2", tr, None, 1.0, fr)
                      for tr in traces]
            strat = [run_strategic("dafb_v2", tr, median_user(tr), 4.0, fr)
                     for tr in traces]
            c, ch, cs = paired_diff([s.honest_heavy_unmet for s in strat],
                                    [h.honest_heavy_unmet for h in honest])
            b, bh = mean_ci([s.burn_frac for s in strat])
            label = "uncapped" if mult is None else f"{mult:g}x"
            lines.append(f"| {label} | {fmt_pct(*mean_ci(honest_unmet))} | "
                         f"{100 * c:+.2f} ± {100 * ch:.2f}{'*' if cs else ''} | "
                         f"{fmt_pct(b, bh)} |")
        lines.append("")
    return lines


def team_pooling_table(seeds: int = SEEDS, budget: float = BUDGET,
                       n_pools: int = 5) -> list[str]:
    """One org-wide v2 pool vs n_pools independent v2 pools of equal size and
    equal budget share, on the same population (users partitioned by index)."""
    lines = ["## Team pooling vs one org pool (dafb_v2)",
             "",
             f"Same 50-user population: one pool with B vs {n_pools} "
             f"independent pools of 10 users with B/{n_pools} each. "
             "Heavy-user unmet demand %, paired diff (positive = pooling "
             "hierarchy is worse).",
             ""]
    lines.append("| scenario | one pool | team pools | teams − one (paired) |")
    lines.append("|---|---|---|---|")
    for sname in SWEEP_SCENARIOS + ("adoption_ramp",):
        sc = SCENARIOS[sname]
        single, teams = [], []
        for seed in range(seeds):
            trace = simulate(sc, budget, seed)
            single.append(run_trace("dafb_v2", trace).heavy_unmet)
            # Partition users into contiguous teams; rebuild sub-traces.
            n = len(trace.users)
            size = n // n_pools
            h_demand = h_served = 0.0
            totals = {u: sum(trace.user_series(u)) for u in trace.users}
            k = max(1, round(0.2 * n))
            heavy = set(sorted(trace.users, key=lambda u: -totals[u])[:k])
            for p in range(n_pools):
                members = trace.users[p * size:(p + 1) * size]
                sub = _SubTrace(trace, members, budget / n_pools)
                served = _served_per_user("dafb_v2", sub)
                for u in members:
                    if u in heavy:
                        h_demand += sum(trace.user_series(u))
                        h_served += served[u]
            teams.append((h_demand - h_served) / h_demand)
        m, half, sig = paired_diff(teams, single)
        lines.append(f"| {sname} | {fmt_pct(*mean_ci(single))} | "
                     f"{fmt_pct(*mean_ci(teams))} | "
                     f"{100 * m:+.2f} ± {100 * half:.2f} pp{'*' if sig else ''} |")
    lines.append("")
    return lines


class _SubTrace:
    """A view of a trace restricted to a subset of users with its own budget."""

    def __init__(self, trace, members: list[str], budget: float):
        self.users = members
        self.budget = budget
        self.seed = trace.seed
        self.demand = [{u: period[u] for u in members}
                       for period in trace.demand]

    def user_series(self, user_id: str) -> list[float]:
        return [period[user_id] for period in self.demand]


def _served_per_user(algo_name: str, trace) -> dict[str, float]:
    """Like benchmark.run_trace but returns per-user served true demand."""
    from benchmark import ALGORITHMS, pool_draws

    users = trace.users
    algo = ALGORITHMS[algo_name](trace.budget, users)
    served = {u: 0.0 for u in users}
    for t in range(len(trace.demand)):
        quotas, buffer = algo.allocate()
        d = trace.demand[t]
        excess = [max(0.0, d[u] - quotas[u]) for u in users]
        draws = pool_draws(algo, users, excess, buffer, "frictionless",
                           trace.budget, trace.seed, t)
        usage = {u: min(d[u], quotas[u] + dr) for u, dr in zip(users, draws)}
        for u in users:
            served[u] += usage[u]
        algo.observe(usage)
    return served


if __name__ == "__main__":
    print("\n".join(cap_sweep_table()))
    print("\n".join(team_pooling_table()))
