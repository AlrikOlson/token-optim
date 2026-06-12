"""Empirical benchmark: DAFB vs baseline allocation rules.

Every algorithm spends the same flat budget B on identical latent-demand
traces (paired by seed). Realized usage is derived through the censoring
adapter: u_i(t) = min(d_i(t), q_i(t) + buffer_draw_i(t)) — algorithms only
ever observe realized usage, never latent demand (see think:6).

Algorithms:
  equal_split         q_i = B/n (the default flat policy)
  usage_proportional  q_i proportional to EWMA of realized usage
  static_tiers        4-period observation, then a permanent 3x 'heavy' tier
                      for the top 20% (models manual org tiering + staleness)
  max_min             equal-weight water-filling on plain EWMA forecasts —
                      ablation: DAFB minus floors, earned weights and probing
  dafb                the Phase 1 allocator (floors + earned weights + probe)

Run `python benchmark.py` to regenerate RESULTS.md (~seconds, stdlib only).
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass

from allocator import DAFBAllocator, DAFBv2Allocator, water_fill
from simulator import SCENARIOS, Scenario, simulate

BUDGET = 1_000_000.0
SEEDS = 30
HEAVY_FRAC = 0.2
ALPHA = 0.3  # EWMA smoothing shared by usage-based baselines

# Two-sided 95% t critical values; normal approx beyond the table.
_T95 = {9: 2.262, 19: 2.093, 29: 2.045, 49: 2.010, 99: 1.984}


def t95(df: int) -> float:
    for k in sorted(_T95):
        if df <= k:
            return _T95[k]
    return 1.96


# ------------------------------------------------------------- algorithms


class EqualSplit:
    """q_i = B/n every period."""

    has_buffer = False

    def __init__(self, budget: float, users: list[str]):
        self.quota = budget / len(users)
        self.users = users

    def allocate(self) -> tuple[dict[str, float], float]:
        return {u: self.quota for u in self.users}, 0.0

    def observe(self, usage: dict[str, float]) -> None:
        pass


class UsageProportional:
    """q_i proportional to EWMA of realized usage (rich-get-richer)."""

    has_buffer = False

    def __init__(self, budget: float, users: list[str]):
        self.budget = budget
        self.users = users
        self.mean: dict[str, float] = {}

    def allocate(self) -> tuple[dict[str, float], float]:
        if not self.mean:
            share = self.budget / len(self.users)
            return {u: share for u in self.users}, 0.0
        total = sum(self.mean.values())
        if total <= 0:
            share = self.budget / len(self.users)
            return {u: share for u in self.users}, 0.0
        return {u: self.budget * self.mean[u] / total for u in self.users}, 0.0

    def observe(self, usage: dict[str, float]) -> None:
        for u in self.users:
            x = usage.get(u, 0.0)
            self.mean[u] = (ALPHA * x + (1 - ALPHA) * self.mean[u]
                            if u in self.mean else x)


class StaticTiers:
    """Observe 4 periods on equal split, then permanently tier: top 20% by
    cumulative usage get 3x weight. Models real-org manual tiering, including
    the staleness that comes from never re-tiering."""

    has_buffer = False
    OBSERVE_PERIODS = 4
    HEAVY_WEIGHT = 3.0

    def __init__(self, budget: float, users: list[str]):
        self.budget = budget
        self.users = users
        self.cum: dict[str, float] = {u: 0.0 for u in users}
        self.periods_seen = 0
        self.weights: dict[str, float] | None = None

    def allocate(self) -> tuple[dict[str, float], float]:
        if self.weights is None:
            share = self.budget / len(self.users)
            return {u: share for u in self.users}, 0.0
        total = sum(self.weights.values())
        return {u: self.budget * self.weights[u] / total
                for u in self.users}, 0.0

    def observe(self, usage: dict[str, float]) -> None:
        for u in self.users:
            self.cum[u] += usage.get(u, 0.0)
        self.periods_seen += 1
        if self.weights is None and self.periods_seen >= self.OBSERVE_PERIODS:
            k = max(1, round(HEAVY_FRAC * len(self.users)))
            heavy = set(sorted(self.users, key=lambda u: -self.cum[u])[:k])
            self.weights = {u: self.HEAVY_WEIGHT if u in heavy else 1.0
                            for u in self.users}


class MaxMin:
    """Equal-weight water-filling on plain EWMA forecasts. Ablation of DAFB:
    no entitlement floors, no earned weights, no saturation probing. Surplus
    becomes a buffer (same draw discipline as DAFB) so the comparison
    isolates the forecasting/weighting differences, not the buffer."""

    has_buffer = True

    def __init__(self, budget: float, users: list[str]):
        self.budget = budget
        self.users = users
        self.mean: dict[str, float] = {}

    def allocate(self) -> tuple[dict[str, float], float]:
        n = len(self.users)
        forecasts = [self.mean.get(u, self.budget / n) for u in self.users]
        grants = water_fill(forecasts, [1.0] * n, self.budget)
        quotas = dict(zip(self.users, grants))
        return quotas, self.budget - sum(grants)

    def observe(self, usage: dict[str, float]) -> None:
        for u in self.users:
            x = usage.get(u, 0.0)
            self.mean[u] = (ALPHA * x + (1 - ALPHA) * self.mean[u]
                            if u in self.mean else x)


class DAFB:
    """Adapter around the Phase 1 DAFBAllocator."""

    has_buffer = True

    def __init__(self, budget: float, users: list[str], **kw):
        self.inner = DAFBAllocator(budget=budget, **kw)
        for u in users:
            self.inner.add_user(u)
        self.last_alloc = None

    def allocate(self) -> tuple[dict[str, float], float]:
        self.last_alloc = self.inner.allocate()
        return dict(self.last_alloc.quotas), self.last_alloc.buffer

    def observe(self, usage: dict[str, float]) -> None:
        self.inner.observe(usage, self.last_alloc)


class DAFBv2:
    """Adapter around the buffer-first DAFBv2Allocator. Exposes draw_weights
    so the serving layer applies earned priority to pool draws."""

    has_buffer = True

    def __init__(self, budget: float, users: list[str], **kw):
        self.inner = DAFBv2Allocator(budget=budget, **kw)
        for u in users:
            self.inner.add_user(u)
        self.last_alloc = None

    def allocate(self) -> tuple[dict[str, float], float]:
        self.last_alloc = self.inner.allocate()
        return dict(self.last_alloc.quotas), self.last_alloc.buffer

    def draw_weights(self) -> dict[str, float]:
        return self.inner.draw_weights()

    def observe(self, usage: dict[str, float]) -> None:
        self.inner.observe(usage, self.last_alloc)


ALGORITHMS = {
    "equal_split": EqualSplit,
    "usage_proportional": UsageProportional,
    "static_tiers": StaticTiers,
    "max_min": MaxMin,
    "dafb": DAFB,
    "dafb_v2": DAFBv2,
}

BUFFER_ALGOS = ("max_min", "dafb", "dafb_v2")
FRICTIONS = ("frictionless", "fcfs", "draw_cap")


def pool_draws(algo, users: list[str], excess: list[float], pool: float,
               friction: str, budget: float, seed: int, t: int) -> list[float]:
    """Distribute the liquid pool against realized excess demand under a
    draw discipline. frictionless = (weighted) water-fill; fcfs = seeded
    arrival race, each arrival grabs its full excess; draw_cap = per-user
    draw capped at one equal share, then weighted water-fill."""
    n = len(users)
    if pool <= 0 or not any(e > 0 for e in excess):
        return [0.0] * n
    if friction == "fcfs":
        rng = random.Random(seed * 1_000_003 + t)
        order = list(range(n))
        rng.shuffle(order)
        draws = [0.0] * n
        remaining = pool
        for i in order:
            g = min(excess[i], remaining)
            draws[i] = g
            remaining -= g
            if remaining <= 0:
                break
        return draws
    if hasattr(algo, "draw_weights"):
        wd = algo.draw_weights()
        weights = [wd[u] for u in users]
    else:
        weights = [1.0] * n
    if friction == "draw_cap" or friction.startswith("draw_cap:"):
        # 'draw_cap' = 1x equal share; 'draw_cap:<m>' = m x equal share.
        mult = float(friction.split(":", 1)[1]) if ":" in friction else 1.0
        cap = mult * budget / n
        excess = [min(e, cap) for e in excess]
    elif friction != "frictionless":
        raise ValueError(f"unknown friction: {friction}")
    return water_fill(excess, weights, pool)


# ------------------------------------------------------------ trace runner


@dataclass
class RunMetrics:
    heavy_unmet: float
    overall_unmet: float
    utilization: float
    waste: float
    jain: float
    volatility: float
    budget_ok: bool


def run_trace(algo_name: str, trace, friction: str = "frictionless") -> RunMetrics:
    """Run one algorithm over one demand trace through the censoring adapter."""
    users = trace.users
    algo = ALGORITHMS[algo_name](trace.budget, users)
    n = len(users)
    periods = len(trace.demand)

    # Heavy users = top 20% by TOTAL LATENT demand (ground truth, identical
    # across algorithms for a given trace).
    totals = {u: sum(trace.user_series(u)) for u in users}
    k = max(1, round(HEAVY_FRAC * n))
    heavy = set(sorted(users, key=lambda u: -totals[u])[:k])

    demand_sum = used_sum = 0.0
    h_demand = h_used = 0.0
    waste_sum = 0.0
    user_used = {u: 0.0 for u in users}
    user_demand = {u: 0.0 for u in users}
    prev_q: dict[str, float] | None = None
    vol_acc = 0.0
    budget_ok = True

    for t in range(periods):
        quotas, buffer = algo.allocate()
        if sum(quotas.values()) + buffer > trace.budget * (1 + 1e-9):
            budget_ok = False
        d = trace.demand[t]

        # Censoring adapter: distribute the pool against realized excess
        # demand under the chosen friction discipline, then realized usage.
        excess = [max(0.0, d[u] - quotas[u]) for u in users]
        draws = pool_draws(algo, users, excess, buffer, friction,
                           trace.budget, trace.seed, t)
        usage = {u: min(d[u], quotas[u] + dr)
                 for u, dr in zip(users, draws)}

        for u in users:
            demand_sum += d[u]
            used_sum += usage[u]
            user_used[u] += usage[u]
            user_demand[u] += d[u]
            waste_sum += max(0.0, quotas[u] - usage[u])
            if u in heavy:
                h_demand += d[u]
                h_used += usage[u]
        if prev_q is not None:
            vol_acc += sum(abs(quotas[u] - prev_q[u]) for u in users) / n
        prev_q = quotas
        algo.observe(usage)

    sat = [user_used[u] / user_demand[u] for u in users if user_demand[u] > 0]
    jain = (sum(sat) ** 2) / (len(sat) * sum(s * s for s in sat))
    return RunMetrics(
        heavy_unmet=(h_demand - h_used) / h_demand,
        overall_unmet=(demand_sum - used_sum) / demand_sum,
        utilization=used_sum / (trace.budget * periods),
        waste=waste_sum / (trace.budget * periods),
        jain=jain,
        volatility=(vol_acc / max(1, periods - 1)) / (trace.budget / n),
        budget_ok=budget_ok,
    )


# -------------------------------------------------------------- statistics


def mean_ci(values: list[float]) -> tuple[float, float]:
    """Mean and 95% CI half-width (t-based)."""
    m = statistics.fmean(values)
    if len(values) < 2:
        return m, 0.0
    half = t95(len(values) - 1) * statistics.stdev(values) / len(values) ** 0.5
    return m, half


def paired_diff(a: list[float], b: list[float]) -> tuple[float, float, bool]:
    """Mean of (a-b), CI half-width, and significance (CI excludes 0)."""
    diffs = [x - y for x, y in zip(a, b)]
    m, half = mean_ci(diffs)
    return m, half, abs(m) > half > 0 or (half == 0 and m != 0)


# ------------------------------------------------------------------- main


def run_benchmark(seeds: int = SEEDS, budget: float = BUDGET,
                  scenarios: dict[str, Scenario] | None = None,
                  ) -> dict[str, dict[str, list[RunMetrics]]]:
    """results[scenario][algo] = list of RunMetrics, paired by seed order."""
    scenarios = scenarios or SCENARIOS
    results: dict[str, dict[str, list[RunMetrics]]] = {}
    for sname, sc in scenarios.items():
        results[sname] = {a: [] for a in ALGORITHMS}
        for seed in range(seeds):
            trace = simulate(sc, budget, seed)
            for a in ALGORITHMS:
                results[sname][a].append(run_trace(a, trace))
    return results


def fmt_pct(m: float, half: float) -> str:
    return f"{100 * m:.1f} ± {100 * half:.1f}"


def friction_section(seeds: int = SEEDS, budget: float = BUDGET) -> list[str]:
    """Heavy-user unmet demand for buffer-bearing algorithms under each draw
    discipline, plus paired v2-vs-max_min differences."""
    lines = ["## Draw-friction sensitivity (buffer-bearing algorithms)",
             "",
             "Heavy-user unmet demand %, mean ± 95% CI. FCFS = seeded arrival "
             "race; draw_cap = per-user pool draw capped at one equal share.",
             ""]
    for sname, sc in SCENARIOS.items():
        lines.append(f"### {sname}")
        lines.append("")
        lines.append("| friction | " + " | ".join(BUFFER_ALGOS) +
                     " | v2 − max_min (paired) |")
        lines.append("|" + "---|" * (len(BUFFER_ALGOS) + 2))
        for friction in FRICTIONS:
            vals = {a: [] for a in BUFFER_ALGOS}
            for seed in range(seeds):
                trace = simulate(sc, budget, seed)
                for a in BUFFER_ALGOS:
                    vals[a].append(run_trace(a, trace, friction).heavy_unmet)
            cells = [friction]
            for a in BUFFER_ALGOS:
                cells.append(fmt_pct(*mean_ci(vals[a])))
            m, half, sig = paired_diff(vals["dafb_v2"], vals["max_min"])
            cells.append(f"{100 * m:+.2f} ± {100 * half:.2f} pp"
                         + ("*" if sig else ""))
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    return lines


def write_results(results, sweep_rows: list[str], path: str = "RESULTS.md",
                  extra_sections: list[str] | None = None) -> None:
    lines = [
        "# Empirical results — DAFB vs baselines",
        "",
        f"{SEEDS} seeds per scenario, {next(iter(SCENARIOS.values())).n_users} users, "
        f"{next(iter(SCENARIOS.values())).n_periods} periods, flat budget B = {BUDGET:.0f} "
        "tokens/period. All algorithms see identical latent-demand traces per seed; "
        "realized usage = min(demand, quota + buffer draw). Values are mean ± 95% CI "
        "across seeds, in percent.",
        "",
    ]
    metric_fields = [
        ("heavy_unmet", "Heavy-user unmet demand % (lower better)"),
        ("overall_unmet", "Overall unmet demand % (lower better)"),
        ("utilization", "Budget utilization % (higher better)"),
        ("waste", "Allocated-but-unused % of B (lower better)"),
        ("jain", "Jain fairness of satisfaction % (higher better)"),
    ]
    for sname, per_algo in results.items():
        lines.append(f"## Scenario: {sname}")
        lines.append("")
        header = "| Metric | " + " | ".join(ALGORITHMS) + " |"
        lines.append(header)
        lines.append("|" + "---|" * (len(ALGORITHMS) + 1))
        for field, label in metric_fields:
            row = [label]
            for a in ALGORITHMS:
                vals = [getattr(r, field) for r in per_algo[a]]
                row.append(fmt_pct(*mean_ci(vals)))
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
        lines.append("Paired DAFB − baseline difference in heavy-user unmet demand "
                     "(negative = DAFB better; * = 95% CI excludes 0):")
        lines.append("")
        dafb_vals = [r.heavy_unmet for r in per_algo["dafb"]]
        for a in ALGORITHMS:
            if a == "dafb":
                continue
            base_vals = [r.heavy_unmet for r in per_algo[a]]
            m, half, sig = paired_diff(dafb_vals, base_vals)
            mark = "*" if sig else ""
            lines.append(f"- vs {a}: {100 * m:+.2f} ± {100 * half:.2f} pp{mark}")
        lines.append("")
        ok = all(r.budget_ok for a in ALGORITHMS for r in per_algo[a])
        lines.append(f"Budget conservation across all runs: {'PASS' if ok else 'FAIL'}")
        lines.append("")
    lines.append("## σ-sweep (tail-heaviness sensitivity, stable scenario)")
    lines.append("")
    lines.extend(sweep_rows)
    lines.append("")
    lines.append(ANALYSIS)
    for section in extra_sections or []:
        lines.append(section)
    with open(path, "w") as f:
        f.write("\n".join(lines))


def sigma_sweep(seeds: int = SEEDS, budget: float = BUDGET) -> list[str]:
    rows = ["| sigma | dafb heavy-unmet % | equal_split | usage_proportional | max_min |",
            "|---|---|---|---|---|"]
    for sigma in (1.2, 1.6, 2.0):
        sc = Scenario(name=f"stable_s{sigma}", sigma=sigma, demand_ratio=0.9)
        cells = [f"| {sigma}"]
        per_algo = {}
        for a in ("dafb", "equal_split", "usage_proportional", "max_min"):
            vals = []
            for seed in range(seeds):
                trace = simulate(sc, budget, seed)
                vals.append(run_trace(a, trace).heavy_unmet)
            per_algo[a] = vals
            cells.append(fmt_pct(*mean_ci(vals)))
        rows.append(" | ".join(cells) + " |")
    return rows


ANALYSIS_V2 = """\
## DAFB v2 analysis (buffer-first redesign)

