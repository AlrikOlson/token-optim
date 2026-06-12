"""Tests for advisory mode: seat recommendations, coarse pushes, and the
partial-visibility qualification in the report."""

import pytest

from advisory import (CLAUDE_CODE_PLANS, SeatPlan, advisory_report,
                      coarse_pushes, recommend_seat)
from allocator import DAFBv2Allocator
from ledger import Ledger, UsageRecord

B = 1000.0
P = "2026-05"


def make_allocation(usages):
    alloc = DAFBv2Allocator(budget=B)
    for u in usages:
        alloc.add_user(u)
    a = alloc.allocate()
    alloc.observe(usages, a)
    return alloc.allocate()


# --------------------------------------------------------- seat tiers

def test_recommend_seat_picks_cheapest_covering_plan():
    assert recommend_seat(10.0)[0].name == "pro"
    assert recommend_seat(60.0)[0].name == "max_5x"
    assert recommend_seat(400.0)[0].name == "max_20x"


def test_recommend_seat_overflow_names_top_plan():
    plan, note = recommend_seat(5000.0)
    assert plan.name == "max_20x"
    assert "overflow" in note


def test_recommend_seat_custom_cost_model():
    plans = (SeatPlan("basic", 10.0, 20.0), SeatPlan("ultra", 50.0, 500.0))
    assert recommend_seat(15.0, plans)[0].name == "basic"
    assert recommend_seat(100.0, plans)[0].name == "ultra"


# ------------------------------------------------------- coarse pushes

def test_coarse_pushes_executable_where_api_exists():
    allocation = make_allocation({"a": 100.0, "b": 50.0})
    pushes = {p.provider: p for p in coarse_pushes(
        allocation, ["anthropic", "copilot", "claude_code", "mystery"])}
    assert pushes["anthropic"].executable
    assert pushes["anthropic"].amount_usd == pytest.approx(B)
    assert pushes["copilot"].executable
    # Seat product: explanatory no-op, never silent.
    assert not pushes["claude_code"].executable
    assert "seat" in pushes["claude_code"].explanation.lower()
    assert not pushes["mystery"].executable
    assert pushes["mystery"].explanation


# ------------------------------------------------------------- report

def fixture_ledger():
    return Ledger([
        UsageRecord("alice", P, "claude_code", 300.0),
        UsageRecord("bob", P, "claude_code", 30.0),
        UsageRecord("cara", P, "litellm", 4.0),
        UsageRecord(None, P, "copilot", 250.0),   # unattributed org spend
    ])


def test_report_contains_all_users_and_seat_recs():
    led = fixture_ledger()
    allocation = make_allocation(led.per_user_period(P))
    report = advisory_report(led, allocation, P, B)
    for u in ("alice", "bob", "cara"):
        assert u in report
    assert "seat-tier recommendations" in report.lower()
    # cara has no claude_code records -> not in the seat table section.
    seat_section = report.split("seat-tier recommendations")[1]
    assert "cara" not in seat_section.split("## Data quality")[0]


def test_report_qualifies_unattributed_spend():
    led = fixture_ledger()
    allocation = make_allocation(led.per_user_period(P))
    report = advisory_report(led, allocation, P, B)
    assert "could not be attributed" in report
    assert "copilot: $250.00 unattributed" in report
    assert "EXCLUDED" in report


def test_report_clean_when_fully_attributed():
    led = Ledger([UsageRecord("alice", P, "litellm", 10.0)])
    allocation = make_allocation(led.per_user_period(P))
    report = advisory_report(led, allocation, P, B)
    assert "All spend in this period is attributed" in report


def test_report_plan_delta_when_current_plans_known():
    led = fixture_ledger()
    allocation = make_allocation(led.per_user_period(P))
    report = advisory_report(led, allocation, P, B,
                             current_plans={"bob": "max_20x"})
    # bob's forecast is tiny -> recommended pro -> delta -180 vs max_20x.
    assert "-180" in report


def test_cost_model_is_stated_in_report():
    led = fixture_ledger()
    allocation = make_allocation(led.per_user_period(P))
    report = advisory_report(led, allocation, P, B)
    assert "Cost model:" in report
    for p in CLAUDE_CODE_PLANS:
        assert p.name in report
