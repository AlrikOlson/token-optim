"""Calibration machinery: fit simulator parameters from a real usage ledger
and re-run the core benchmark on the fitted scenario.

Estimators mirror the simulator's generative model component-by-component:

  sigma        stdev of log per-user MEAN cost across users (time-averaging
               first suppresses AR/burst noise that would inflate the
               cross-sectional spread)
  rho          pooled lag-1 autocorrelation of per-user log-cost deviations
               from the user mean (needs >= 3 periods)
  burst_prob   fraction of observations exceeding burst_lo x user median
  demand_ratio mean per-period total / budget — a LOWER bound: observed
               spend is censored by whatever policy was in force.

Short panels make rho/burst noisy; insufficient history produces defaults
plus explicit warnings, never silently confident numbers.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

from benchmark import mean_ci, run_trace
from ledger import Ledger
from simulator import Scenario, simulate

CAL_ALGOS = ("dafb_v2", "max_min", "equal_split")


@dataclass
class FittedParams:
    sigma: float
    rho: float
    burst_prob: float
    demand_ratio: float
    n_users: int
    n_periods: int
    warnings: list[str]

    def to_scenario(self, name: str = "calibrated") -> Scenario:
        return Scenario(name=name, n_users=max(2, self.n_users),
                        n_periods=max(12, self.n_periods),
                        demand_ratio=self.demand_ratio, sigma=self.sigma,
                        rho=self.rho, burst_prob=self.burst_prob)


def fit_parameters(ledger: Ledger, budget: float,
                   burst_lo: float = 2.0) -> FittedParams:
    by_period = ledger.usage_by_period()
    periods = sorted(by_period)
    users = ledger.users()
    warnings = []
    if len(users) < 2 or not periods:
        raise ValueError("need >= 2 users and >= 1 period to fit")

    # Per-user series over all periods (0.0 where absent).
    series = {u: [by_period[p].get(u, 0.0) for p in periods] for u in users}
    means = {u: statistics.fmean(s) for u, s in series.items()}
    active = {u: m for u, m in means.items() if m > 0}
    if len(active) < 2:
        raise ValueError("need >= 2 users with non-zero usage")

    sigma = statistics.stdev(math.log(m) for m in active.values())

    # Pooled lag-1 autocorrelation of log deviations from user means.
    # Burst observations (> burst_lo x median) are EXCLUDED: bursts are
    # uncorrelated multiplicative spikes that attenuate rho toward 0 if
    # left in (caught by the parameter-recovery test).
    rho = 0.8
    if len(periods) >= 3:
        xs, ys = [], []
        for u in active:
            med = statistics.median(series[u])
            logs = [math.log(v) if (v > 0 and v <= burst_lo * med) else None
                    for v in series[u]]
            present = [v for v in logs if v is not None]
            if len(present) < 2:
                continue
            center = statistics.fmean(present)
            for a, b in zip(logs[:-1], logs[1:]):  # adjacent non-burst pairs
                if a is not None and b is not None:
                    xs.append(a - center)
                    ys.append(b - center)
        if len(xs) >= 4 and statistics.pstdev(xs) > 0 and statistics.pstdev(ys) > 0:
            mx, my = statistics.fmean(xs), statistics.fmean(ys)
            cov = statistics.fmean([(a - mx) * (b - my) for a, b in zip(xs, ys)])
            rho = max(0.0, min(0.99,
                               cov / (statistics.pstdev(xs) * statistics.pstdev(ys))))
        else:
            warnings.append("too little variation to estimate rho; using 0.8")
    else:
        warnings.append("fewer than 3 periods; rho defaulted to 0.8")

    # Burst frequency: observations above burst_lo x the user's median.
    n_obs = burst_hits = 0
    for u in active:
        med = statistics.median(series[u])
        if med <= 0:
            continue
        for v in series[u]:
            n_obs += 1
            if v > burst_lo * med:
                burst_hits += 1
    burst_prob = burst_hits / n_obs if n_obs else 0.05
    if len(periods) < 6:
        warnings.append("fewer than 6 periods; burst_prob is coarse")

    mean_total = statistics.fmean(sum(by_period[p].values()) for p in periods)
    demand_ratio = mean_total / budget
    warnings.append("demand_ratio is a LOWER bound: observed spend is "
                    "censored by the policy in force when it was recorded")

    return FittedParams(sigma=sigma, rho=rho, burst_prob=burst_prob,
                        demand_ratio=demand_ratio, n_users=len(users),
                        n_periods=len(periods), warnings=warnings)


def calibrated_benchmark(params: FittedParams, budget: float,
                         seeds: int = 30) -> list[str]:
    """Heavy-user unmet demand on the fitted scenario, mean ± 95% CI."""
    sc = params.to_scenario()
    lines = [f"calibrated scenario: sigma={sc.sigma:.2f} rho={sc.rho:.2f} "
             f"burst={sc.burst_prob:.3f} demand_ratio={sc.demand_ratio:.2f} "
             f"({sc.n_users} users, {sc.n_periods} periods, {seeds} seeds)",
             "heavy-user unmet demand:"]
    for algo in CAL_ALGOS:
        vals = [run_trace(algo, simulate(sc, budget, s)).heavy_unmet
                for s in range(seeds)]
        m, half = mean_ci(vals)
        lines.append(f"  {algo:12s} {100 * m:5.1f} ± {100 * half:.1f} %")
    for w in params.warnings:
        lines.append(f"  WARNING: {w}")
    return lines
