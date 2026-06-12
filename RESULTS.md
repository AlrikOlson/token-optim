# Empirical results — DAFB vs baselines

30 seeds per scenario, 50 users, 52 periods, flat budget B = 1000000 tokens/period. All algorithms see identical latent-demand traces per seed; realized usage = min(demand, quota + buffer draw). Values are mean ± 95% CI across seeds, in percent.

## Scenario: stable

| Metric | equal_split | usage_proportional | static_tiers | max_min | dafb | dafb_v2 |
|---|---|---|---|---|---|---|
| Heavy-user unmet demand % (lower better) | 71.0 ± 1.6 | 17.7 ± 0.9 | 52.5 ± 3.1 | 9.7 ± 0.8 | 17.4 ± 0.7 | 6.0 ± 0.9 |
| Overall unmet demand % (lower better) | 55.1 ± 2.8 | 16.4 ± 0.8 | 42.6 ± 3.2 | 7.6 ± 0.7 | 15.4 ± 0.5 | 4.6 ± 0.9 |
| Budget utilization % (higher better) | 40.4 ± 2.5 | 75.2 ± 0.7 | 51.6 ± 2.8 | 83.1 ± 0.7 | 76.2 ± 0.5 | 85.9 ± 0.8 |
| Allocated-but-unused % of B (lower better) | 59.6 ± 2.5 | 24.8 ± 0.7 | 48.4 ± 2.8 | 11.7 ± 0.3 | 23.3 ± 0.5 | 2.5 ± 0.1 |
| Jain fairness of satisfaction % (higher better) | 93.0 ± 0.5 | 99.5 ± 0.0 | 96.2 ± 0.2 | 99.9 ± 0.0 | 99.6 ± 0.0 | 99.9 ± 0.0 |

Paired DAFB − baseline difference in heavy-user unmet demand (negative = DAFB better; * = 95% CI excludes 0):

- vs equal_split: -53.59 ± 1.82 pp*
- vs usage_proportional: -0.32 ± 0.68 pp
- vs static_tiers: -35.11 ± 3.15 pp*
- vs max_min: +7.66 ± 0.57 pp*
- vs dafb_v2: +11.41 ± 0.84 pp*

Budget conservation across all runs: PASS

## Scenario: adoption_ramp

| Metric | equal_split | usage_proportional | static_tiers | max_min | dafb | dafb_v2 |
|---|---|---|---|---|---|---|
| Heavy-user unmet demand % (lower better) | 77.2 ± 1.1 | 28.1 ± 1.3 | 63.3 ± 2.4 | 24.3 ± 1.4 | 33.4 ± 1.5 | 21.8 ± 1.7 |
| Overall unmet demand % (lower better) | 61.7 ± 2.2 | 28.2 ± 0.6 | 52.3 ± 2.5 | 20.4 ± 1.0 | 27.7 ± 1.0 | 16.5 ± 1.3 |
| Budget utilization % (higher better) | 42.1 ± 2.4 | 79.0 ± 0.7 | 52.5 ± 2.7 | 87.6 ± 1.1 | 79.5 ± 1.1 | 91.9 ± 1.4 |
| Allocated-but-unused % of B (lower better) | 57.9 ± 2.4 | 21.0 ± 0.7 | 47.5 ± 2.7 | 9.2 ± 0.3 | 19.7 ± 0.8 | 2.2 ± 0.1 |
| Jain fairness of satisfaction % (higher better) | 90.6 ± 0.6 | 89.2 ± 1.5 | 92.9 ± 0.5 | 98.8 ± 0.2 | 98.6 ± 0.2 | 99.3 ± 0.1 |

Paired DAFB − baseline difference in heavy-user unmet demand (negative = DAFB better; * = 95% CI excludes 0):

- vs equal_split: -43.76 ± 2.09 pp*
- vs usage_proportional: +5.27 ± 1.06 pp*
- vs static_tiers: -29.85 ± 2.82 pp*
- vs max_min: +9.08 ± 0.67 pp*
- vs dafb_v2: +11.65 ± 0.71 pp*

Budget conservation across all runs: PASS

