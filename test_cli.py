"""End-to-end CLI tests in a temp working directory: ingest -> allocate ->
apply (dry) -> report -> simulate, plus state round-trips and safety."""

import json
import os

import pytest

from cli import main
from ledger import Ledger, UsageRecord


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = {"budget": 1000.0, "litellm": {"enabled": True,
                                         "base_url": "http://example.invalid"}}
    with open("token-optim.json", "w") as f:
        json.dump(cfg, f)
    led = Ledger([
        UsageRecord("alice", "2026-04", "claude_code", 400.0),
        UsageRecord("bob", "2026-04", "litellm", 60.0),
        UsageRecord("cara", "2026-04", "litellm", 5.0),
        UsageRecord(None, "2026-04", "copilot", 99.0),
        UsageRecord("alice", "2026-05", "claude_code", 500.0),
        UsageRecord("bob", "2026-05", "litellm", 80.0),
        UsageRecord("cara", "2026-05", "litellm", 4.0),
    ])
    with open("usage.csv", "w") as f:
        f.write(led.to_csv())
    return tmp_path


def test_full_loop(workspace, capsys):
    assert main(["ingest", "--csv", "usage.csv"]) == 0
    assert main(["allocate", "--period", "2026-04"]) == 0
    out = capsys.readouterr().out
    assert "POOL" in out and "alice" in out

    # State persisted with all users and the pending allocation.
    state = json.load(open("token-optim-state.json"))
    assert set(state["users"]) == {"alice", "bob", "cara"}
    assert state["allocation"]["buffer"] > 0
    assert "2026-04" in state["observed_periods"]

    # Dry-run apply: prints the plan, never needs a reachable proxy.
    assert main(["apply"]) == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out and "max_budget" in out

    # Report includes the data-quality qualification for copilot.
    assert main(["report", "--period", "2026-04", "--out", "r.md"]) == 0
    report = open("r.md").read()
    assert "copilot" in report and "unattributed" in report

    # Simulate runs on >=2 periods and states the censoring caveat.
    assert main(["allocate", "--period", "2026-05"]) == 0
    capsys.readouterr()
    assert main(["simulate"]) == 0
    out = capsys.readouterr().out
    assert "dafb_v2" in out and "censored" in out.lower()


def test_allocate_is_idempotent_per_period(workspace, capsys):
    main(["ingest", "--csv", "usage.csv"])
    main(["allocate", "--period", "2026-04"])
    state1 = json.load(open("token-optim-state.json"))
    main(["allocate", "--period", "2026-04"])     # same period again
    out = capsys.readouterr().out
    assert "already observed" in out
    state2 = json.load(open("token-optim-state.json"))
    assert state1["users"] == state2["users"]     # EWMAs unchanged


def test_state_round_trip_changes_allocations(workspace, capsys):
    main(["ingest", "--csv", "usage.csv"])
    main(["allocate", "--period", "2026-04"])
    s1 = json.load(open("token-optim-state.json"))["allocation"]
    main(["allocate", "--period", "2026-05"])
    s2 = json.load(open("token-optim-state.json"))["allocation"]
    # Two observed periods -> EWMAs moved -> floors differ.
    assert s1["quotas"] != s2["quotas"]


def test_apply_without_allocation_errors(workspace, capsys):
    main(["ingest", "--csv", "usage.csv"])
    assert main(["apply"]) == 1


def test_apply_yes_uses_live_path_and_fails_loudly(workspace, capsys):
    # --yes against an unreachable proxy must raise, not silently pass —
    # proving the live transport is actually constructed and called.
    main(["ingest", "--csv", "usage.csv"])
    main(["allocate", "--period", "2026-04"])
    with pytest.raises(Exception):
        main(["apply", "--yes"])


def test_unknown_config_key_rejected(workspace):
    with open("token-optim.json", "w") as f:
        json.dump({"budet": 5}, f)  # typo
    with pytest.raises(SystemExit):
        main(["allocate", "--period", "2026-04"])


def test_coarse_pushes_printed_for_non_litellm_providers(workspace, capsys):
    cfg = json.load(open("token-optim.json"))
    cfg["providers"] = ["litellm", "copilot", "claude_code"]
    cfg["litellm"]["enabled"] = False
    json.dump(cfg, open("token-optim.json", "w"))
    main(["ingest", "--csv", "usage.csv"])
    main(["allocate", "--period", "2026-04"])
    capsys.readouterr()
    assert main(["apply"]) == 0
    out = capsys.readouterr().out
    assert "[PUSH] copilot" in out
    assert "[NO-OP] claude_code" in out
    assert "litellm disabled" in out
