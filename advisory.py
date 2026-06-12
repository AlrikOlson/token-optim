"""Advisory mode for providers without per-user hard enforcement.

Tier taxonomy (think:18): gateway-fronted traffic gets hard enforcement
(enforcement.py); provider-direct APIs get coarse limits; seat products
(Claude Code subscriptions, GitHub Copilot) get ADVICE. This module is the
advice: per-user allocation advisories, seat-tier recommendations under a
stated cost model, and coarse-limit push actions where an API exists —
with explanatory no-ops where one does not.

Partial visibility is handled explicitly (think:21): spend the ledger could
not attribute to a user is shown per provider in a Data Quality section and
recommendations are qualified accordingly — never silently averaged away.
"""

from __future__ import annotations

from dataclasses import dataclass

from allocator import Allocation
from ledger import CopilotActivity, Ledger


@dataclass(frozen=True)
class SeatPlan:
    """One subscription tier. included_value_usd approximates the
    API-equivalent consumption the plan supports per month."""

    name: str
    price_usd: float
    included_value_usd: float


# June 2026 public pricing defaults (Pro $20, Max 5x $100, Max 20x $200);
# included values derived from the 5x/20x multiplier language relative to
# Pro (~$50 API-equivalent). A COST MODEL, not ground truth — pass your own.
CLAUDE_CODE_PLANS = (
    SeatPlan("pro", 20.0, 50.0),
    SeatPlan("max_5x", 100.0, 250.0),
    SeatPlan("max_20x", 200.0, 1000.0),
)


def recommend_seat(forecast_usd: float,
                   plans: tuple[SeatPlan, ...] = CLAUDE_CODE_PLANS) -> tuple[SeatPlan, str]:
    """Cheapest plan whose included value covers the forecast demand."""
    for plan in sorted(plans, key=lambda p: p.price_usd):
        if forecast_usd <= plan.included_value_usd:
            return plan, f"forecast ${forecast_usd:.0f} fits {plan.name}"
    top = max(plans, key=lambda p: p.included_value_usd)
    return top, (f"forecast ${forecast_usd:.0f} exceeds every plan; "
                 f"{top.name} + API overflow")


# ----------------------------------------------- activity-based mode
# Graph Copilot reports expose ACTIVITY, not cost (think:31). For seat
# right-sizing activity is the better signal anyway: a seat is wasted when
# nobody uses it, regardless of token volume. Rules are deliberately simple
# and are PRINTED in every report — no black box in front of a client.

ACTIVITY_RULES = (
    ("keep", "Active in the last 14 days (across 2+ apps, where app-level "
             "data exists — M365; GitHub Copilot reports activity only)"),
    ("review", "Last activity 15-45 days ago, or single-app use where "
               "app-level data exists"),
    ("reclaim", "No Copilot activity in 45+ days (or never)"),
)

# The numeric law behind the prose above. This module is THE source of the
# stated rules; gui/src/rules-spec.json is GENERATED from rules_spec()
# (`python3 advisory.py`) and a pytest drift gate keeps the artifact honest
# (gui-1b convergence — rules.ts no longer hand-mirrors these numbers).
RULE_THRESHOLDS = {
    "reclaim_after_days": 45,   # inactive longer than this -> reclaim
    "review_after_days": 14,    # inactive longer than this -> review
    "single_app_max": 1,        # tracked apps at or below this -> review
}


def rules_spec() -> dict:
    """The stated activity rules as one machine-readable spec."""
    return {
        "version": 1,
        "thresholds": dict(RULE_THRESHOLDS),
        "stated": [{"verdict": v, "description": d} for v, d in ACTIVITY_RULES],
    }


@dataclass(frozen=True)
class SeatRecommendation:
    user: str
    verdict: str        # 'keep' | 'review' | 'reclaim'
    reason: str
    monthly_saving_usd: float
    product: str = "m365"   # 'm365' | 'github' — seat costs differ per product


def activity_recommendations(activities: list[CopilotActivity],
                             seat_cost_usd: float = 30.0,
                             product: str = "m365"
                             ) -> list[SeatRecommendation]:
    """Stated-rule seat verdicts from Graph activity data."""
    recs = []
    for a in activities:
        if a.days_since_last_activity is None:
            recs.append(SeatRecommendation(
                a.user, "reclaim", "never used Copilot", seat_cost_usd,
                product))
        elif a.days_since_last_activity > RULE_THRESHOLDS["reclaim_after_days"]:
            recs.append(SeatRecommendation(
                a.user, "reclaim",
                f"inactive {a.days_since_last_activity} days", seat_cost_usd,
                product))
        elif (a.days_since_last_activity > RULE_THRESHOLDS["review_after_days"]
              or (a.apps_tracked
                  and a.active_apps <= RULE_THRESHOLDS["single_app_max"])):
            recs.append(SeatRecommendation(
                a.user, "review",
                (f"last active {a.days_since_last_activity}d ago"
                 + (f", {a.active_apps} app(s) in the last month"
                    if a.apps_tracked else "")), 0.0, product))
        else:
            recs.append(SeatRecommendation(
                a.user, "keep",
                (f"active, {a.active_apps} apps in the last month"
                 if a.apps_tracked else
                 f"active {a.days_since_last_activity}d ago"), 0.0, product))
    return recs


