# Launch drafts (NOT YET POSTED — CEO presses the button)

Pre-flight checklist before any post goes live:
- [ ] Repo public on GitHub, LICENSE present
- [ ] `uv build` artifact uploaded to PyPI as `token-optim` (or adjust install
      lines to `uvx --from git+https://github.com/<org>/token-optim`)
- [ ] README renders correctly on GitHub
- [ ] All numbers double-checked against RESULTS.md

---

## Show HN

**Title options (pick one):**
1. `Show HN: We falsified our own token-allocation algorithm – the fixed version is open source`
2. `Show HN: Token-optim – fair-share AI budget autopilot for LiteLLM (with the research that killed our v1)`

**Body:**

> I wanted to answer a simple question: if your org buys a flat AI token
> budget and usage is wildly unequal (top 20% of users want ~78% of tokens),
> how should you split it so heavy users get what they need without raising
> the budget or starving each other?
>
> I built the clever version first — EWMA demand forecasting, saturation
> probing, utilization-earned quotas — and benchmarked it against its own
> ablation: plain water-filling plus a shared liquid pool. **The ablation won
> in every scenario** (paired 30-seed runs, 95% CIs). Every dollar moved from
> the demand-revealing pool into a forecast was allocated strictly worse.
>
> So the version that ships is the inverted architecture: small guaranteed
> floors (half the equal share, demand-capped), one big liquid pool, and pool
> draws prioritized by demonstrated utilization. Versus equal split it cuts
> heavy-user unmet demand from 71% to 6% and waste from ~60% of budget to
> ~2.5%. We also red-teamed it: a strategic token-burner gains nothing (the
> gaming is pure vandalism), and a 4x draw cap makes it mechanically
> vandalism-proof at a measured cost.
>
> It's an external controller for LiteLLM (floors -> per-user budgets, pool
> draws -> dynamic raises, with a runtime can't-exceed-the-budget invariant),
> plus advisory mode for the things with no enforcement API (Claude Code
> seats, Copilot — we document what's NOT controllable rather than pretend).
> Pure stdlib Python, 217 tests, every number regenerable with one command.
>
> The full falsification trail is in REPORT.md. Happy to answer anything about
> the methodology — the negative result was the most useful thing we found.

**First comment (post immediately, sets the tone):** the honest-limitations
list from INTEGRATIONS.md (poll-based draws, single proxy, synthetic-workload
calibration caveat) + "if you run an org's AI budget and want the benchmark
re-run on your real usage shape, `token-optim calibrate` does exactly that."

---

## r/LocalLLaMA

**Title:** `Open-sourced a fair-share budget allocator for LiteLLM — our fancy
forecasting lost to its own ablation, so we shipped the simple thing that won`

Short body: the table from README + quickstart + "AMA about the benchmark."

---

## LiteLLM Discord / GitHub Discussion

> Built an external budget controller on top of the /user/update API: it
> turns a flat org budget into per-user floors + a dynamic fair-share pool
> (weighted by demonstrated utilization), with dry-run plans and a hard
> invariant against exceeding the org budget. Research + benchmarks included.
> Would there be interest in tighter integration (callbacks for mid-period
> draws instead of polling)? Happy to contribute.

---

## The soft MSP funnel (append to HN first-comment ONLY if asked about
multi-tenant / client management)

> Separately exploring a managed version for MSPs (per-client branded
> right-sizing reports for Copilot/M365/Claude seats). If you run an MSP and
> want a free report on your own export, DM me.
