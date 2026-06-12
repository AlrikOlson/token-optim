"""Tests for the usage ledger and provider parsers. Fixtures encode our
schema assumptions about each provider's payload (validated live in op-5)."""

import pytest

from allocator import DAFBv2Allocator
from ledger import (Ledger, UsageRecord, parse_anthropic_cost,
                    parse_claude_code_analytics, parse_copilot_billing,
                    parse_litellm_spend)

P = "2026-05"


# ------------------------------------------------------------- record/ledger

def test_record_validation():
    with pytest.raises(ValueError):
        UsageRecord(user="a", period=P, provider="x", cost_usd=-1.0)
    with pytest.raises(ValueError):
        UsageRecord(user="a", period=P, provider="x", cost_usd=1.0,
                    unit_type="bananas")
    with pytest.raises(ValueError):
        UsageRecord(user="a", period="", provider="x", cost_usd=1.0)


def test_multi_provider_costs_sum_per_user():
    led = Ledger([
        UsageRecord("alice", P, "claude_code", 120.0),
        UsageRecord("alice", P, "copilot", 30.0),
        UsageRecord("bob", P, "claude_code", 10.0),
        UsageRecord("alice", "2026-06", "claude_code", 99.0),
    ])
    by = led.usage_by_period()
    assert by[P]["alice"] == pytest.approx(150.0)
    assert by[P]["bob"] == pytest.approx(10.0)
    assert by["2026-06"]["alice"] == pytest.approx(99.0)
    assert led.users() == ["alice", "bob"]
    assert led.periods() == [P, "2026-06"]
    assert led.providers() == ["claude_code", "copilot"]


def test_unattributed_rows_surface_not_silently_drop():
    led = Ledger([
        UsageRecord(None, P, "copilot", 500.0),
        UsageRecord("alice", P, "copilot", 25.0),
    ])
    assert led.unattributed() == {P: pytest.approx(500.0)}
    assert led.per_user_period(P) == {"alice": pytest.approx(25.0)}
    assert led.users() == ["alice"]


def test_csv_round_trip_preserves_everything():
    led = Ledger([
        UsageRecord("alice", P, "anthropic", 12.345, 1_000_000, "tokens"),
        UsageRecord(None, P, "copilot", 77.0, 190, "premium_requests"),
    ])
    again = Ledger.from_csv(led.to_csv())
    assert again.records == led.records


# ------------------------------------------------------------ parsers

def test_parse_anthropic_cost():
    payload = {"data": [
        {"starting_at": "2026-05-01T00:00:00Z", "results": [
            {"user": "alice@org.com", "amount": 41.5, "currency": "USD"},
            {"api_key_name": "ci-bot", "amount": 8.0, "currency": "USD"},
        ]},
        {"starting_at": "2026-05-02T00:00:00Z", "results": [
            {"user": "alice@org.com", "amount": 2.5, "currency": "USD"},
        ]},
    ]}
    recs = parse_anthropic_cost(payload, P)
    assert len(recs) == 3
    led = Ledger(recs)
    assert led.per_user_period(P)["alice@org.com"] == pytest.approx(44.0)
    assert led.per_user_period(P)["ci-bot"] == pytest.approx(8.0)


def test_parse_claude_code_analytics():
    payload = {"data": [
        {"actor_email": "alice@org.com", "estimated_cost_usd": 6.2,
         "total_tokens": 1_500_000},
        {"actor_email": "bob@org.com", "estimated_cost_usd": 0.4,
         "total_tokens": 90_000},
    ]}
    recs = parse_claude_code_analytics(payload, P)
    assert recs[0].provider == "claude_code"
    assert recs[0].unit_type == "tokens"
    assert recs[0].raw_units == 1_500_000
    assert Ledger(recs).per_user_period(P)["bob@org.com"] == pytest.approx(0.4)


def test_parse_copilot_billing_filters_skus_and_keeps_aggregates():
    payload = {"usageItems": [
        {"sku": "copilot_premium_requests", "username": "alice",
         "netAmount": 12.0, "quantity": 300},
        {"sku": "copilot_premium_requests", "username": None,
         "netAmount": 88.0, "quantity": 2200},          # org-level, no user
        {"sku": "actions_linux", "username": "alice", "netAmount": 5.0,
         "quantity": 100},                               # not Copilot
    ]}
    recs = parse_copilot_billing(payload, P)
    assert len(recs) == 2  # actions row filtered out
    led = Ledger(recs)
    assert led.per_user_period(P)["alice"] == pytest.approx(12.0)
    assert led.unattributed()[P] == pytest.approx(88.0)  # the documented gap
    assert recs[0].unit_type == "premium_requests"


def test_parse_litellm_spend():
    payload = [
        {"user": "alice", "spend": 3.25, "total_tokens": 800_000},
        {"end_user": "bob", "spend": 0.75, "total_tokens": 200_000},
    ]
    recs = parse_litellm_spend(payload, P)
    led = Ledger(recs)
    assert led.per_user_period(P) == {"alice": pytest.approx(3.25),
                                      "bob": pytest.approx(0.75)}


# ------------------------------------------- ledger -> allocator integration

def test_ledger_feeds_dafb_v2_in_dollars():
    # Two periods of real-ish multi-provider usage drive the allocator with
    # a dollar budget; quotas come back budget-conserving.
    budget = 1000.0
    led = Ledger([
        UsageRecord("alice", "2026-04", "claude_code", 400.0),
        UsageRecord("alice", "2026-04", "copilot", 100.0),
        UsageRecord("bob", "2026-04", "litellm", 50.0),
        UsageRecord("cara", "2026-04", "litellm", 5.0),
    ])
    alloc = DAFBv2Allocator(budget=budget)
    for u in led.users():
        alloc.add_user(u)
    a = alloc.allocate()
    alloc.observe(led.per_user_period("2026-04"), a)
    a2 = alloc.allocate()
    assert a2.total == pytest.approx(budget, abs=1e-9)
    # Heavy user's floor is capped at half the equal share; light user's
    # floor tracks their tiny spend.
    cap = 0.5 * budget / 3
    assert a2.quotas["alice"] == pytest.approx(cap)
    assert a2.quotas["cara"] == pytest.approx(5.0)
