# DAFB — Demand-Adaptive Floors with Buffer

**Allocating a flat organizational AI-token budget across users with heterogeneous demand.**

Status: Phase 1 design (chunk `phase-1-formalize-design`). Empirical validation in Phases 2–4.

---

## 1. Problem statement

An organization buys a **flat budget of `B` tokens per period** (e.g., per month). It has `n`
users whose true demand for tokens is wildly unequal — token usage across a population is
heavy-tailed (a minority of power users account for a majority of consumption). The org wants
an allocation rule that:

1. **Never exceeds `B`** (no surprise overage billing).
2. **Heavy, experienced users get the tokens they actually need**, funded by the slack that
   light users predictably leave on the table.
3. **Heavy users do not rob each other**: when several power users contend, the rule treats
   them symmetrically at the margin rather than first-come-first-served.
4. **Light users are never locked out**: anyone can ramp up and reclaim up to their fair
   entitlement at any time.
5. **Waste is minimized**: tokens reserved for someone who won't use them are tokens denied to
   someone who would.

The naive rules each fail one of these:

| Rule | Failure |
|---|---|
| Equal split `B/n` | Massive waste from light users; heavy users starved (fails 2, 5) |
| Pure usage-proportional | Rich-get-richer; a ramping user can't break in (fails 4); rewards waste |
| Static tiers (industry practice: LiteLLM, Kong, Azure APIM quotas) | Tiers go stale; reassignment is manual and political (fails 2, 5) |
| First-come-first-served pool | Heavy users race each other; end-of-period famine (fails 3, 4) |

## 2. Formal model

- Periods `t = 1, 2, …` (e.g., weeks within a billing month, or months).
- Budget `B > 0` tokens per period (flat — the thing we must not increase).
- Users `i = 1..n`. Observed usage last period: `u_i(t)`. Allocation this period: `q_i(t)`.
- **Feasibility (hard):** `Σ_i q_i(t) + buffer(t) ≤ B` for every `t`.

The allocator sees only realized usage history `{u_i(1..t-1)}` and prior allocations — no
self-reported demand (requests are cheap talk; observed utilization is a costly signal).

## 3. The DAFB algorithm

Three stages per period, plus a mid-period burst buffer.

### Stage A — Demand forecasting (per user)

Robust EWMA forecast with deviation headroom, so a *growing* user's forecast leads (not lags)
their trajectory:

```
v_i ← α·|u_i − m_i| + (1−α)·v_i  # EWMA absolute deviation (vs pre-update mean, Jacobson-style)
m_i ← α·u_i + (1−α)·m_i          # EWMA mean of usage
d̂_i = m_i + κ·v_i                # forecast demand, κ ≥ 0 headroom factor
```

Cold start: a new user enters with `d̂_i = B/n` (the equal-share prior) so they are neither
starved nor over-funded before they have history. Defaults: `α = 0.3`, `κ = 1.0`.

**Saturation probing (demand uncensoring).** Observed usage is a *censored* observation of
latent demand: a user capped at `q_i` can never show usage above `q_i`, so a pure EWMA
forecast would seal a light-turned-heavy user at their old quota forever (discovered while
constructing the ramp-up property test). Remedy, borrowed from TCP slow start: if a user
consumes ≥ `0.95·q_i` of their grant (saturated), their next forecast is bumped:

```
probe_i = γ·u_i  if u_i ≥ 0.95·q_i else 0      # γ = 1.5
d̂_i = max(m_i + κ·v_i, probe_i)
```

A persistently saturated user climbs ×1.5 per period — exponential recovery toward their
entitlement — and the probe vanishes the first period they leave headroom unused, bounding
forecast overshoot to one γ-step.

### Stage B — Entitlement floors (the fairness guarantee)

Every user is guaranteed their **max-min entitlement**:

```
f_i = min(d̂_i, B/n)
```

Interpretation: nobody can be pushed below the equal share by someone else's appetite, and a
light user (`d̂_i < B/n`) automatically cedes the difference — that ceded amount is exactly the
**slack pool** the brief intuits: `S = Σ_i max(0, B/n − d̂_i)`.

### Stage C — Earned-weight water-filling on the residual

Residual budget `R = B − Σf_i` is distributed against residual demands `r_i = d̂_i − f_i`
(only heavy users have `r_i > 0`) by **weighted progressive filling** (Bertsekas–Gallager
water-filling, the primitive underlying max-min fairness and DRF):

