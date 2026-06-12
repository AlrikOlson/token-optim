"""token-optim CLI — the periodic ingest -> allocate -> apply -> report loop.

Usage (cron-friendly; each subcommand is a separate invocation):

    token-optim ingest   --config CONFIG --csv usage.csv
    token-optim allocate --config CONFIG --period 2026-06
    token-optim apply    --config CONFIG [--yes]
    token-optim report   --config CONFIG --period 2026-06 [--out report.md]
    token-optim simulate --config CONFIG

Safety: `apply` without --yes is a pure dry-run and never constructs a live
transport — the plan is printed, nothing is sent. State (per-user EWMAs +
the pending allocation) persists as JSON between invocations, and observing
a period is idempotent.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from advisory import advisory_report, coarse_pushes
from allocator import Allocation, DAFBv2Allocator
from enforcement import LiteLLMEnforcer, urllib_transport
from ledger import Ledger

DEFAULT_CONFIG = {
    "budget": 10000.0,           # USD per period
    "floor_frac": 0.5,
    "cap_multiplier": 4.0,       # the calibrated dial (REPORT.md §4)
    "alpha": 0.3,
    "w_min": 0.25,
    "ledger_csv": "ledger.csv",
    "state_path": "token-optim-state.json",
    "providers": ["litellm"],
    "litellm": {"enabled": False, "base_url": "http://localhost:4000"},
    "claude_code_current_plans": {},
}


def load_config(path: str) -> dict:
    cfg = dict(DEFAULT_CONFIG)
    with open(path) as f:
        user_cfg = json.load(f)
    unknown = set(user_cfg) - set(DEFAULT_CONFIG)
    if unknown:
        raise SystemExit(f"unknown config keys: {sorted(unknown)}")
    cfg.update(user_cfg)
    if cfg["budget"] <= 0:
        raise SystemExit("budget must be positive")
    return cfg


def load_ledger(cfg: dict) -> Ledger:
    path = cfg["ledger_csv"]
    if not os.path.exists(path):
        return Ledger()
    with open(path) as f:
        return Ledger.from_csv(f.read())


# ----------------------------------------------------------------- state


def load_state(cfg: dict) -> dict:
    if os.path.exists(cfg["state_path"]):
        with open(cfg["state_path"]) as f:
            return json.load(f)
    return {"users": {}, "observed_periods": [], "allocation": None}


def save_state(cfg: dict, state: dict) -> None:
    with open(cfg["state_path"], "w") as f:
        json.dump(state, f, indent=2)


def build_allocator(cfg: dict, state: dict, users: list[str]) -> DAFBv2Allocator:
    alloc = DAFBv2Allocator(budget=cfg["budget"], alpha=cfg["alpha"],
                            floor_frac=cfg["floor_frac"], w_min=cfg["w_min"])
    for u in users:
        alloc.add_user(u)
    for u, s in state["users"].items():
        if u in alloc.users:
            alloc.users[u].mean = s["mean"]
            alloc.users[u].utilization = s["utilization"]
            alloc.users[u].has_history = s["has_history"]
    return alloc


def allocator_state(alloc: DAFBv2Allocator) -> dict:
    return {u: {"mean": s.mean, "utilization": s.utilization,
                "has_history": s.has_history}
            for u, s in alloc.users.items()}


def allocation_to_dict(a: Allocation) -> dict:
    return {"quotas": a.quotas, "buffer": a.buffer, "forecasts": a.forecasts,
            "floors": a.floors, "weights": a.weights}


def allocation_from_dict(d: dict) -> Allocation:
    return Allocation(quotas=d["quotas"], buffer=d["buffer"],
                      forecasts=d["forecasts"], floors=d["floors"],
                      weights=d["weights"])


# ------------------------------------------------------------ subcommands


def cmd_ingest(cfg: dict, args) -> int:
    with open(args.csv) as f:
        incoming = Ledger.from_csv(f.read())
    existing = load_ledger(cfg)
    existing.extend(incoming.records)
    with open(cfg["ledger_csv"], "w") as f:
        f.write(existing.to_csv())
    print(f"ingested {len(incoming.records)} records "
          f"({len(existing.records)} total) into {cfg['ledger_csv']}")
    return 0


def cmd_allocate(cfg: dict, args) -> int:
    ledger = load_ledger(cfg)
    state = load_state(cfg)
    usage = ledger.per_user_period(args.period)
    if not usage:
        print(f"no attributed usage for period {args.period}", file=sys.stderr)
        return 1
    users = sorted(set(usage) | set(state["users"]))
    alloc = build_allocator(cfg, state, users)

    if args.period not in state["observed_periods"]:
        # Observe against the previous allocation's quotas when available so
        # utilization is measured against what was actually granted.
        prev = (allocation_from_dict(state["allocation"])
                if state["allocation"] else alloc.allocate())
        alloc.observe(usage, prev)
        state["observed_periods"].append(args.period)
    else:
        print(f"period {args.period} already observed; allocating from state")

    a = alloc.allocate()
    state["users"] = allocator_state(alloc)
    state["allocation"] = allocation_to_dict(a)
    save_state(cfg, state)

    print(f"allocation for next period (B = ${cfg['budget']:,.0f}):")
    for u in sorted(a.quotas):
        print(f"  {u:30s} floor ${a.quotas[u]:>10.2f}  "
              f"forecast ${a.forecasts[u]:>10.2f}  w {a.weights[u]:.2f}")
    print(f"  {'POOL (shared, on demand)':30s} ${a.buffer:>16.2f}")
    return 0


def cmd_apply(cfg: dict, args) -> int:
    state = load_state(cfg)
    if not state["allocation"]:
        print("no allocation in state; run `allocate` first", file=sys.stderr)
        return 1
    a = allocation_from_dict(state["allocation"])

    for push in coarse_pushes(a, [p for p in cfg["providers"]
                                  if p != "litellm"]):
        marker = "PUSH" if push.executable else "NO-OP"
        amount = f" ${push.amount_usd:,.0f}" if push.amount_usd else ""
        print(f"[{marker}] {push.provider}: {push.action}{amount} — "
              f"{push.explanation}")

    if not cfg["litellm"]["enabled"]:
        print("litellm disabled in config; nothing to enforce")
        return 0

    live = bool(args.yes)
    # Without --yes the transport is a stub that must never be called.
    transport = (urllib_transport(cfg["litellm"]["base_url"]) if live
                 else _refusing_transport)
    enf = LiteLLMEnforcer(transport=transport, budget=cfg["budget"],
                          cap_multiplier=cfg["cap_multiplier"],
                          dry_run=not live)
    plan = enf.start_period(a)
    calls = enf.apply(plan)
    mode = "APPLIED" if live else "DRY-RUN (pass --yes to apply)"
    print(f"{mode}: {len(calls)} budget mutations")
    for c in calls:
        p = c["payload"]
        print(f"  {p['user_id']:30s} max_budget ${p['max_budget']:.2f} "
              f"/ {p['budget_duration']}")
    return 0


def _refusing_transport(method, path, payload):  # pragma: no cover
    raise RuntimeError("dry-run transport must never be called")


def cmd_report(cfg: dict, args) -> int:
    state = load_state(cfg)
    if not state["allocation"]:
        print("no allocation in state; run `allocate` first", file=sys.stderr)
        return 1
    report = advisory_report(
        load_ledger(cfg), allocation_from_dict(state["allocation"]),
        args.period, cfg["budget"],
        current_plans=cfg["claude_code_current_plans"] or None)
    if args.out:
        with open(args.out, "w") as f:
            f.write(report)
        print(f"wrote {args.out}")
    else:
        print(report)
    return 0


def cmd_simulate(cfg: dict, args) -> int:
    """Counterfactual replay on the org's own ledger: DAFB-v2 vs equal split.

    CAVEAT (printed): observed usage is a CENSORED proxy for demand — users
    capped by today's policy could not show what they would have used, so
    this comparison UNDERSTATES v2's advantage. Full calibration is op-5.
    """
    ledger = load_ledger(cfg)
    periods = ledger.periods()
    if len(periods) < 2:
        print("need >=2 periods of ledger history to simulate", file=sys.stderr)
        return 1
    users = ledger.users()
    n = len(users)
    alloc = DAFBv2Allocator(budget=cfg["budget"], alpha=cfg["alpha"],
                            floor_frac=cfg["floor_frac"], w_min=cfg["w_min"])
    for u in users:
        alloc.add_user(u)
    served_v2 = served_eq = demand_total = 0.0
    for period in periods:
        usage = ledger.per_user_period(period)
        a = alloc.allocate()
        for u in users:
            d = usage.get(u, 0.0)
            demand_total += d
            served_v2 += min(d, a.quotas[u] + a.buffer * (1.0 / n))
            served_eq += min(d, cfg["budget"] / n)
        alloc.observe(usage, a)
    print("counterfactual replay on your ledger "
          f"({len(periods)} periods, {n} users, B=${cfg['budget']:,.0f}):")
    print(f"  served demand: dafb_v2 {100 * served_v2 / demand_total:.1f}% "
          f"vs equal split {100 * served_eq / demand_total:.1f}%")
    print("  CAVEAT: observed usage is censored by your current policy; "
          "this understates v2's advantage. Run op-5 calibration for "
          "rigorous numbers.")
    return 0


def cmd_calibrate(cfg: dict, args) -> int:
    """Fit simulator parameters to the org's own ledger and re-run the
    core benchmark on the calibrated scenario (op-5a machinery; running it
    on REAL exported telemetry is the op-5 act)."""
    from calibrate import calibrated_benchmark, fit_parameters

    ledger = load_ledger(cfg)
    try:
        params = fit_parameters(ledger, cfg["budget"])
    except ValueError as e:
        print(f"cannot calibrate: {e}", file=sys.stderr)
        return 1
    for line in calibrated_benchmark(params, cfg["budget"], seeds=args.seeds):
        print(line)
    return 0


def cmd_reconcile(cfg: dict, args) -> int:
    """Compare org-wide ledger spend vs proxy-metered spend for a period."""
    state = load_state(cfg)
    if not state["allocation"]:
        print("no allocation in state; run `allocate` first", file=sys.stderr)
        return 1
    with open(args.proxy_csv) as f:
        proxy = Ledger.from_csv(f.read()).per_user_period(args.period)
    org = load_ledger(cfg).per_user_period(args.period)
    a = allocation_from_dict(state["allocation"])
    enf = LiteLLMEnforcer(transport=_refusing_transport, budget=cfg["budget"],
                          cap_multiplier=cfg["cap_multiplier"], dry_run=True)
    enf.start_period(a)
    report = enf.reconcile(org, proxy)
    print(f"reconciliation for {args.period}:")
    if report["drift"]:
        for u, d in sorted(report["drift"].items()):
            print(f"  {u:30s} ledger-proxy drift ${d:+.2f}")
    else:
        print("  no per-user drift beyond tolerance")
    print(f"  out-of-band spend ${report['out_of_band_usd']:.2f} -> "
          f"pool reduced by ${report['pool_reduced_by']:.2f} "
          f"(remaining ${report['pool_remaining']:.2f})")
    return 0


# ------------------------------------------------------------------ main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="token-optim")
    parser.add_argument("--config", default="token-optim.json")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="append a usage CSV into the ledger")
    p.add_argument("--csv", required=True)

    p = sub.add_parser("allocate", help="observe a period and allocate the next")
    p.add_argument("--period", required=True)

    p = sub.add_parser("apply", help="push the allocation to enforcement surfaces")
    p.add_argument("--yes", action="store_true",
                   help="actually apply (default: dry-run)")

    p = sub.add_parser("report", help="write the advisory report")
    p.add_argument("--period", required=True)
    p.add_argument("--out")

    sub.add_parser("simulate", help="counterfactual replay on your own ledger")

    p = sub.add_parser("calibrate",
                       help="fit simulator params to your ledger, re-run benchmark")
    p.add_argument("--seeds", type=int, default=30)

    p = sub.add_parser("reconcile", help="ledger vs proxy spend drift report")
    p.add_argument("--proxy-csv", required=True)
    p.add_argument("--period", required=True)

    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    return {"ingest": cmd_ingest, "allocate": cmd_allocate,
            "apply": cmd_apply, "report": cmd_report,
            "simulate": cmd_simulate, "calibrate": cmd_calibrate,
            "reconcile": cmd_reconcile}[args.command](cfg, args)


if __name__ == "__main__":
    raise SystemExit(main())
