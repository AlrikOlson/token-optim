"""Tests for the Phase 5 experiment harness (parametric caps, pooling sim)."""

import pytest

from alternatives import _SubTrace, _served_per_user
from benchmark import pool_draws, run_trace
from simulator import Scenario, simulate

B = 100_000.0
SC = Scenario(name="alt", n_users=10, n_periods=10, demand_ratio=1.2)


def test_parametric_cap_parses_and_caps():
    class NoWeights:
        pass

    users = ["a", "b"]
    excess = [1000.0, 0.0]
    d1 = pool_draws(NoWeights(), users, excess, 500.0, "draw_cap:1",
                    budget=200.0, seed=1, t=0)
    d4 = pool_draws(NoWeights(), users, excess, 500.0, "draw_cap:4",
                    budget=200.0, seed=1, t=0)
    assert d1[0] == pytest.approx(100.0)   # 1x of 200/2
    assert d4[0] == pytest.approx(400.0)   # 4x of 200/2
    # bare 'draw_cap' still means 1x
    legacy = pool_draws(NoWeights(), users, excess, 500.0, "draw_cap",
                        budget=200.0, seed=1, t=0)
    assert legacy == d1


def test_cap_multiplier_monotone_service():
    # Looser caps can only help (weakly) the heavy users on a fixed trace.
    trace = simulate(SC, B, seed=2)
    unmet = [run_trace("dafb_v2", trace, f).heavy_unmet
             for f in ("draw_cap:1", "draw_cap:4", "frictionless")]
    assert unmet[0] >= unmet[1] >= unmet[2] - 1e-9


def test_subtrace_views_are_consistent():
    trace = simulate(SC, B, seed=3)
    members = trace.users[:5]
    sub = _SubTrace(trace, members, B / 2)
    assert sub.users == members
    assert sub.user_series(members[0]) == trace.user_series(members[0])
    assert len(sub.demand) == len(trace.demand)


def test_served_per_user_bounded_by_demand():
    trace = simulate(SC, B, seed=4)
    served = _served_per_user("dafb_v2", trace)
    for u in trace.users:
        total_d = sum(trace.user_series(u))
        assert 0.0 <= served[u] <= total_d + 1e-6


def test_served_total_bounded_by_budget():
    trace = simulate(SC, B, seed=5)
    served = _served_per_user("dafb_v2", trace)
    assert sum(served.values()) <= B * len(trace.demand) + 1e-6
