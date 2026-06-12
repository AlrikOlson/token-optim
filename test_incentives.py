"""Tests for the strategic-behavior harness."""

import pytest

from incentives import median_user, run_strategic
from simulator import Scenario, simulate

B = 100_000.0
SC = Scenario(name="inc", n_users=12, n_periods=16, demand_ratio=1.2)


def test_median_user_deterministic():
    trace = simulate(SC, B, seed=1)
    assert median_user(trace) == median_user(trace)
    assert median_user(trace) in trace.users


@pytest.mark.parametrize("algo", ["usage_proportional", "max_min", "dafb",
                                  "dafb_v2"])
def test_honest_run_burns_nothing(algo):
    trace = simulate(SC, B, seed=2)
    out = run_strategic(algo, trace, None, 1.0, "frictionless")
    assert out.burn_frac == pytest.approx(0.0, abs=1e-12)
    assert 0.0 <= out.target_served_frac <= 1.0 + 1e-9
    assert 0.0 <= out.honest_heavy_unmet <= 1.0


@pytest.mark.parametrize("algo", ["usage_proportional", "max_min", "dafb",
                                  "dafb_v2"])
def test_strategic_run_deterministic(algo):
    trace = simulate(SC, B, seed=3)
    u = median_user(trace)
    a = run_strategic(algo, trace, u, 2.0, "frictionless")
    b = run_strategic(algo, trace, u, 2.0, "frictionless")
    assert a == b


def test_burner_actually_burns():
    trace = simulate(SC, B, seed=4)
    u = median_user(trace)
    out = run_strategic("dafb_v2", trace, u, 4.0, "frictionless")
    assert out.burn_frac > 0.0


def test_burning_hurts_honest_heavies_or_is_neutral():
    # Across a few seeds, collateral should be >= 0 on average (the gamer
    # cannot make honest heavy users better off by burning).
    deltas = []
    for seed in range(5):
        trace = simulate(SC, B, seed=seed)
        u = median_user(trace)
        honest = run_strategic("dafb_v2", trace, None, 1.0, "frictionless")
        strat = run_strategic("dafb_v2", trace, u, 4.0, "frictionless")
        deltas.append(strat.honest_heavy_unmet - honest.honest_heavy_unmet)
    assert sum(deltas) / len(deltas) >= -1e-6


def test_draw_cap_throttles_burn():
    # With pool draws capped at one equal share, total burn cannot exceed
    # floor + cap each period; expect strictly less burn than frictionless.
    trace = simulate(SC, B, seed=5)
    u = median_user(trace)
    free = run_strategic("dafb_v2", trace, u, 4.0, "frictionless")
    capped = run_strategic("dafb_v2", trace, u, 4.0, "draw_cap")
    assert capped.burn_frac < free.burn_frac
