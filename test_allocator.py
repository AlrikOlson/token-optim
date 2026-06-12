"""Property suite for the DAFB allocator (P1-P6 from DESIGN.md) plus edge cases."""

import random

import pytest

from allocator import Allocation, DAFBAllocator, DAFBv2Allocator, water_fill

B = 10_000.0


def make_allocator(usages: dict[str, float] | None = None, budget: float = B,
                   **kw) -> DAFBAllocator:
    """Allocator with one observed period of usage so forecasts are real."""
    alloc = DAFBAllocator(budget=budget, **kw)
    usages = usages or {}
    for uid in usages:
        alloc.add_user(uid)
    if usages:
        first = alloc.allocate()
        alloc.observe(usages, first)
    return alloc


def random_population(seed: int, n: int = 12) -> dict[str, float]:
    """Heavy-tailed usage population (lognormal-ish via random)."""
    rng = random.Random(seed)
    return {f"u{i}": rng.lognormvariate(6.0, 1.5) for i in range(n)}


# ---------------------------------------------------------------- water_fill

def test_water_fill_exact_budget():
    grants = water_fill([100, 200, 700], [1, 1, 1], 600)
    assert sum(grants) == pytest.approx(600, abs=1e-9)


def test_water_fill_demand_capped():
    grants = water_fill([100, 200, 300], [1, 1, 1], 10_000)
    assert grants == [100, 200, 300]


def test_water_fill_zero_target():
    assert water_fill([5, 5], [1, 1], 0) == [0.0, 0.0]


def test_water_fill_equal_weights_equal_level():
    # Two unsaturated equal-weight users end at the same level.
    grants = water_fill([1000, 1000, 10], [1, 1, 1], 510)
    assert grants[0] == pytest.approx(grants[1])
    assert grants[2] == pytest.approx(10)


def test_water_fill_weight_monotone():
    lo = water_fill([1000, 1000], [1, 1], 1000)
    hi = water_fill([1000, 1000], [3, 1], 1000)
    assert hi[0] > lo[0]


def test_water_fill_rejects_bad_input():
    with pytest.raises(ValueError):
        water_fill([1], [1, 2], 5)
    with pytest.raises(ValueError):
        water_fill([-1], [1], 5)
    with pytest.raises(ValueError):
        water_fill([1], [0], 5)


# ------------------------------------------------------------- P1: budget

@pytest.mark.parametrize("seed", range(20))
def test_p1_budget_conservation(seed):
    alloc = make_allocator(random_population(seed))
    a = alloc.allocate()
    assert a.total == pytest.approx(B, abs=1e-6)          # quotas + buffer == B
    assert sum(a.quotas.values()) <= B + 1e-6


def test_p1_holds_over_many_periods():
    alloc = make_allocator(random_population(99))
    rng = random.Random(7)
    for _ in range(30):
        a = alloc.allocate()
        assert a.total == pytest.approx(B, abs=1e-6)
        usage = {i: max(0.0, q * rng.uniform(0.3, 1.4)) for i, q in a.quotas.items()}
        alloc.observe(usage, a)


# ------------------------------------------------------------- P2: floors

@pytest.mark.parametrize("seed", range(20))
def test_p2_floor_guarantee(seed):
    alloc = make_allocator(random_population(seed))
    a = alloc.allocate()
    share = B / len(a.quotas)
    for i, q in a.quotas.items():
        assert q >= min(a.forecasts[i], share) - 1e-9


def test_p2_heavy_demand_cannot_push_anyone_below_share():
    # One user forecasts 100x the budget; others still get their entitlement.
    usages = {"whale": B * 100, "a": 900.0, "b": 900.0, "c": 900.0}
    alloc = make_allocator(usages)
    a = alloc.allocate()
    share = B / 4
    for i in ("a", "b", "c"):
        assert a.quotas[i] >= min(a.forecasts[i], share) - 1e-9


# ------------------------------------- P3: no contention -> fully funded

def test_p3_no_contention_everyone_fully_funded():
    usages = {"a": 1000.0, "b": 2000.0, "c": 500.0}  # sum well under B
    alloc = make_allocator(usages)
    a = alloc.allocate()
    for i, q in a.quotas.items():
        assert q == pytest.approx(a.forecasts[i], rel=1e-9)
    assert a.buffer == pytest.approx(B - sum(a.forecasts.values()), rel=1e-9)
    assert a.buffer > 0