## Scenario: all_heavy_crunch

| Metric | equal_split | usage_proportional | static_tiers | max_min | dafb | dafb_v2 |
|---|---|---|---|---|---|---|
| Heavy-user unmet demand % (lower better) | 76.7 ± 0.8 | 60.2 ± 0.6 | 70.8 ± 1.3 | 62.2 ± 0.5 | 71.9 ± 0.6 | 68.3 ± 0.5 |
| Overall unmet demand % (lower better) | 54.8 ± 0.7 | 47.0 ± 0.2 | 53.5 ± 0.5 | 46.5 ± 0.1 | 49.9 ± 0.3 | 45.1 ± 0.1 |
| Budget utilization % (higher better) | 81.4 ± 1.2 | 95.4 ± 0.3 | 83.8 ± 0.9 | 96.3 ± 0.2 | 90.2 ± 0.5 | 98.9 ± 0.1 |
| Allocated-but-unused % of B (lower better) | 18.6 ± 1.2 | 4.6 ± 0.3 | 16.2 ± 0.9 | 3.7 ± 0.2 | 9.8 ± 0.5 | 1.1 ± 0.1 |
| Jain fairness of satisfaction % (higher better) | 86.7 ± 0.3 | 95.9 ± 0.2 | 86.6 ± 0.4 | 94.8 ± 0.1 | 90.4 ± 0.3 | 91.1 ± 0.3 |

Paired DAFB − baseline difference in heavy-user unmet demand (negative = DAFB better; * = 95% CI excludes 0):

- vs equal_split: -4.76 ± 0.45 pp*
- vs usage_proportional: +11.73 ± 0.43 pp*
- vs static_tiers: +1.09 ± 1.19 pp
- vs max_min: +9.69 ± 0.35 pp*
- vs dafb_v2: +3.63 ± 0.24 pp*

Budget conservation across all runs: PASS

## Scenario: bursty

| Metric | equal_split | usage_proportional | static_tiers | max_min | dafb | dafb_v2 |
|---|---|---|---|---|---|---|
| Heavy-user unmet demand % (lower better) | 74.1 ± 1.6 | 28.7 ± 0.8 | 57.9 ± 2.9 | 21.8 ± 0.7 | 29.9 ± 0.7 | 15.5 ± 1.0 |
| Overall unmet demand % (lower better) | 59.3 ± 2.6 | 27.4 ± 0.6 | 48.7 ± 2.9 | 17.3 ± 0.7 | 27.2 ± 0.5 | 11.7 ± 1.1 |
| Budget utilization % (higher better) | 40.7 ± 2.6 | 72.6 ± 0.6 | 51.3 ± 2.9 | 82.7 ± 0.7 | 72.8 ± 0.5 | 88.3 ± 1.1 |
| Allocated-but-unused % of B (lower better) | 59.3 ± 2.6 | 27.4 ± 0.6 | 48.7 ± 2.9 | 14.8 ± 0.2 | 27.0 ± 0.4 | 3.5 ± 0.1 |
| Jain fairness of satisfaction % (higher better) | 92.0 ± 0.5 | 99.2 ± 0.1 | 95.0 ± 0.3 | 99.4 ± 0.1 | 99.2 ± 0.0 | 99.7 ± 0.0 |

Paired DAFB − baseline difference in heavy-user unmet demand (negative = DAFB better; * = 95% CI excludes 0):

- vs equal_split: -44.22 ± 1.74 pp*
- vs usage_proportional: +1.13 ± 0.59 pp*
- vs static_tiers: -28.08 ± 3.00 pp*
- vs max_min: +8.10 ± 0.43 pp*
- vs dafb_v2: +14.35 ± 0.83 pp*

Budget conservation across all runs: PASS

## σ-sweep (tail-heaviness sensitivity, stable scenario)

| sigma | dafb heavy-unmet % | equal_split | usage_proportional | max_min |
|---|---|---|---|---|
| 1.2 | 18.4 ± 0.7 | 64.8 ± 1.6 | 17.7 ± 0.9 | 9.3 ± 0.6 |
| 1.6 | 17.4 ± 0.7 | 71.0 ± 1.6 | 17.7 ± 0.9 | 9.7 ± 0.8 |
| 2.0 | 16.7 ± 0.8 | 75.1 ± 1.7 | 17.6 ± 1.0 | 10.1 ± 0.9 |

