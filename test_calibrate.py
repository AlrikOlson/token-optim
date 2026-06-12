"""Calibration machinery tests — the load-bearing one is parameter recovery:
the estimators must recover the simulator's known ground truth from traces
the simulator itself generated, within stated tolerances."""

import json

import pytest

from calibrate import calibrated_benchmark, fit_parameters
from cli import main
from ledger import Ledger, UsageRecord
from simulator import Scenario, simulate

B = 1_000_000.0


def trace_to_ledger(trace) -> Ledger:
    records = []
    for t, period_demand in enumerate(trace.demand):
        period = f"2026-{t + 1:02d}"
        for u, d in period_demand.items():
            records.append(UsageRecord(u, period, "litellm", d))
    return Ledger(records)


# ----------------------------------------------------- parameter recovery

@pytest.mark.parametrize("sigma", [1.2, 1.6])
def test_recovers_sigma(sigma):
    sc = Scenario(name="truth", n_users=80, n_periods=26, sigma=sigma,
                  demand_ratio=0.9)
    fitted = fit_parameters(trace_to_ledger(simulate(sc, B, seed=1)), B)
    assert fitted.sigma == pytest.approx(sigma, abs=0.35)


def test_recovers_rho_and_burst_roughly():
    sc = Scenario(name="truth", n_users=80, n_periods=26, rho=0.8,
                  burst_prob=0.05, demand_ratio=0.9)
    fitted = fit_parameters(trace_to_ledger(simulate(sc, B, seed=2)), B)
    assert fitted.rho == pytest.approx(0.8, abs=0.25)
    assert fitted.burst_prob == pytest.approx(0.05, abs=0.10)


def test_recovers_demand_ratio_exactly_on_uncensored_data():
    sc = Scenario(name="truth", n_users=40, n_periods=12, demand_ratio=1.3)
    fitted = fit_parameters(trace_to_ledger(simulate(sc, B, seed=3)), B)
    assert fitted.demand_ratio == pytest.approx(1.3, rel=1e-6)
    assert any("LOWER bound" in w for w in fitted.warnings)


def test_short_panel_warns_and_defaults():
    led = Ledger([UsageRecord("a", "2026-01", "x", 10.0),
                  UsageRecord("b", "2026-01", "x", 99.0)])
    fitted = fit_parameters(led, 1000.0)
    assert fitted.rho == 0.8
    assert any("fewer than 3 periods" in w for w in fitted.warnings)


def test_fit_rejects_degenerate_input():
    with pytest.raises(ValueError):
        fit_parameters(Ledger([UsageRecord("a", "2026-01", "x", 5.0)]), 100.0)
    with pytest.raises(ValueError):
        fit_parameters(Ledger([UsageRecord("a", "2026-01", "x", 0.0),
                               UsageRecord("b", "2026-01", "x", 0.0)]), 100.0)


def test_calibrated_benchmark_outputs_all_algos():
    sc = Scenario(name="truth", n_users=20, n_periods=12, demand_ratio=0.9)
    fitted = fit_parameters(trace_to_ledger(simulate(sc, B, seed=4)), B)
    lines = "\n".join(calibrated_benchmark(fitted, B, seeds=5))
    for algo in ("dafb_v2", "max_min", "equal_split"):
        assert algo in lines
    assert "±" in lines and "WARNING" in lines


# ------------------------------------------------------- CLI subcommands

@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    json.dump({"budget": 1000.0}, open("token-optim.json", "w"))
    led = Ledger([
        UsageRecord(u, p, "litellm", v)
        for p, vals in [("2026-03", {"alice": 300, "bob": 40, "cara": 8}),
                        ("2026-04", {"alice": 350, "bob": 55, "cara": 6}),
                        ("2026-05", {"alice": 280, "bob": 70, "cara": 9})]
        for u, v in vals.items()
    ])
    with open("usage.csv", "w") as f:
        f.write(led.to_csv())
    main(["ingest", "--csv", "usage.csv"])
    return tmp_path


def test_cli_calibrate(workspace, capsys):
    capsys.readouterr()
    assert main(["calibrate", "--seeds", "3"]) == 0
    out = capsys.readouterr().out
    assert "calibrated scenario" in out
    assert "dafb_v2" in out
    assert "LOWER bound" in out


def test_cli_reconcile(workspace, capsys):
    main(["allocate", "--period", "2026-03"])
    proxy = Ledger([UsageRecord("alice", "2026-03", "litellm", 250.0),
                    UsageRecord("bob", "2026-03", "litellm", 40.0)])
    with open("proxy.csv", "w") as f:
        f.write(proxy.to_csv())
    capsys.readouterr()
    assert main(["reconcile", "--proxy-csv", "proxy.csv",
                 "--period", "2026-03"]) == 0
    out = capsys.readouterr().out
    assert "alice" in out                     # 300 vs 250 -> drift +50
    assert "out-of-band" in out
    assert "pool reduced" in out
