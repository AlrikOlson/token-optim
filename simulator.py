"""Synthetic workload simulator for token-demand traces.

Generates per-user LATENT demand (what a user would consume if unconstrained)
per period, allocator-independent, so every benchmarked algorithm in Phase 3
sees identical demand. Multiplicative model per user i, period t:

    d_i(t) = base_i * persist_i(t) * burst_i(t) * ramp_i(t)

  base_i      ~ Lognormal(0, sigma): cross-sectional heterogeneity. Default
                sigma=1.6 puts ~75-80% of demand in the top 20% of users,
                matching the qualitative power-user concentration documented in
                enterprise AI usage reports (no exact public distribution
                exists; sigma is swept in Phase 3).
  persist_i   log-AR(1), coefficient rho: heavy weeks follow heavy weeks.
  burst_i     with prob burst_prob, multiply by U(burst_lo, burst_hi).
  ramp_i      for a ramp_frac subset, a logistic climb from ramp_floor to 1 —
              the light-user-turned-heavy case (DAFB saturation probing's
              target scenario).

Traces are rescaled so the mean per-period total demand equals
demand_ratio * budget, which is what makes scenarios comparable: demand_ratio
< 1 means slack exists; > 1 means structural contention.

Stdlib only; one random.Random(seed) per trace for exact reproducibility.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    """Parameters for one workload scenario."""

    name: str
    n_users: int = 50
    n_periods: int = 52
    demand_ratio: float = 0.9   # mean total demand / budget
    sigma: float = 1.6          # lognormal cross-sectional spread
    rho: float = 0.8            # log-AR(1) persistence
    shock_sd: float = 0.4       # stationary sd of the log persistence process
    burst_prob: float = 0.05
    burst_lo: float = 2.0
    burst_hi: float = 5.0
    ramp_frac: float = 0.0      # fraction of users on an adoption ramp
    ramp_floor: float = 0.02    # ramp users start at this multiplier


SCENARIOS: dict[str, Scenario] = {
    # Healthy org: aggregate demand fits inside the budget; slack exists.
    "stable": Scenario(name="stable", demand_ratio=0.9),
    # 30% of users adopt mid-trace and become heavy; ends contended.
    "adoption_ramp": Scenario(name="adoption_ramp", demand_ratio=1.1,
                              ramp_frac=0.3),
    # Everyone is heavy and the budget is structurally short.
    "all_heavy_crunch": Scenario(name="all_heavy_crunch", demand_ratio=1.8,
                                 sigma=0.8),
    # Deadline-driven org: frequent multi-x spikes.
    "bursty": Scenario(name="bursty", demand_ratio=1.0, burst_prob=0.15),
}


@dataclass
class DemandTrace:
    """A generated demand trace: demand[t][user_id] in tokens."""

    scenario: Scenario
    budget: float
    seed: int
    users: list[str]
    ramp_users: list[str]
    demand: list[dict[str, float]]

    def user_series(self, user_id: str) -> list[float]:
        return [period[user_id] for period in self.demand]

    def period_total(self, t: int) -> float:
        return sum(self.demand[t].values())


def simulate(scenario: Scenario, budget: float, seed: int) -> DemandTrace:
    """Generate one reproducible demand trace for a scenario."""
    if budget <= 0:
        raise ValueError("budget must be positive")
    rng = random.Random(seed)
    n, periods = scenario.n_users, scenario.n_periods
    users = [f"u{i:03d}" for i in range(n)]

    base = {u: rng.lognormvariate(0.0, scenario.sigma) for u in users}

    n_ramp = round(scenario.ramp_frac * n)
    ramp_users = sorted(rng.sample(users, n_ramp)) if n_ramp else []
    ramp_set = set(ramp_users)
    # Logistic midpoint mid-trace; transition spans roughly a third of it.
    t0 = periods / 2.0
    k = 12.0 / max(periods, 1)

    # Stationary log-AR(1): innovations scaled so the marginal sd stays
    # shock_sd regardless of rho.
    innov_sd = scenario.shock_sd * math.sqrt(1.0 - scenario.rho ** 2)
    log_persist = {u: rng.gauss(0.0, scenario.shock_sd) for u in users}

    raw: list[dict[str, float]] = []
    for t in range(periods):
        period: dict[str, float] = {}
        for u in users:
            if t > 0:
                log_persist[u] = (scenario.rho * log_persist[u]
                                  + rng.gauss(0.0, innov_sd))
            d = base[u] * math.exp(log_persist[u])
            if rng.random() < scenario.burst_prob:
                d *= rng.uniform(scenario.burst_lo, scenario.burst_hi)
            if u in ramp_set:
                ramp = (scenario.ramp_floor
                        + (1.0 - scenario.ramp_floor)
                        / (1.0 + math.exp(-k * (t - t0))))
                d *= ramp
            period[u] = d
        raw.append(period)

    # Rescale so mean per-period total == demand_ratio * budget.
    mean_total = sum(sum(p.values()) for p in raw) / periods
    scale = scenario.demand_ratio * budget / mean_total
    demand = [{u: d * scale for u, d in p.items()} for p in raw]

    return DemandTrace(scenario=scenario, budget=budget, seed=seed,
                       users=users, ramp_users=ramp_users, demand=demand)


def top_share(values: list[float], frac: float = 0.2) -> float:
    """Share of the total held by the top `frac` of values (concentration)."""
    if not values:
        raise ValueError("values must be non-empty")
    total = sum(values)
    if total <= 0:
        raise ValueError("total must be positive")
    k = max(1, round(frac * len(values)))
    return sum(sorted(values, reverse=True)[:k]) / total


def gini(values: list[float]) -> float:
    """Gini coefficient of a non-negative sample (0 equal .. ~1 concentrated)."""
    if not values:
        raise ValueError("values must be non-empty")
    s = sorted(values)
    n = len(s)
    total = sum(s)
    if total <= 0:
        raise ValueError("total must be positive")
    cum = 0.0
    weighted = 0.0
    for i, v in enumerate(s, start=1):
        cum += v
        weighted += cum
    # Gini via Lorenz trapezoids: 1 - 2 * area under Lorenz curve.
    return 1.0 - (2.0 * weighted - total) / (n * total)
