"""Tier-A enforcement adapter: DAFBv2 Allocation -> LiteLLM budget mutations.

Maps the buffer-first architecture onto LiteLLM proxy's per-user budget
surface (June 2026 API: POST /user/update with user_id / max_budget /
budget_duration; budgets are USD):

  floors      -> per-user base budgets (max_budget = floor for the period)
  liquid pool -> NOT pre-assigned; mid-period draws raise individual budgets
                 in earned-weight priority via weighted water-filling
  cap dial    -> per-user cumulative draw cap = cap_multiplier x equal share

Org invariant enforced here, not just in simulation: the sum of all budget
promises (floors + cumulative raises) never exceeds the flat budget B.

Dry-run is the DEFAULT: plans are inspectable BudgetMutation lists and apply()
makes no network calls until dry_run=False. The transport is injectable so
tests run against a recorder, never the network.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field

from allocator import Allocation, water_fill


@dataclass(frozen=True)
class BudgetMutation:
    """One planned change to the proxy's budget state."""

    op: str            # 'set_budget' | 'raise_budget'
    user: str
    amount_usd: float  # set: the new max_budget; raise: the increment
    reason: str = ""

    def __post_init__(self):
        if self.op not in ("set_budget", "raise_budget"):
            raise ValueError(f"unknown op: {self.op}")
        if self.amount_usd < 0:
            raise ValueError("amount must be non-negative")


def urllib_transport(base_url: str, api_key: str | None = None):
    """Default live transport. Tests inject a recorder instead."""
    key = api_key or os.environ.get("LITELLM_MASTER_KEY", "")

    def transport(method: str, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            base_url.rstrip("/") + path,
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    return transport


@dataclass
class LiteLLMEnforcer:
    """Drives a LiteLLM proxy from DAFBv2 allocations.

    Lifecycle per period: start_period(allocation) -> [mid-period
    plan_draws(...) as overage requests arrive] -> reconcile(...) against
    the ledger before the next period.
    """

    transport: object                      # callable(method, path, payload)
    budget: float                          # flat org budget B for the period
    cap_multiplier: float = 4.0            # the calibrated default dial
    budget_duration: str = "30d"
    dry_run: bool = True
    pool_remaining: float = field(default=0.0, init=False)
    promised: dict[str, float] = field(default_factory=dict, init=False)
    drawn: dict[str, float] = field(default_factory=dict, init=False)
    applied_log: list[BudgetMutation] = field(default_factory=list, init=False)

    # ------------------------------------------------------------- planning

    def start_period(self, allocation: Allocation) -> list[BudgetMutation]:
        """Plan base budgets = floors; arm the pool. Returns the plan."""
        self.pool_remaining = allocation.buffer
        self.promised = dict(allocation.quotas)
        self.drawn = {u: 0.0 for u in allocation.quotas}
        plan = [BudgetMutation("set_budget", u, q,
                               reason=f"period floor (forecast-capped)")
                for u, q in sorted(allocation.quotas.items())]
        self._check_invariant()
        return plan

    def plan_draws(self, excess_requests: dict[str, float],
                   allocation: Allocation) -> list[BudgetMutation]:
        """Mid-period overage: distribute pool by earned-weight water-fill,
        capped per user at cap_multiplier x equal share cumulative."""
        users = [u for u in allocation.quotas if excess_requests.get(u, 0) > 0]
        if not users or self.pool_remaining <= 0:
            return []
        n = len(allocation.quotas)
        cap = self.cap_multiplier * self.budget / n
        weights = [allocation.weights.get(u, 1.0) for u in users]
        capped = [min(max(0.0, excess_requests[u]),
                      max(0.0, cap - self.drawn.get(u, 0.0))) for u in users]
        grants = water_fill(capped, weights, self.pool_remaining)
        plan = []
        for u, g in zip(users, grants):
            if g <= 0:
                continue
            self.pool_remaining -= g
            self.drawn[u] = self.drawn.get(u, 0.0) + g
            self.promised[u] = self.promised.get(u, 0.0) + g
            plan.append(BudgetMutation(
                "raise_budget", u, g,
                reason=f"pool draw (weight {allocation.weights.get(u, 1.0):.2f})"))
        self._check_invariant()
        return plan

    def _check_invariant(self) -> None:
        total = sum(self.promised.values()) + self.pool_remaining
        if total > self.budget * (1 + 1e-9):
            raise RuntimeError(
                f"flat-budget invariant violated: promised+pool {total:.2f} "
                f"> B {self.budget:.2f}")

    # -------------------------------------------------------------- apply

    def apply(self, plan: list[BudgetMutation]) -> list[dict]:
        """Execute a plan against the proxy. In dry-run, returns the would-be
        calls without touching the transport."""
        calls = []
        for m in plan:
            if m.op == "set_budget":
                payload = {"user_id": m.user, "max_budget": round(m.amount_usd, 6),
                           "budget_duration": self.budget_duration}
            else:  # raise_budget: new max = current promise (already updated)
                payload = {"user_id": m.user,
                           "max_budget": round(self.promised[m.user], 6),
                           "budget_duration": self.budget_duration}
            call = {"method": "POST", "path": "/user/update", "payload": payload}
            calls.append(call)
            if not self.dry_run:
                self.transport("POST", "/user/update", payload)
                self.applied_log.append(m)
        return calls

    # ----------------------------------------------------------- reconcile

    def reconcile(self, ledger_spend: dict[str, float],
                  proxy_spend: dict[str, float],
                  tolerance_usd: float = 1.0) -> dict:
        """Compare org-wide ledger spend vs what the proxy metered.

        Out-of-band spend (ledger > proxy: direct API keys, other providers)
        does not consume proxy budgets but DOES consume the org's real
        budget — so it shrinks what the pool can still safely promise.
        """
        drift = {}
        out_of_band = 0.0
        for u in set(ledger_spend) | set(proxy_spend):
            delta = ledger_spend.get(u, 0.0) - proxy_spend.get(u, 0.0)
            if abs(delta) > tolerance_usd:
                drift[u] = delta
            if delta > 0:
                out_of_band += delta
        pool_adjustment = min(self.pool_remaining, out_of_band)
        self.pool_remaining -= pool_adjustment
        return {"drift": drift, "out_of_band_usd": out_of_band,
                "pool_reduced_by": pool_adjustment,
                "pool_remaining": self.pool_remaining}
