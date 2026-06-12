"""Tests for the synthetic workload simulator: reproducibility, heavy-tail
concentration, scenario semantics, and ramp behavior."""

import pytest

from simulator import SCENARIOS, Scenario, gini, simulate, top_share

B = 1_000_000.0


def totals_per_user(trace) -> list[float]:
    return [sum(trace.user_series(u)) for u in trace.users]


# ----------------------------------------------------------- reproducibility

@pytest.mark.parametrize("name", list(SCENARIOS))
def test_same_seed_identical(name):
    a = simulate(SCENARIOS[name], B, seed=42)
    b = simulate(SCENARIOS[name], B, seed=42)
    assert a.demand == b.demand
    assert a.ramp_users == b.ramp_users


def test_different_seed_differs():
    a = simulate(SCENARIOS["stable"], B, seed=1)
    b = simulate(SCENARIOS["stable"], B, seed=2)
    assert a.demand != b.demand


# ------------------------------------------------------------ basic sanity

@pytest.mark.parametrize("name", list(SCENARIOS))
def test_all_demands_positive_finite(name):
    trace = simulate(SCENARIOS[name], B, seed=7)
    for period in trace.demand:
        for d in period.values():
            assert d > 0
            assert d == d and d != float("inf")


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_mean_total_matches_demand_ratio(name):
    sc = SCENARIOS[name]
    trace = simulate(sc, B, seed=11)
    mean_total = sum(trace.period_total(t) for t in range(sc.n_periods)) / sc.n_periods
    assert mean_total == pytest.approx(sc.demand_ratio * B, rel=1e-9)


def test_budget_must_be_positive():
    with pytest.raises(ValueError):
        simulate(SCENARIOS["stable"], 0.0, seed=1)


# --------------------------------------------------------------- heavy tail

@pytest.mark.parametrize("seed", range(5))
def test_stable_scenario_is_heavy_tailed(seed):
    # sigma=1.6 lognormal: top 20% of users should hold ~65-90% of demand.
    sc = Scenario(name="big", n_users=200, n_periods=26, sigma=1.6)
    trace = simulate(sc, B, seed=seed)
    share = top_share(totals_per_user(trace), 0.2)
    assert 0.55 < share < 0.95
    assert gini(totals_per_user(trace)) > 0.5


def test_crunch_is_more_homogeneous_than_stable():
    stable = simulate(SCENARIOS["stable"], B, seed=3)
    crunch = simulate(SCENARIOS["all_heavy_crunch"], B, seed=3)
    assert gini(totals_per_user(crunch)) < gini(totals_per_user(stable))


# ---------------------------------------------------------------- scenarios

def test_crunch_structurally_contended():
    sc = SCENARIOS["all_heavy_crunch"]
    trace = simulate(sc, B, seed=5)
    over = sum(1 for t in range(sc.n_periods) if trace.period_total(t) > B)
    assert over >= sc.n_periods * 0.8  # most periods exceed the budget


def test_stable_mostly_under_budget():
    sc = SCENARIOS["stable"]
    trace = simulate(sc, B, seed=5)
    under = sum(1 for t in range(sc.n_periods) if trace.period_total(t) < B)
    assert under >= sc.n_periods * 0.6


def test_bursty_spikier_than_stable():
    # Deterministic given fixed seeds: max/median per-user ratio is larger
    # in the bursty scenario.
    def spikiness(trace):
        ratios = []
        for u in trace.users:
            series = sorted(trace.user_series(u))
            median = series[len(series) // 2]
            ratios.append(max(series) / median)
        return sum(ratios) / len(ratios)

    stable = simulate(SCENARIOS["stable"], B, seed=9)
    bursty = simulate(SCENARIOS["bursty"], B, seed=9)
    assert spikiness(bursty) > spikiness(stable)


# --------------------------------------------------------------------- ramp

def test_ramp_users_start_light_end_heavy():
    sc = SCENARIOS["adoption_ramp"]
    trace = simulate(sc, B, seed=13)
    assert len(trace.ramp_users) == round(sc.ramp_frac * sc.n_users)
    q = sc.n_periods // 4
    for u in trace.ramp_users:
        series = trace.user_series(u)
        early = sum(series[:q]) / q
        late = sum(series[-q:]) / q
        assert late > early * 5  # logistic climb from ramp_floor


def test_no_ramp_users_when_frac_zero():
    trace = simulate(SCENARIOS["stable"], B, seed=1)
    assert trace.ramp_users == []


# ------------------------------------------------------------------ helpers

def test_top_share_and_gini_basics():
    assert top_share([1, 1, 1, 1, 96], 0.2) == pytest.approx(0.96)
    assert gini([1, 1, 1, 1]) == pytest.approx(0.0, abs=1e-12)
    assert gini([0.0001, 0.0001, 0.0001, 100]) > 0.7
    with pytest.raises(ValueError):
        top_share([])
    with pytest.raises(ValueError):
        gini([0.0, 0.0])