```
find λ ≥ 0 such that  Σ_i min(r_i, w_i·λ) = min(R, Σ_i r_i)
q_i = f_i + min(r_i, w_i·λ)
```

Solved **exactly** by sorting breakpoints `r_i/w_i` (no numerical tolerance — budget
conservation is an identity).

The weights are **earned from demonstrated utilization**, not requested:

```
util_i ← EWMA of min(1, u_i / q_i)        # how much of past grants were actually used
w_i = w_min + (1 − w_min)·util_i          # w_min > 0 keeps everyone fillable
```

A user who consistently uses what they're granted fills faster; a user who hoards fills
slower. This is the bespoke piece: *experience is operationalized as demonstrated utilization*,
which is costly to fake (you must actually burn tokens — quantified as an attack in Phase 4).
Default `w_min = 0.25`.

### Burst buffer

Whatever residual remains after all forecast demand is met is **not** pre-assigned:

```
buffer = B − Σ_i q_i
```

It stays liquid for mid-period overage draws (a user who blows past `q_i` mid-period draws
from the buffer rather than being hard-stopped), with draws debited so `Σ draws ≤ buffer`.
Under low contention the buffer is large and quotas are soft; under high contention it
naturally shrinks toward zero and quotas bind. The reference implementation models the buffer
size and draw accounting; queueing discipline for concurrent draws is a Phase 2+ concern.

## 4. Properties (each is a test in `test_allocator.py`)

- **P1 Budget conservation:** `Σq_i + buffer = B` exactly, and `Σq_i ≤ B`, every period.
- **P2 Floor guarantee:** `q_i ≥ min(d̂_i, B/n)` — no user is starved below the equal-share
  entitlement they actually want.
- **P3 No-contention fully-funded:** if `Σd̂ ≤ B` then `q_i = d̂_i` for all `i` and the rest is
  buffer.
- **P4 No reservation waste:** `q_i ≤ d̂_i` — zero-demand users get 0; their slack recycles.
- **P5 Symmetric heavy users:** under contention, users with equal weights whose demand
  exceeds the water line receive **equal** residual grants — heavy users don't rob each
  other; scarcity is shared at the margin.
- **P6 Earned-weight monotonicity:** ceteris paribus, higher `w_i` ⇒ weakly higher `q_i`.

P1–P5 follow from the water-filling construction (P2 because floors are granted before the
residual round; P5 because equal-weight unsaturated users sit at the same level `w·λ`). P6
holds at fixed λ-target since `min(r, wλ)` is nondecreasing in `w`. All six are verified
empirically by the test suite rather than trusted.

## 5. Known limitations / open questions (honest accounting)

- **Use-it-or-lose-it hazard:** utilization-earned weights create an incentive to burn tokens
  to protect next period's weight. Mitigations (weight caps, decay, utilization measured
  against *demand* not grant) are Phase 4's subject — unquantified as of Phase 1.
- **Forecast lag:** EWMA with `κ·v` headroom still lags a step-change in demand; saturation
  probing converts the lag into an exponential (×γ per period) climb rather than a permanent
  trap, but a user starting from a tiny quota still needs ~`log_γ(entitlement/quota)` periods
  to fully recover (≈15 periods from 0.3% of share at γ=1.5). Shorter allocation periods or a
  larger γ trade recovery speed against overshoot waste — a Phase 3 sweep.
- **`B/n` floor with very large `n`:** if `n` grows so the equal share is tiny, floors stop
  mattering and DAFB degenerates toward pure weighted water-filling. May need a minimum
  absolute floor parameter.
- **Within-period dynamics** (who draws the buffer first) are not yet modeled.

## 6. Prior art this builds on

- Max-min fairness & progressive filling — Bertsekas & Gallager, *Data Networks*.
- Dominant Resource Fairness — Ghodsi et al., NSDI 2011 (single-resource specialization here;
  DRF's strategy-proofness analysis motivates Phase 4).
- Burstable credit instances (AWS EC2 T-family) — baseline + earned-burst semantics.
- Borg/Autopilot-style reclamation of forecast-unused reservations.
- Industry LLM gateways (LiteLLM, Kong AI, Azure APIM `llm-token-limit`) — confirm static
  quotas are the deployed state of the art; none reallocate on demand forecasts.