# ------------------------------------------------------ P4: no waste

def test_p4_zero_demand_user_gets_zero_slack_recycles():
    usages = {"idle": 0.0, "heavy1": B, "heavy2": B}
    alloc = make_allocator(usages)
    a = alloc.allocate()
    assert a.quotas["idle"] == pytest.approx(0.0, abs=1e-9)
    # idle user's entire equal share went to the heavy users
    assert a.quotas["heavy1"] + a.quotas["heavy2"] == pytest.approx(B, abs=1e-6)


@pytest.mark.parametrize("seed", range(10))
def test_p4_never_allocated_above_forecast(seed):
    alloc = make_allocator(random_population(seed))
    a = alloc.allocate()
    for i, q in a.quotas.items():
        assert q <= a.forecasts[i] + 1e-9


# ------------------------------------- P5: heavy users share scarcity

def test_p5_equal_heavy_users_get_equal_grants():
    # Two identical whales contending: symmetric outcome, not FCFS.
    usages = {"w1": B * 2, "w2": B * 2, "light": 100.0}
    alloc = make_allocator(usages)
    a = alloc.allocate()
    assert a.quotas["w1"] == pytest.approx(a.quotas["w2"], rel=1e-9)
    assert a.quotas["w1"] > B / 3  # both got more than equal share


def test_p5_all_heavy_crunch_degrades_to_equal_split():
    # Everyone wants more than B: equal histories -> equal split, sum == B.
    usages = {f"h{i}": B for i in range(5)}
    alloc = make_allocator(usages)
    a = alloc.allocate()
    vals = list(a.quotas.values())
    assert all(v == pytest.approx(vals[0], rel=1e-9) for v in vals)
    assert sum(vals) == pytest.approx(B, abs=1e-6)
    assert a.buffer == pytest.approx(0.0, abs=1e-6)


# ------------------------------------------- P6: earned-weight monotone

def test_p6_higher_utilization_fills_faster():
    # Same demand history, but one user consistently uses their grant and
    # the other uses a small fraction of it.
    alloc = DAFBAllocator(budget=B)
    for uid in ("worker", "hoarder", "light"):
        alloc.add_user(uid)
    for _ in range(8):
        a = alloc.allocate()
        usage = {
            "worker": a.quotas["worker"],            # full utilization
            "hoarder": a.quotas["hoarder"] * 0.05,   # hoards
            "light": 50.0,
        }
        alloc.observe(usage, a)
    a = alloc.allocate()
    assert a.weights["worker"] > a.weights["hoarder"]
    # Worker's forecast collapsed less and weight is higher -> bigger quota.
    assert a.quotas["worker"] > a.quotas["hoarder"]


# ----------------------------------------------------------- burst buffer

def test_buffer_draw_accounting():
    usages = {"a": 1000.0, "b": 1000.0}
    alloc = make_allocator(usages)
    a = alloc.allocate()
    assert alloc.buffer_remaining == pytest.approx(a.buffer)
    got = alloc.draw_buffer(a.buffer / 2)
    assert got == pytest.approx(a.buffer / 2)
    got2 = alloc.draw_buffer(a.buffer)  # asks for more than remains
    assert got2 == pytest.approx(a.buffer / 2)
    assert alloc.buffer_remaining == pytest.approx(0.0, abs=1e-9)
    with pytest.raises(ValueError):
        alloc.draw_buffer(-1)


# ------------------------------------------------------------- edge cases

def test_cold_start_equal_shares():
    alloc = DAFBAllocator(budget=B)
    for uid in ("a", "b", "c", "d"):
        alloc.add_user(uid)
    a = alloc.allocate()
    for q in a.quotas.values():
        assert q == pytest.approx(B / 4, rel=1e-9)
    assert a.buffer == pytest.approx(0.0, abs=1e-9)


def test_no_users_raises():
    with pytest.raises(ValueError):
        DAFBAllocator(budget=B).allocate()


def test_negative_usage_rejected():
    alloc = make_allocator({"a": 10.0})
    a = alloc.allocate()
    with pytest.raises(ValueError):
        alloc.observe({"a": -5.0}, a)


# ------------------------------------------------------------- DAFB v2

