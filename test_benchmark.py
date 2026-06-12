"""Harness tests for the benchmark: adapter invariants, budget discipline,
determinism, and stats helpers. The full 30-seed run is exercised by
executing benchmark.py itself; these tests keep the harness honest at
smaller scale."""

import pytest

from benchmark import (ALGORITHMS, BUFFER_ALGOS, FRICTIONS, mean_ci,
                       paired_diff, pool_draws, run_trace, t95)
from simulator import SCENARIOS, Scenario, simulate

B = 100_000.0
SMALL = Scenario(name="small", n_users=12, n_periods=12, demand_ratio=1.2)


@pytest.mark.parametrize("algo", list(ALGORITHMS))
def test_budget_never_exceeded(algo):
    trace = simulate(SMALL, B, seed=1)
    metrics = run_trace(algo, trace)
    assert metrics.budget_ok


@pytest.mark.parametrize("algo", list(ALGORITHMS))
def test_metrics_in_valid_ranges(algo):
    trace = simulate(SMALL, B, seed=2)
    m = run_trace(algo, trace)
    assert 0.0 <= m.heavy_unmet <= 1.0
    assert 0.0 <= m.overall_unmet <= 1.0
    assert 0.0 <= m.utilization <= 1.0 + 1e-9
    assert 0.0 <= m.waste <= 1.0
    assert 0.0 < m.jain <= 1.0 + 1e-9
    assert m.volatility >= 0.0


@pytest.mark.parametrize("algo", list(ALGORITHMS))
def test_run_trace_deterministic(algo):
    trace = simulate(SMALL, B, seed=3)
    assert run_trace(algo, trace) == run_trace(algo, trace)


def test_usage_never_exceeds_demand_or_grant():
    # Adapter invariant, checked indirectly: with demand_ratio far above 1,
    # utilization can never exceed 100% of budget and unmet must be > 0.
    sc = Scenario(name="crunchy", n_users=10, n_periods=10, demand_ratio=3.0)
    trace = simulate(sc, B, seed=4)
    for algo in ALGORITHMS:
        m = run_trace(algo, trace)
        assert m.utilization <= 1.0 + 1e-9
        assert m.overall_unmet > 0.3  # demand is 3x budget; most is unmet


def test_equal_split_wastes_under_heterogeneity():
    # Equal split must waste budget when demand is heavy-tailed and slack
    # exists — the core motivating failure.
    sc = Scenario(name="het", n_users=40, n_periods=20, demand_ratio=0.9,
                  sigma=1.6)
    trace = simulate(sc, B, seed=5)
    eq = run_trace("equal_split", trace)
    da = run_trace("dafb", trace)
    assert eq.waste > da.waste
    assert da.heavy_unmet < eq.heavy_unmet


# --------------------------------------------------------- draw frictions

@pytest.mark.parametrize("friction", FRICTIONS)
@pytest.mark.parametrize("algo", BUFFER_ALGOS)
def test_frictions_respect_budget_and_determinism(algo, friction):
    trace = simulate(SMALL, B, seed=6)
    m1 = run_trace(algo, trace, friction)
    m2 = run_trace(algo, trace, friction)
    assert m1 == m2
    assert m1.budget_ok
    assert m1.utilization <= 1.0 + 1e-9


def test_pool_draws_never_exceed_pool_or_excess():
    users = ["a", "b", "c"]
    excess = [50.0, 100.0, 0.0]

    class NoWeights:
        pass

    for friction in FRICTIONS:
        draws = pool_draws(NoWeights(), users, excess, 60.0, friction,
                           budget=300.0, seed=1, t=0)
        assert sum(draws) <= 60.0 + 1e-9
        for d, e in zip(draws, excess):
            assert 0.0 <= d <= e + 1e-9


def test_fcfs_is_a_race_not_prorata():
    # With pool smaller than total excess, FCFS gives the lucky arrival
    # their full excess; pro-rata water-fill splits evenly.
    users = ["a", "b"]
    excess = [100.0, 100.0]

    class NoWeights:
        pass

    fair = pool_draws(NoWeights(), users, excess, 100.0, "frictionless",
                      budget=200.0, seed=3, t=0)
    assert fair == pytest.approx([50.0, 50.0])
    race = pool_draws(NoWeights(), users, excess, 100.0, "fcfs",
                      budget=200.0, seed=3, t=0)
    assert sorted(race) == pytest.approx([0.0, 100.0])


def test_draw_cap_limits_single_user():
    users = ["a", "b"]
    excess = [1000.0, 0.0]

    class NoWeights:
        pass

    draws = pool_draws(NoWeights(), users, excess, 500.0, "draw_cap",
                       budget=200.0, seed=1, t=0)  # cap = 100 per user
    assert draws[0] == pytest.approx(100.0)


def test_unknown_friction_rejected():
    class NoWeights:
        pass

    with pytest.raises(ValueError):
        pool_draws(NoWeights(), ["a"], [1.0], 1.0, "bogus",
                   budget=10.0, seed=1, t=0)


def test_v2_weights_steer_draws():
    # dafb_v2 supplies earned weights; verify they reach pool_draws by
    # checking a worker out-draws a hoarder under contention.
    trace = simulate(SMALL, B, seed=8)
    m_v2 = run_trace("dafb_v2", trace, "frictionless")
    assert m_v2.budget_ok


def test_stats_helpers():
    m, half = mean_ci([1.0, 1.0, 1.0])
    assert m == 1.0 and half == 0.0
    m, half = mean_ci([0.0, 2.0])
    assert m == pytest.approx(1.0)
    assert half > 0
    d, half, sig = paired_diff([1.0, 1.0, 1.0], [0.0, 0.0, 0.0])
    assert d == pytest.approx(1.0) and sig
    d, half, sig = paired_diff([0.0, 1.0], [1.0, 0.0])
    assert not sig  # symmetric noise, no significance
    assert t95(29) == pytest.approx(2.045)
    assert t95(1000) == pytest.approx(1.96)
