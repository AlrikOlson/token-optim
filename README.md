# token-optim

**Fair-share AI budget autopilot.** Give your org a flat AI budget; token-optim
splits it across users the way the data says works — small guaranteed floors,
one big liquid pool, and pool draws prioritized by demonstrated use — and pushes
the result to your LiteLLM proxy as real, enforced per-user budgets.

```sh
uvx --from token-optim token-optim ingest --csv usage.csv
uvx --from token-optim token-optim allocate --period 2026-06
uvx --from token-optim token-optim apply          # dry-run by default
```

## We falsified our own algorithm, and the replacement is what ships

This started as a research question: *how should a flat token budget be split
across users whose demand is wildly unequal?* We built the clever thing first —
EWMA demand forecasting, saturation probing, utilization-earned quotas — and
benchmarked it against its own ablation (30 seeds, paired 95% CIs, 4 scenarios).

**The ablation won.** Every token moved from a demand-revealing shared pool into
a forecast-based quota was allocated strictly worse. So we inverted the
architecture, and that version — DAFB-v2 — beat everything:

| Heavy-user unmet demand (stable scenario) | |
|---|---|
| equal split | 71.0 ± 1.6 % |
| static tiers (industry practice) | 52.5 ± 3.1 % |
| usage-proportional | 17.7 ± 0.9 % |
| max-min water-filling | 9.7 ± 0.8 % |
| **DAFB-v2 (this tool)** | **6.0 ± 0.9 %** |

Waste drops from ~60% of budget (equal split) to ~2.5%. A strategic
token-burner gains *nothing* (often negative) while a 4× equal-share draw cap
makes the system mechanically vandalism-proof at a measured efficiency cost.
Full methodology, ablations, incentive analysis, and the honest failure
boundary: [REPORT.md](REPORT.md), raw numbers in [RESULTS.md](RESULTS.md).

## What it does

- **Ledger** (`ledger.py`) — normalizes per-user AI spend to dollars across
  Anthropic (Usage/Cost + Claude Code Analytics APIs), GitHub Copilot billing,
  LiteLLM spend logs, or any CSV. Unattributable spend is surfaced, never
  silently averaged away.
- **Allocator** (`allocator.py`) — DAFB-v2: demand-capped floors at half the
  equal share, maximal liquid pool, utilization-weighted pool draws, exact
  water-filling. 217-test property suite (budget conservation is an identity,
  not a tolerance).
- **Enforcement** (`enforcement.py`) — pushes floors as LiteLLM per-user
  budgets and pool draws as capped dynamic raises, with a runtime guard that
  the flat budget can never be exceeded. Dry-run by default.
- **Advisory** (`advisory.py`) — where hard enforcement is impossible (Claude
  Code seats, Copilot), generates per-user reports and seat-tier
  recommendations instead, with the data-quality caveats stated.
- **Calibration** (`calibrate.py`) — fits the simulator to *your* ledger and
  re-runs the benchmark on your org's shape. The estimators self-validate by
  recovering known synthetic ground truth.

## What's enforceable where (the honest tier table)

| Your setup | What token-optim can do |
|---|---|
| API traffic behind LiteLLM | **Hard per-user budgets + dynamic fair-share pool** |
| Anthropic / OpenAI API direct | Coarse workspace/project limits + per-user advisories |
| Claude Code seats, GitHub Copilot | Advisory reports + seat-tier recommendations (no per-user cap APIs exist — we say so rather than pretend) |

See [INTEGRATIONS.md](INTEGRATIONS.md) for the worked LiteLLM example.

## Install

```sh
pip install token-optim        # or: uvx --from token-optim token-optim --help
```

Pure Python, stdlib only, no dependencies.

## Development

```sh
uv run --with pytest python -m pytest -q     # 217 tests
python benchmark.py                          # regenerate RESULTS.md (~10s)
```

`DESIGN.md` has the formal model; `ROADMAP.md` is a generated project view.

## License

MIT.