def make_v2(usages: dict[str, float], budget: float = B) -> DAFBv2Allocator:
    alloc = DAFBv2Allocator(budget=budget)
    for uid in usages:
        alloc.add_user(uid)
    a = alloc.allocate()
    alloc.observe(usages, a)
    return alloc


@pytest.mark.parametrize("seed", range(10))
def test_v2_budget_conservation(seed):
    alloc = make_v2(random_population(seed))
    a = alloc.allocate()
    assert a.total == pytest.approx(B, abs=1e-6)
    assert all(q >= 0 for q in a.quotas.values())


@pytest.mark.parametrize("seed", range(10))
def test_v2_floors_bounded_and_pool_maximal(seed):
    alloc = make_v2(random_population(seed))
    a = alloc.allocate()
    n = len(a.quotas)
    cap = alloc.floor_frac * B / n
    for i, q in a.quotas.items():
        assert q <= cap + 1e-9              # floors never exceed the cap
        assert q <= a.forecasts[i] + 1e-9   # and never exceed forecast
    # Pool is at least the non-floor fraction of the budget.
    assert a.buffer >= (1 - alloc.floor_frac) * B - 1e-6


def test_v2_no_starvation_floor():
    # Even with whales around, an active user keeps their demand-capped floor.
    alloc = make_v2({"whale1": B * 10, "whale2": B * 10, "small": 500.0})
    a = alloc.allocate()
    cap = alloc.floor_frac * B / 3
    assert a.quotas["small"] == pytest.approx(min(500.0, cap), rel=1e-9)


def test_v2_zero_demand_user_cedes_floor():
    alloc = make_v2({"idle": 0.0, "busy": B})
    a = alloc.allocate()
    assert a.quotas["idle"] == pytest.approx(0.0, abs=1e-9)


def test_v2_draw_weights_bounds_and_ordering():
    alloc = DAFBv2Allocator(budget=B)
    for uid in ("worker", "hoarder"):
        alloc.add_user(uid)
    for _ in range(6):
        a = alloc.allocate()
        alloc.observe({"worker": a.quotas["worker"],
                       "hoarder": a.quotas["hoarder"] * 0.05}, a)
    w = alloc.draw_weights()
    assert alloc.w_min <= w["hoarder"] < w["worker"] <= 1.0


def test_v2_cold_start_floors_are_capped_equal_shares():
    alloc = DAFBv2Allocator(budget=B)
    for uid in ("a", "b", "c", "d"):
        alloc.add_user(uid)
    a = alloc.allocate()
    cap = alloc.floor_frac * B / 4
    for q in a.quotas.values():
        assert q == pytest.approx(cap, rel=1e-9)
    assert a.buffer == pytest.approx(B - 4 * cap, rel=1e-9)


def test_v2_negative_usage_rejected():
    alloc = make_v2({"a": 10.0})
    a = alloc.allocate()
    with pytest.raises(ValueError):
        alloc.observe({"a": -1.0}, a)


def test_ramping_user_reclaims_entitlement():
    # A light user turning heavy climbs back to (at least) equal share via
    # saturation probing, despite their usage being censored by the cap.
    alloc = DAFBAllocator(budget=B)
    for uid in ("ramp", "w1", "w2"):
        alloc.add_user(uid)
    a = alloc.allocate()
    alloc.observe({"ramp": 10.0, "w1": B, "w2": B}, a)
    quotas = []
    for _ in range(18):
        a = alloc.allocate()
        quotas.append(a.quotas["ramp"])
        # ramp user now consumes every token granted (saturated each period)
        alloc.observe({"ramp": a.quotas["ramp"], "w1": B, "w2": B}, a)
    share = B / 3
    assert quotas[-1] >= share * 0.95
    assert quotas[-1] > quotas[0]


def test_probe_clears_when_user_stops_saturating():
    alloc = make_allocator({"a": 1000.0, "b": 1000.0})
    a = alloc.allocate()
    alloc.observe({"a": a.quotas["a"], "b": 100.0}, a)  # a saturated
    assert alloc.users["a"].probe > 0
    a = alloc.allocate()
    alloc.observe({"a": a.quotas["a"] * 0.5, "b": 100.0}, a)  # a leaves headroom
    assert alloc.users["a"].probe == 0.0
