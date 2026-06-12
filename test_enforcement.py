"""Tests for the LiteLLM enforcement adapter — all against a recording mock
transport; the network is never touched."""

import pytest

from allocator import DAFBv2Allocator
from enforcement import BudgetMutation, LiteLLMEnforcer

B = 1000.0


class RecordingTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, method, path, payload):
        self.calls.append((method, path, payload))
        return {"status": "ok"}


def make_allocation(usages: dict[str, float], budget: float = B):
    alloc = DAFBv2Allocator(budget=budget)
    for u in usages:
        alloc.add_user(u)
    a = alloc.allocate()
    alloc.observe(usages, a)
    return alloc.allocate()


@pytest.fixture
def setup():
    allocation = make_allocation({"alice": 600.0, "bob": 100.0, "cara": 5.0})
    transport = RecordingTransport()
    enf = LiteLLMEnforcer(transport=transport, budget=B)
    return allocation, transport, enf


# ------------------------------------------------------------- planning

def test_start_period_plans_floor_budgets(setup):
    allocation, _, enf = setup
    plan = enf.start_period(allocation)
    assert {m.user for m in plan} == {"alice", "bob", "cara"}
    by_user = {m.user: m for m in plan}
    for u, m in by_user.items():
        assert m.op == "set_budget"
        assert m.amount_usd == pytest.approx(allocation.quotas[u])
    assert enf.pool_remaining == pytest.approx(allocation.buffer)


def test_mutation_validation():
    with pytest.raises(ValueError):
        BudgetMutation("delete_user", "a", 1.0)
    with pytest.raises(ValueError):
        BudgetMutation("set_budget", "a", -1.0)


# ------------------------------------------------------------- dry run

def test_dry_run_never_touches_transport(setup):
    allocation, transport, enf = setup
    plan = enf.start_period(allocation)
    calls = enf.apply(plan)
    assert transport.calls == []           # nothing sent
    assert len(calls) == 3                 # but the full plan is inspectable
    assert all(c["path"] == "/user/update" for c in calls)


def test_live_mode_posts_user_updates(setup):
    allocation, transport, enf = setup
    enf.dry_run = False
    plan = enf.start_period(allocation)
    enf.apply(plan)
    assert len(transport.calls) == 3
    method, path, payload = transport.calls[0]
    assert (method, path) == ("POST", "/user/update")
    assert payload["budget_duration"] == "30d"
    assert payload["max_budget"] >= 0
    assert enf.applied_log == plan


# ------------------------------------------------------------- draws

def test_draws_follow_weights_and_consume_pool(setup):
    allocation, _, enf = setup
    enf.start_period(allocation)
    pool_before = enf.pool_remaining
    plan = enf.plan_draws({"alice": 300.0, "bob": 50.0}, allocation)
    granted = {m.user: m.amount_usd for m in plan}
    assert all(m.op == "raise_budget" for m in plan)
    assert sum(granted.values()) <= pool_before + 1e-9
    assert enf.pool_remaining == pytest.approx(pool_before - sum(granted.values()))
    # bob's full request fits; alice (heavier ask) gets the rest
    assert granted["bob"] == pytest.approx(50.0)


def test_cumulative_draw_cap_respected(setup):
    allocation, _, enf = setup
    enf.cap_multiplier = 1.0               # cap = B/n = 333.33
    enf.start_period(allocation)
    cap = 1.0 * B / 3
    total_alice = 0.0
    for _ in range(5):                     # repeated mid-period draws
        plan = enf.plan_draws({"alice": 500.0}, allocation)
        total_alice += sum(m.amount_usd for m in plan)
    assert total_alice <= cap + 1e-9


def test_raise_budget_payload_is_cumulative_max(setup):
    allocation, transport, enf = setup
    enf.dry_run = False
    enf.apply(enf.start_period(allocation))
    plan = enf.plan_draws({"cara": 100.0}, allocation)
    enf.apply(plan)
    # The last call's max_budget equals cara's floor + draw, not just the raise.
    _, _, payload = transport.calls[-1]
    assert payload["user_id"] == "cara"
    assert payload["max_budget"] == pytest.approx(
        allocation.quotas["cara"] + sum(m.amount_usd for m in plan))


def test_flat_budget_invariant_always_holds(setup):
    allocation, _, enf = setup
    enf.start_period(allocation)
    for _ in range(10):
        enf.plan_draws({"alice": 1000.0, "bob": 1000.0, "cara": 1000.0},
                       allocation)
    assert sum(enf.promised.values()) + enf.pool_remaining <= B + 1e-6


def test_no_draws_when_pool_empty(setup):
    allocation, _, enf = setup
    enf.start_period(allocation)
    enf.pool_remaining = 0.0
    assert enf.plan_draws({"alice": 100.0}, allocation) == []


# ----------------------------------------------------------- reconcile

def test_reconcile_flags_drift_and_shrinks_pool(setup):
    allocation, _, enf = setup
    enf.start_period(allocation)
    pool_before = enf.pool_remaining
    report = enf.reconcile(
        ledger_spend={"alice": 200.0, "bob": 20.0},   # org-wide truth
        proxy_spend={"alice": 150.0, "bob": 20.0},    # what the proxy saw
        tolerance_usd=1.0)
    assert report["drift"] == {"alice": pytest.approx(50.0)}
    assert report["out_of_band_usd"] == pytest.approx(50.0)
    assert enf.pool_remaining == pytest.approx(pool_before - 50.0)


def test_reconcile_within_tolerance_is_clean(setup):
    allocation, _, enf = setup
    enf.start_period(allocation)
    report = enf.reconcile({"alice": 100.5}, {"alice": 100.0})
    assert report["drift"] == {}
    assert report["out_of_band_usd"] == pytest.approx(0.5)