## Analysis and honest findings

**DAFB decisively beats deployed practice.** Against equal split it cuts
heavy-user unmet demand by 44-54 pp (significant) in every non-crunch scenario;
against static tiers by 28-35 pp. The slack-recycling premise of the project is
confirmed: a flat budget serves heavy users far better when light users' unused
entitlement is actively redistributed.

**But the central hypothesis is partially FALSIFIED.** The `max_min` ablation —
plain EWMA forecasts, equal weights, no floors, no saturation probing, same
liquid buffer — beats full DAFB on heavy-user unmet demand by 7.7-9.7 pp in
*every* scenario (all significant). Diagnosis: DAFB's bespoke components
(deviation headroom, probe bumps, earned weights) all *inflate pre-assigned
quotas*, which shrinks the liquid buffer; the buffer's pro-rata draw against
*realized* excess demand is demand-revealing (zero forecast error), so every
token moved from the buffer into forecast-based quotas is allocated strictly
worse. Under frictionless mid-period draws, **conservative pre-assignment plus a
large shared pool dominates clever forecasting**. The forecasting machinery
optimized the wrong stage.

**Scope caveats (why this is not yet the final word):**

1. The draw adapter is an idealized frictionless pool (instant, pro-rata,
   no races). Real draw mechanisms have friction — FCFS contention, approval
   latency, rate limits — which is exactly when guaranteed quotas regain value.
   The backlog chunk on buffer draw discipline becomes the decisive experiment.
2. Quotas have *commitment value* not measured here: a user who can see a
   guaranteed allocation can plan work; a pool grants no forward guarantee.
3. Strategic robustness is untested (Phase 4): a pool drawn by claimed excess
   may be more gameable than utilization-earned quotas.
4. `usage_proportional` also beats DAFB in ramp/crunch on heavy-unmet, but
   pays for it with the worst satisfaction-fairness in the ramp scenario
   (Jain 89.2% vs DAFB 98.6%) — it starves precisely the ramping users the
   brief cares about.

**Design implication for DAFB v2:** invert the architecture. Keep a small
guaranteed floor per user (predictability + fairness), push everything else
into the liquid pool, and let demand reveal itself through draws; apply
earned-weight discipline to *draw priority* rather than to pre-assigned quotas.

## Draw-friction sensitivity (buffer-bearing algorithms)

Heavy-user unmet demand %, mean ± 95% CI. FCFS = seeded arrival race; draw_cap = per-user pool draw capped at one equal share.

### stable

| friction | max_min | dafb | dafb_v2 | v2 − max_min (paired) |
|---|---|---|---|---|
| frictionless | 9.7 ± 0.8 | 17.4 ± 0.7 | 6.0 ± 0.9 | -3.76 ± 0.35 pp* |
| fcfs | 9.0 ± 0.8 | 17.2 ± 0.7 | 5.4 ± 0.9 | -3.57 ± 0.33 pp* |
| draw_cap | 23.9 ± 3.5 | 18.5 ± 0.8 | 59.6 ± 2.7 | +35.67 ± 1.53 pp* |

### adoption_ramp

| friction | max_min | dafb | dafb_v2 | v2 − max_min (paired) |
|---|---|---|---|---|
| frictionless | 24.3 ± 1.4 | 33.4 ± 1.5 | 21.8 ± 1.7 | -2.57 ± 0.70 pp* |
| fcfs | 21.8 ± 1.4 | 33.3 ± 1.5 | 18.7 ± 1.5 | -3.05 ± 0.50 pp* |
| draw_cap | 35.0 ± 2.7 | 34.5 ± 1.5 | 67.6 ± 1.9 | +32.61 ± 1.53 pp* |

### all_heavy_crunch

