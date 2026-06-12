# Contributing

Issues and PRs welcome. The short version of how this repo works:

## Setup

```sh
python -m venv .venv && .venv/bin/pip install -e ".[dev]" pytest
cd gui && npm install
```

## Gates (all must be green before a PR)

```sh
pytest                      # Python suite
cd gui && npx vitest run    # unit + browser-mode story tests (+ axe)
cd gui && npm run build     # tsc + vite
```

## House rules the tests enforce

- **The stated rules live once.** `advisory.py` is the source of the
  verdict rules; `gui/src/rules-spec.json` is generated from it
  (`python3 advisory.py > gui/src/rules-spec.json`) and a drift test
  fails if they diverge. Golden vectors are mirrored verbatim between
  `test_demo.py` and `gui/src/rules.test.ts`.
- **Values never lie.** UI numbers render only from real domain
  computations; stamps render only true verdict values. Tests enforce
  this — keep it that way.
- **Cohesion gate.** Static styling lives in `gui/src/tokens.css`;
  inline `style={{...}}` is allowed only for data-driven values with an
  `inline-ok(...)` justification comment (mechanically checked).
- Deterministic everywhere: no `Math.random`/`random()` in product code —
  hashes derive any per-instance variation.