def projected_savings(recs: list[SeatRecommendation]) -> float:
    return sum(r.monthly_saving_usd for r in recs)


@dataclass(frozen=True)
class CoarsePush:
    """A coarse limit action — either executable or an explanatory no-op."""

    provider: str
    action: str          # 'set_workspace_spend_limit' | 'set_org_budget' | 'noop'
    amount_usd: float | None
    explanation: str

    @property
    def executable(self) -> bool:
        return self.action != "noop"


def coarse_pushes(allocation: Allocation, providers: list[str]) -> list[CoarsePush]:
    """Per-provider coarse limit actions for one period.

    The pushable total is floors + pool (= B): coarse surfaces cannot
    distinguish users, so the only honest hard number is the org budget.
    """
    total = sum(allocation.quotas.values()) + allocation.buffer
    out = []
    for p in providers:
        if p == "anthropic":
            out.append(CoarsePush(
                "anthropic", "set_workspace_spend_limit", total,
                "Anthropic Admin API supports workspace-level spend limits; "
                "per-user caps are not available — workspace limit set to "
                "the org budget."))
        elif p == "copilot":
            out.append(CoarsePush(
                "copilot", "set_org_budget", total,
                "GitHub billing budgets are org/SKU-level under June 2026 "
                "usage-based billing."))
        elif p == "claude_code":
            out.append(CoarsePush(
                "claude_code", "noop", None,
                "Claude Code seat plans expose no per-user or workspace "
                "spend-limit API; use the seat-tier recommendations below."))
        else:
            out.append(CoarsePush(
                p, "noop", None,
                f"No known limit API for provider '{p}'; advisory only."))
    return out


def advisory_report(ledger: Ledger, allocation: Allocation, period: str,
                    budget: float,
                    plans: tuple[SeatPlan, ...] = CLAUDE_CODE_PLANS,
                    current_plans: dict[str, str] | None = None) -> str:
    """Markdown advisory report for one period."""
    spend = ledger.per_user_period(period)
    equal_share = budget / max(1, len(allocation.quotas))
    cc_users = {r.user for r in ledger.records
                if r.provider == "claude_code" and r.user}

    lines = [f"# token-optim advisory — {period}",
             "",
             f"Flat budget B = ${budget:,.0f}. Floors are guaranteed; the pool "
             f"(${allocation.buffer:,.0f}) is shared on demand by earned "
             "priority. Arrows compare forecast demand to the equal share.",
             "",
             "## Per-user allocation",
             "",
             "| user | observed $ | floor $ | forecast $ | draw weight | trend |",
             "|---|---|---|---|---|---|"]
    for u in sorted(allocation.quotas):
        f = allocation.forecasts.get(u, 0.0)
        arrow = "↑" if f > equal_share * 1.2 else (
            "↓" if f < equal_share * 0.5 else "→")
        lines.append(f"| {u} | {spend.get(u, 0.0):.2f} | "
                     f"{allocation.quotas[u]:.2f} | {f:.2f} | "
                     f"{allocation.weights.get(u, 1.0):.2f} | {arrow} |")

    if cc_users:
        lines += ["", "## Claude Code seat-tier recommendations",
                  "",
                  "Cost model: " + ", ".join(
                      f"{p.name} ${p.price_usd:.0f}/mo ≈ "
                      f"${p.included_value_usd:.0f} value"
                      for p in plans),
                  "",
                  "| user | forecast $ | recommended | note | monthly delta $ |",
                  "|---|---|---|---|---|"]
        for u in sorted(cc_users & set(allocation.quotas)):
            plan, note = recommend_seat(allocation.forecasts.get(u, 0.0), plans)
            delta = ""
            if current_plans and u in current_plans:
                cur = next((p for p in plans if p.name == current_plans[u]), None)
                if cur:
                    delta = f"{plan.price_usd - cur.price_usd:+.0f}"
            lines.append(f"| {u} | {allocation.forecasts.get(u, 0.0):.2f} | "
                         f"{plan.name} | {note} | {delta} |")

    unattributed = ledger.unattributed()
    lines += ["", "## Data quality"]
    if unattributed.get(period, 0.0) > 0:
        per_provider: dict[str, float] = {}
        for r in ledger.records:
            if r.user is None and r.period == period:
                per_provider[r.provider] = (per_provider.get(r.provider, 0.0)
                                            + r.cost_usd)
        lines.append("")
        lines.append(f"**${unattributed[period]:,.2f} of spend in {period} "
                     "could not be attributed to a user** and is EXCLUDED "
                     "from the table above. Per-user recommendations are "
                     "correspondingly incomplete for these providers:")
        for p, amt in sorted(per_provider.items()):
            lines.append(f"- {p}: ${amt:,.2f} unattributed")
    else:
        lines.append("")
        lines.append("All spend in this period is attributed to users.")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    # Emit the rules spec — regenerate the GUI artifact with:
    #   python3 advisory.py > gui/src/rules-spec.json
    import json
    print(json.dumps(rules_spec(), indent=2))