v2 = demand-capped floors at half the equal share + maximal liquid pool +
utilization-earned DRAW priority (think:10). Findings:

**Under realistic draw disciplines, v2 is the best algorithm tested.**
Frictionless: v2 beats max_min significantly in stable (−3.8 pp), ramp
(−2.6 pp) and bursty (−6.3 pp) heavy-user unmet demand, with the lowest waste
of any algorithm (2.2–2.5% of B vs max_min's 9–12%), the highest utilization
(86–92%), and tied-best Jain fairness. Under an FCFS race it wins in ALL four
scenarios including crunch (−2.6 pp): its small floors mean even race losers
keep a guarantee, and the race itself is demand-revealing. The earned-weight
mechanism finally pays for itself once relocated to draw priority — the brief's
'experienced heavy users win contention' goal without the pool-shrinkage tax.

**Honest negative findings:**

1. **Structural crunch, frictionless/capped: v2 loses to max_min (+6 pp).**
   When everyone's demand exceeds the budget, weighted draws concentrate
   tokens on high-utilization users and the half-share floors are too small
   to compensate; max_min's full pre-assignment equalizes better. If an org
   expects sustained org-wide contention (demand ≈ 1.8×B), the budget itself
   is the problem — no allocator fixes structural under-provisioning.
2. **The draw_cap collapse is the decisive deployment caveat.** Capping pool
   draws at one equal share per user per period devastates v2 (+30 to +36 pp
   vs max_min) — heavy users simply cannot pull enough through the capped
   pipe, while max_min/v1 already pre-assigned them most of their demand.
   Hypothesis H2 (friction rehabilitates pre-assignment) is CONFIRMED, and
   dramatically: **the right architecture depends on the serving layer.**
   If the gateway can do uncapped (or generously capped) real-time pool
   draws, deploy v2; if overage is tightly rate-limited, deploy forecast
   pre-assignment (max_min-style water-filling).

**Deployment guidance (preliminary, pre-incentive-analysis):** v2 with
frictionless or FCFS-ish pool draws for orgs whose gateway supports real-time
shared-pool metering (LiteLLM/Kong-class proxies can); max_min water-filling
quotas where overage must be pre-approved. Phase 4 must now stress-test v2's
draw-priority weights against strategic token burning, which the draw_cap
result suggests may double as a gaming throttle.
"""

ANALYSIS = """\
## Analysis and honest findings

**DAFB decisively beats deployed practice.** Against equal split it cuts
heavy-user unmet demand by 44-54 pp (significant) in every non-crunch scenario;
against static tiers by 28-35 pp. The slack-recycling premise of the project is
confirmed: a flat budget serves heavy users far better when light users' unused
entitlement is actively redistributed.

**But the central hypothesis is partially FALSIFIED.** The `max_min` ablation —
plain EWMA forecasts, equal weights, no floors, no saturation probing, same
liquid buffer — beats full DAFB on heavy-user unmet demand by 7.7-9.7 pp in
*every* scenario (all significant). Diagnosis: DAFB's bespoke components
(deviation headroom, probe bumps, earned weights) all *inflate pre-assigned
quotas*, which shrinks the liquid buffer; the buffer's pro-rata draw against
*realized* excess demand is demand-revealing (zero forecast error), so every
token moved from the buffer into forecast-based quotas is allocated strictly
worse. Under frictionless mid-period draws, **conservative pre-assignment plus a
large shared pool dominates clever forecasting**. The forecasting machinery
optimized the wrong stage.

**Scope caveats (why this is not yet the final word):**

1. The draw adapter is an idealized frictionless pool (instant, pro-rata,
   no races). Real draw mechanisms have friction — FCFS contention, approval
   latency, rate limits — which is exactly when guaranteed quotas regain value.
   The backlog chunk on buffer draw discipline becomes the decisive experiment.
2. Quotas have *commitment value* not measured here: a user who can see a
   guaranteed allocation can plan work; a pool grants no forward guarantee.
3. Strategic robustness is untested (Phase 4): a pool drawn by claimed excess
   may be more gameable than utilization-earned quotas.
4. `usage_proportional` also beats DAFB in ramp/crunch on heavy-unmet, but
   pays for it with the worst satisfaction-fairness in the ramp scenario
   (Jain 89.2% vs DAFB 98.6%) — it starves precisely the ramping users the
   brief cares about.

**Design implication for DAFB v2:** invert the architecture. Keep a small
guaranteed floor per user (predictability + fairness), push everything else
into the liquid pool, and let demand reveal itself through draws; apply
earned-weight discipline to *draw priority* rather than to pre-assigned quotas.
"""


if __name__ == "__main__":
    from incentives import ANALYSIS_INCENTIVES, gaming_table

    results = run_benchmark()
    sweep = sigma_sweep()
    friction = friction_section()
    incentive_rows = gaming_table()
    write_results(results, sweep,
                  extra_sections=["\n".join(friction), ANALYSIS_V2,
                                  "\n".join(incentive_rows),
                                  ANALYSIS_INCENTIVES])
    print("RESULTS.md written.")
    for sname, per_algo in results.items():
        v2_m, _ = mean_ci([r.heavy_unmet for r in per_algo["dafb_v2"]])
        mm_m, _ = mean_ci([r.heavy_unmet for r in per_algo["max_min"]])
        eq_m, _ = mean_ci([r.heavy_unmet for r in per_algo["equal_split"]])
        print(f"{sname}: heavy-unmet v2 {100 * v2_m:.1f}% vs max_min "
              f"{100 * mm_m:.1f}% vs equal {100 * eq_m:.1f}%")
