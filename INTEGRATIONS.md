# Integrations

## LiteLLM (hard enforcement — the full experience)

**How it actually works (no magic):** token-optim is an *external controller*,
not an in-process LiteLLM plugin. On a schedule (cron), it reads spend, runs
the allocation, and drives LiteLLM's budget API (`POST /user/update`) over
HTTP. LiteLLM remains the enforcement plane; token-optim decides the numbers.

### Worked example

1. Run LiteLLM with a master key and per-user budgets enabled:

```sh
docker run -p 4000:4000 -e LITELLM_MASTER_KEY=sk-master \
  ghcr.io/berriai/litellm:main-latest --config litellm-config.yaml
```

2. `token-optim.json`:

```json
{
  "budget": 5000.0,
  "cap_multiplier": 4.0,
  "providers": ["litellm"],
  "litellm": {"enabled": true, "base_url": "http://localhost:4000"}
}
```

3. Monthly loop (cron-able):

```sh
export LITELLM_MASTER_KEY=sk-master
token-optim ingest   --csv spend-2026-05.csv     # or fetch_litellm_spend
token-optim allocate --period 2026-05
token-optim apply                                 # DRY-RUN: prints the plan
token-optim apply --yes                           # actually patches budgets
```

Dry-run output looks like:

```
DRY-RUN (pass --yes to apply): 3 budget mutations
  alice                          max_budget $833.33 / 30d
  bob                            max_budget $145.20 / 30d
  cara                           max_budget $12.75 / 30d
```

Floors are set at period start; mid-period overage raises come from the shared
pool in earned-priority order, cumulatively capped at `cap_multiplier ×` the
equal share (default 4× — the knee of the measured efficiency/abuse curve, see
REPORT.md §4). A runtime invariant guarantees promised budgets + remaining
pool never exceed your flat budget.

```sh
token-optim reconcile --proxy-csv litellm-spend.csv --period 2026-05
```

reports drift between org-wide spend and what the proxy metered (out-of-band
spend shrinks the remaining pool so the org total stays true).

**Known limitations (honest list):**
- Poll-based: draws happen when the loop runs, not per-request.
- Assumes `max_budget` can be raised mid-`budget_duration` (true per LiteLLM
  docs as of June 2026; validate against your version).
- One proxy per config; multi-proxy federation is not built.

## Anthropic API (direct) / Claude Code

- **Telemetry:** `ledger.py` parses the Admin Usage & Cost API and the Claude
  Code Analytics API (per-user estimated costs). Live fetch behind
  `ANTHROPIC_ADMIN_KEY`.
- **Enforcement:** workspace-level spend limits only — token-optim emits the
  workspace-limit push plus per-user advisories and Claude Code **seat-tier
  recommendations** (Pro vs Max 5x vs Max 20x by forecast demand). There is no
  per-user cap API; we say so instead of pretending.

## GitHub Copilot

- **Telemetry:** billing usage report parsing (usage-based billing, June 2026),
  with org-level rows that lack per-user attribution surfaced explicitly via
  `Ledger.unattributed()` — a documented platform gap, not a bug here.
- **Enforcement:** org budget recommendation only.

## Anything else

Export a CSV with `user, period, provider, cost_usd, raw_units, unit_type` and
`token-optim ingest` takes it from there.