| friction | max_min | dafb | dafb_v2 | v2 − max_min (paired) |
|---|---|---|---|---|
| frictionless | 62.2 ± 0.5 | 71.9 ± 0.6 | 68.3 ± 0.5 | +6.06 ± 0.30 pp* |
| fcfs | 56.6 ± 0.6 | 71.9 ± 0.6 | 54.0 ± 0.4 | -2.59 ± 0.64 pp* |
| draw_cap | 62.2 ± 0.5 | 71.9 ± 0.6 | 68.6 ± 0.6 | +6.44 ± 0.34 pp* |

### bursty

| friction | max_min | dafb | dafb_v2 | v2 − max_min (paired) |
|---|---|---|---|---|
| frictionless | 21.8 ± 0.7 | 29.9 ± 0.7 | 15.5 ± 1.0 | -6.25 ± 0.55 pp* |
| fcfs | 19.7 ± 0.8 | 29.6 ± 0.7 | 13.7 ± 1.2 | -6.03 ± 0.60 pp* |
| draw_cap | 34.5 ± 3.0 | 30.8 ± 0.7 | 64.0 ± 2.5 | +29.54 ± 1.28 pp* |

## DAFB v2 analysis (buffer-first redesign)

v2 = demand-capped floors at half the equal share + maximal liquid pool +
utilization-earned DRAW priority (think:10). Findings:

