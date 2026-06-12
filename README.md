# token-optim

Give your org a flat AI budget. token-optim splits it across users by
demonstrated use — small guaranteed floors, one liquid pool, pool draws
prioritized by who actually uses the stuff — and pushes the result to a
LiteLLM proxy as real, enforced per-user budgets. Where no enforcement API
exists (Copilot seats), it issues per-seat verdicts instead: keep, review,
reclaim, with the decision rules printed on the report.

The first time it processed a live Copilot seat, it recommended cancelling
the subscription that had been bought to test it. The seat was unused. The
verdict was correct.

```sh
uvx --from token-optim token-optim ingest --csv usage.csv
uvx --from token-optim token-optim allocate --period 2026-06
uvx --from token-optim token-optim apply       # dry-run by default
python demo.py serve                           # seat report UI at localhost:8400
```

## The benchmark that picked the design

The original allocator forecast per-user demand and pre-assigned quotas.
Benchmarked against its own ablation (30 seeds, paired 95% CIs, 4
scenarios), the ablation won everywhere: every token moved from the
demand-revealing shared pool into a forecast-based quota allocated strictly
worse. The shipped allocator (DAFB-v2) is the rebuild around that result.

| Heavy-user unmet demand (stable scenario) | |
|---|---|
| equal split | 71.0 ± 1.6 % |
| static tiers | 52.5 ± 3.1 % |
| usage-proportional | 17.7 ± 0.9 % |
| max-min water-filling | 9.7 ± 0.8 % |
| **DAFB-v2** | **6.0 ± 0.9 %** |

Waste drops from ~60% of budget (equal split) to ~2.5%. A strategic
token-burner gains nothing (often negative); a 4× equal-share draw cap
makes the system mechanically vandalism-proof at a measured efficiency
cost. Methodology, ablations, incentive analysis, and the conditions where
v2 does *not* win: [REPORT.md](REPORT.md). Raw numbers:
[RESULTS.md](RESULTS.md). Regenerate them yourself: `python benchmark.py`.

## What's in the box

- `allocator.py` — DAFB-v2: demand-capped floors at half the equal share,
  maximal liquid pool, utilization-weighted draws, exact water-filling.
  Property-tested; budget conservation is an identity, not a tolerance.
- `ledger.py` — per-user AI spend normalized to dollars across Anthropic
  (Usage/Cost + Claude Code Analytics), GitHub Copilot billing + seats,
  LiteLLM spend logs, or any CSV. Unattributable spend is surfaced, never
  averaged away.
- `enforcement.py` — floors become LiteLLM per-user budgets; pool draws
  become capped dynamic raises; a runtime guard keeps the flat budget an
  invariant. Dry-run by default.
- `advisory.py` — seat verdicts (keep / review / reclaim) from activity
  data, plus seat-tier recommendations. The verdict rules live here once;
  the GUI and the report consume the same generated spec.
- `demo.py` — local web UI: upload an M365 Copilot usage export or a
  GitHub seats payload, review each verdict, generate a branded report.
  Processing is local; the file never leaves the machine.
- `calibrate.py` — fits the simulator to your ledger and re-runs the
  benchmark on your org's shape. Estimators self-validate against known
  synthetic ground truth.
- `gui/` — a React front-end for the seat-review workflow, styled as a
  1968 federal memo. Storybook catalog included. (`cd gui && npm install
  && npm run dev`)

## What's enforceable where

| Your setup | What token-optim can do |
|---|---|
| API traffic behind LiteLLM | Hard per-user budgets + dynamic fair-share pool |
| Anthropic / OpenAI API direct | Coarse workspace limits + per-user advisories |
| Claude Code seats, GitHub Copilot | Advisory reports + seat-tier recommendations — no per-user cap APIs exist |

Worked LiteLLM example: [INTEGRATIONS.md](INTEGRATIONS.md).

## Install

```sh
pip install token-optim    # or: uvx --from token-optim token-optim --help
```

The Python package has zero dependencies.

## Development

```sh
pytest                        # Python suite
cd gui && npx vitest run      # unit + browser-mode story tests
python benchmark.py           # regenerate RESULTS.md (~10s)
```

Formal model in [DESIGN.md](DESIGN.md). Contribution gates and house
rules: [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT.