**Under realistic draw disciplines, v2 is the best algorithm tested.**
Frictionless: v2 beats max_min significantly in stable (−3.8 pp), ramp
(−2.6 pp) and bursty (−6.3 pp) heavy-user unmet demand, with the lowest waste
of any algorithm (2.2–2.5% of B vs max_min's 9–12%), the highest utilization
(86–92%), and tied-best Jain fairness. Under an FCFS race it wins in ALL four
scenarios including crunch (−2.6 pp): its small floors mean even race losers
keep a guarantee, and the race itself is demand-revealing. The earned-weight
mechanism finally pays for itself once relocated to draw priority — the brief's
'experienced heavy users win contention' goal without the pool-shrinkage tax.

**Honest negative findings:**

1. **Structural crunch, frictionless/capped: v2 loses to max_min (+6 pp).**
   When everyone's demand exceeds the budget, weighted draws concentrate
   tokens on high-utilization users and the half-share floors are too small
   to compensate; max_min's full pre-assignment equalizes better. If an org
   expects sustained org-wide contention (demand ≈ 1.8×B), the budget itself
   is the problem — no allocator fixes structural under-provisioning.
2. **The draw_cap collapse is the decisive deployment caveat.** Capping pool
   draws at one equal share per user per period devastates v2 (+30 to +36 pp
   vs max_min) — heavy users simply cannot pull enough through the capped
   pipe, while max_min/v1 already pre-assigned them most of their demand.
   Hypothesis H2 (friction rehabilitates pre-assignment) is CONFIRMED, and
   dramatically: **the right architecture depends on the serving layer.**
   If the gateway can do uncapped (or generously capped) real-time pool
   draws, deploy v2; if overage is tightly rate-limited, deploy forecast
   pre-assignment (max_min-style water-filling).

**Deployment guidance (preliminary, pre-incentive-analysis):** v2 with
frictionless or FCFS-ish pool draws for orgs whose gateway supports real-time
shared-pool metering (LiteLLM/Kong-class proxies can); max_min water-filling
quotas where overage must be pre-approved. Phase 4 must now stress-test v2's
draw-priority weights against strategic token burning, which the draw_cap
result suggests may double as a gaming throttle.

## Incentive robustness (strategic burner/over-claimer)

A mid-tier user claims/burns up to greed × B/n per period; everyone else honest. 'gain' = Δ served true demand for the gamer vs the honest counterfactual (paired, pp); 'collateral' = Δ heavy-user unmet among honest users (pp); 'burn' = budget destroyed (%/period). Mitigation bar: draw_cap must hold dafb_v2 gain below 5 pp.

### stable

| algo | friction | greed | gain pp | collateral pp | burn % |
|---|---|---|---|---|---|
| usage_proportional | frictionless | 1x | -0.63 ± 0.69 | +0.72 ± 0.06* | 1.4 ± 0.1 |
| usage_proportional | frictionless | 2x | -0.02 ± 0.04 | +1.58 ± 0.10* | 3.3 ± 0.1 |
| usage_proportional | frictionless | 4x | +0.00 ± 0.00 | +3.31 ± 0.19* | 7.1 ± 0.1 |
| usage_proportional | draw_cap | 1x | -0.63 ± 0.69 | +0.72 ± 0.06* | 1.4 ± 0.1 |
| usage_proportional | draw_cap | 2x | -0.02 ± 0.04 | +1.58 ± 0.10* | 3.3 ± 0.1 |
| usage_proportional | draw_cap | 4x | +0.00 ± 0.00 | +3.31 ± 0.19* | 7.1 ± 0.1 |
| max_min | frictionless | 1x | +0.00 ± 0.00 | +0.57 ± 0.04* | 1.4 ± 0.1 |
| max_min | frictionless | 2x | +0.00 ± 0.00 | +1.55 ± 0.08* | 3.3 ± 0.1 |
| max_min | frictionless | 4x | +0.00 ± 0.00 | +3.83 ± 0.21* | 7.3 ± 0.1 |
| max_min | draw_cap | 1x | -0.14 ± 0.20 | +0.02 ± 0.02* | 1.4 ± 0.1 |
| max_min | draw_cap | 2x | +0.00 ± 0.00 | +0.09 ± 0.05* | 3.3 ± 0.1 |
| max_min | draw_cap | 4x | +0.00 ± 0.00 | +0.49 ± 0.19* | 7.0 ± 0.1 |
| dafb | frictionless | 1x | -0.52 ± 0.42* | +0.98 ± 0.09* | 1.4 ± 0.1 |
| dafb | frictionless | 2x | +0.00 ± 0.00 | +2.59 ± 0.20* | 3.3 ± 0.1 |
| dafb | frictionless | 4x | +0.00 ± 0.00 | +5.48 ± 0.54* | 7.1 ± 0.2 |
| dafb | draw_cap | 1x | -0.52 ± 0.42* | +0.91 ± 0.09* | 1.4 ± 0.1 |
| dafb | draw_cap | 2x | +0.00 ± 0.00 | +2.40 ± 0.19* | 3.3 ± 0.1 |
| dafb | draw_cap | 4x | +0.00 ± 0.00 | +5.18 ± 0.47* | 7.0 ± 0.2 |
| dafb_v2 | frictionless | 1x | +0.00 ± 0.00 | +0.45 ± 0.04* | 1.4 ± 0.1 |
| dafb_v2 | frictionless | 2x | +0.00 ± 0.00 | +1.25 ± 0.09* | 3.4 ± 0.1 |
| dafb_v2 | frictionless | 4x | +0.00 ± 0.00 | +3.22 ± 0.22* | 7.4 ± 0.1 |
| dafb_v2 | draw_cap | 1x | -0.47 ± 0.57 | +0.00 ± 0.00 | 1.4 ± 0.1 |
| dafb_v2 | draw_cap | 2x | -0.47 ± 0.57 | +0.00 ± 0.00 | 2.4 ± 0.1 |
| dafb_v2 | draw_cap | 4x | -0.47 ± 0.57 | +0.00 ± 0.00 | 2.4 ± 0.1 |

### bursty

| algo | friction | greed | gain pp | collateral pp | burn % |
|---|---|---|---|---|---|
| usage_proportional | frictionless | 1x | -2.63 ± 1.51* | +0.67 ± 0.06* | 1.4 ± 0.1 |
| usage_proportional | frictionless | 2x | -0.35 ± 0.38 | +1.44 ± 0.09* | 3.3 ± 0.1 |
| usage_proportional | frictionless | 4x | +0.00 ± 0.00 | +2.94 ± 0.16* | 7.1 ± 0.1 |
| usage_proportional | draw_cap | 1x | -2.63 ± 1.51* | +0.67 ± 0.06* | 1.4 ± 0.1 |
| usage_proportional | draw_cap | 2x | -0.35 ± 0.38 | +1.44 ± 0.09* | 3.3 ± 0.1 |
| usage_proportional | draw_cap | 4x | +0.00 ± 0.00 | +2.94 ± 0.16* | 7.1 ± 0.1 |
| max_min | frictionless | 1x | -0.79 ± 0.65* | +0.69 ± 0.05* | 1.4 ± 0.1 |
| max_min | frictionless | 2x | -0.18 ± 0.28 | +1.82 ± 0.08* | 3.3 ± 0.1 |
| max_min | frictionless | 4x | +0.00 ± 0.00 | +4.28 ± 0.15* | 7.2 ± 0.1 |
| max_min | draw_cap | 1x | -0.94 ± 0.83* | +0.07 ± 0.03* | 1.4 ± 0.1 |
| max_min | draw_cap | 2x | -0.21 ± 0.26 | +0.21 ± 0.09* | 3.3 ± 0.1 |
| max_min | draw_cap | 4x | +0.00 ± 0.00 | +0.73 ± 0.27* | 6.9 ± 0.1 |
| dafb | frictionless | 1x | -3.50 ± 1.54* | +0.87 ± 0.12* | 1.4 ± 0.1 |
| dafb | frictionless | 2x | -0.49 ± 0.58 | +2.30 ± 0.22* | 3.3 ± 0.1 |
| dafb | frictionless | 4x | -0.01 ± 0.02 | +4.46 ± 0.48* | 7.0 ± 0.3 |
| dafb | draw_cap | 1x | -3.49 ± 1.54* | +0.80 ± 0.11* | 1.4 ± 0.1 |
| dafb | draw_cap | 2x | -0.49 ± 0.58 | +2.09 ± 0.21* | 3.3 ± 0.1 |
| dafb | draw_cap | 4x | -0.00 ± 0.00 | +4.20 ± 0.47* | 6.9 ± 0.3 |
| dafb_v2 | frictionless | 1x | +0.00 ± 0.00 | +0.73 ± 0.04* | 1.4 ± 0.1 |
| dafb_v2 | frictionless | 2x | +0.00 ± 0.00 | +2.00 ± 0.12* | 3.3 ± 0.1 |
| dafb_v2 | frictionless | 4x | +0.00 ± 0.00 | +4.78 ± 0.30* | 7.2 ± 0.2 |
| dafb_v2 | draw_cap | 1x | -2.13 ± 1.44* | +0.00 ± 0.00 | 1.4 ± 0.1 |
| dafb_v2 | draw_cap | 2x | -2.13 ± 1.44* | +0.00 ± 0.00 | 2.4 ± 0.1 |
| dafb_v2 | draw_cap | 4x | -2.13 ± 1.44* | +0.00 ± 0.00 | 2.4 ± 0.1 |

### Incentive analysis

1. **Gaming yields the gamer nothing.** Across every algorithm, friction, and
   greed level, the strategic user's served TRUE demand gain is ≈0 pp — and
   often significantly negative (down to −3.5 pp): under slack-recycling
   allocators a mid-tier user is already near-fully served, and burning
   displaces their own real work during bursts. The use-it-or-lose-it gambit
   has no payoff; burning is pure vandalism, not rational strategy.
2. **But vandalism hurts everyone else.** Collateral on honest heavy users
   reaches +5.5 pp (dafb v1, 4x greed) and a single 4x burner destroys ~7% of
   the org budget per period. The threat model is misuse, not strategy.
3. **The mitigation bar is exceeded.** draw_cap holds dafb_v2's gaming gain
   far below the stated 5 pp (gain ≤ 0), and stronger: it drives v2's
   collateral to exactly +0.00 pp with burn capped at 2.4%/period — bounded
   floors plus capped draws mechanically limit any one user's extraction to
   floor + cap. max_min under the same cap still leaks +0.5-0.7 pp because
   its forecast-grown quotas are unbounded.
4. **The honest tension:** the same draw cap that makes v2 vandalism-proof
   costs honest heavy users ~30 pp service (see friction tables). The cap
   multiplier is the org's efficiency-vs-immunity dial; sweeping intermediate
   caps (2-4x equal share) is recorded as future work.
