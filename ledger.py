"""Provider-agnostic usage ledger for token-optim.

Normalizes per-user AI usage from heterogeneous providers into one schema
with DOLLARS as the common unit — Copilot meters premium requests, Anthropic
meters tokens, gateways meter spend; only cost normalizes across them
(think:18). The ledger feeds DAFBv2Allocator directly: the allocator is
unit-agnostic, so a dollar budget works unchanged.

Adapter pattern: each provider gets a pure `parse_<provider>(payload)`
function (fixture-tested, no network) plus an optional `fetch_*` helper that
performs the live HTTP call behind an env-var credential. Payload schemas
are BEST-EFFORT reconstructions of the public docs as of June 2026 — the
fixtures in test_ledger.py encode our assumptions; validating them against
live APIs is op-5 scope.

Known provider gaps (documented constraints, not bugs):
  * GitHub Copilot: per-user premium-request usage is not reliably available
    via REST for organizations (community discussions #184208, navikt/copilot
    #111). Aggregate-only line items are recorded with user=None and surface
    via Ledger.unattributed().
  * Claude Code Analytics per-user costs are estimates, per Anthropic docs.
"""

from __future__ import annotations

import csv
import io
import json
import os
import urllib.request
from collections import defaultdict
from dataclasses import dataclass

UNIT_TYPES = ("tokens", "premium_requests", "requests", "usd", "unknown")


@dataclass(frozen=True)
class UsageRecord:
    """One user's usage of one provider in one period, normalized to USD."""

    user: str | None          # None = aggregate row (unattributable)
    period: str                # ISO month 'YYYY-MM' (or any consistent key)
    provider: str
    cost_usd: float
    raw_units: float = 0.0
    unit_type: str = "usd"

    def __post_init__(self):
        if self.cost_usd < 0:
            raise ValueError(f"negative cost: {self.cost_usd}")
        if self.unit_type not in UNIT_TYPES:
            raise ValueError(f"unknown unit_type: {self.unit_type}")
        if not self.period:
            raise ValueError("period must be non-empty")


class Ledger:
    """Append-only collection of UsageRecords with dollar aggregation."""

    def __init__(self, records: list[UsageRecord] | None = None):
        self.records: list[UsageRecord] = []
        if records:
            self.extend(records)

    def add(self, record: UsageRecord) -> None:
        self.records.append(record)

    def extend(self, records: list[UsageRecord]) -> None:
        for r in records:
            self.add(r)

    def users(self) -> list[str]:
        return sorted({r.user for r in self.records if r.user is not None})

    def periods(self) -> list[str]:
        return sorted({r.period for r in self.records})

    def providers(self) -> list[str]:
        return sorted({r.provider for r in self.records})

    def usage_by_period(self) -> dict[str, dict[str, float]]:
        """{period: {user: total cost_usd}} — multiple providers sum."""
        out: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for r in self.records:
            if r.user is not None:
                out[r.period][r.user] += r.cost_usd
        return {p: dict(u) for p, u in out.items()}

    def per_user_period(self, period: str) -> dict[str, float]:
        """Allocator-ready usage dict for one period (USD)."""
        return self.usage_by_period().get(period, {})

    def unattributed(self) -> dict[str, float]:
        """{period: cost} that could not be attributed to a user — the
        Copilot org gap, surfaced rather than silently dropped."""
        out: dict[str, float] = defaultdict(float)
        for r in self.records:
            if r.user is None:
                out[r.period] += r.cost_usd
        return dict(out)

    # ------------------------------------------------------------- CSV I/O

    CSV_FIELDS = ("user", "period", "provider", "cost_usd", "raw_units",
                  "unit_type")

    def to_csv(self) -> str:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=self.CSV_FIELDS)
        w.writeheader()
        for r in self.records:
            w.writerow({"user": r.user if r.user is not None else "",
                        "period": r.period, "provider": r.provider,
                        "cost_usd": repr(r.cost_usd),
                        "raw_units": repr(r.raw_units),
                        "unit_type": r.unit_type})
        return buf.getvalue()

    @classmethod
    def from_csv(cls, text: str) -> "Ledger":
        records = []
        for row in csv.DictReader(io.StringIO(text)):
            records.append(UsageRecord(
                user=row["user"] or None,
                period=row["period"],
                provider=row["provider"],
                cost_usd=float(row["cost_usd"]),
                raw_units=float(row.get("raw_units") or 0.0),
                unit_type=row.get("unit_type") or "usd",
            ))
        return cls(records)


# ----------------------------------------------------- activity (Graph)


@dataclass(frozen=True)
class CopilotActivity:
    """Per-user Copilot ACTIVITY from the Microsoft Graph usage reports
    export (getMicrosoft365CopilotUsageUserDetail). Graph exposes per-app
    last-activity dates, not token costs — activity is the right signal for
    seat right-sizing anyway."""

    user: str
    days_since_last_activity: int | None   # None = never active
    active_apps: int                        # apps with activity <= window
    apps_ever_used: int
    apps_tracked: bool = True               # False: source has no per-app data
    source: str = "m365_copilot"


def parse_graph_copilot_activity(csv_text: str,
                                 active_window_days: int = 30
                                 ) -> list[CopilotActivity]:
    """Parse the Graph Copilot usage user-detail CSV export.

    Column handling is suffix-based ('... Last Activity Date') to tolerate
    Microsoft adding apps; recency is computed against the 'Report Refresh
    Date' column so reports parse identically whenever they were downloaded.
    """
    import datetime

    rows = list(csv.DictReader(io.StringIO(csv_text)))
    out = []
    for row in rows:
        upn = (row.get("User Principal Name") or row.get("user principal name")
               or row.get("UPN"))
        if not upn:
            continue
        refresh = _parse_date(row.get("Report Refresh Date", ""))
        # The bare 'Last Activity Date' column is the OVERALL recency;
        # per-app columns are '<App> ... Last Activity Date'. Both end with
        # the same suffix, so app counting must exclude the bare column.
        all_dates, app_dates = [], []
        for col, val in row.items():
            if not col or not val:
                continue
            name = col.strip()
            if name.endswith("Last Activity Date"):
                d = _parse_date(val)
                if d:
                    all_dates.append(d)
                    if name != "Last Activity Date":
                        app_dates.append(d)
        if not all_dates or refresh is None:
            out.append(CopilotActivity(user=upn, days_since_last_activity=None,
                                       active_apps=0,
                                       apps_ever_used=len(app_dates)))
            continue
        days_since = (refresh - max(all_dates)).days
        active = sum(1 for d in app_dates
                     if (refresh - d).days <= active_window_days)
        out.append(CopilotActivity(user=upn,
                                   days_since_last_activity=max(0, days_since),
                                   active_apps=active,
                                   apps_ever_used=len(app_dates)))
    return out


def _parse_date(s: str):
    import datetime
    try:
        return datetime.date.fromisoformat(s.strip()[:10])
    except (ValueError, AttributeError):
        return None


def parse_github_copilot_seats(payload: dict, as_of: str
                               ) -> list[CopilotActivity]:
    """GitHub Copilot seats API (GET /orgs/{org}/copilot/billing/seats):
    per-seat assignee.login + last_activity_at + last_activity_editor.

    This is the per-user ACTIVITY signal GitHub does expose (distinct from
    the org per-user premium-request spend gap documented at the top of this
    module). No per-app breakdown exists, so apps_tracked=False — verdict
    rules must not require multi-app evidence from this source.

    `as_of` is the reference date (ISO) — pass today's date for live pulls,
    a fixed date in tests.
    """
    ref = _parse_date(as_of)
    if ref is None:
        raise ValueError(f"invalid as_of date: {as_of!r}")
    out = []
    for seat in payload.get("seats", []):
        login = (seat.get("assignee") or {}).get("login")
        if not login:
            continue
        last = _parse_date(seat.get("last_activity_at") or "")
        if last is None:
            out.append(CopilotActivity(user=login,
                                       days_since_last_activity=None,
                                       active_apps=0, apps_ever_used=0,
                                       apps_tracked=False,
                                       source="github_copilot"))
        else:
            days = max(0, (ref - last).days)
            out.append(CopilotActivity(user=login,
                                       days_since_last_activity=days,
                                       active_apps=1 if days <= 30 else 0,
                                       apps_ever_used=1,
                                       apps_tracked=False,
                                       source="github_copilot"))
    return out


# ---------------------------------------------------------------- parsers
# Pure functions: documented-schema payload -> list[UsageRecord].


def parse_anthropic_cost(payload: dict, period: str) -> list[UsageRecord]:
    """Anthropic Usage & Cost API (Admin API) cost report.

    Assumed shape (platform.claude.com usage-cost-api, June 2026): top-level
    'data' = time buckets, each with 'results' carrying a grouping key
    (api key / workspace / user attribution where configured) and 'amount'
    in USD. We attribute by the 'description'/'workspace_id'/'user' field
    when present, else record as unattributed.
    """
    records = []
    for bucket in payload.get("data", []):
        for result in bucket.get("results", []):
            user = (result.get("user") or result.get("api_key_name")
                    or result.get("workspace_id"))
            amount = float(result.get("amount", 0.0))
            records.append(UsageRecord(
                user=user, period=period, provider="anthropic",
                cost_usd=amount, raw_units=amount, unit_type="usd"))
    return records


def parse_claude_code_analytics(payload: dict, period: str) -> list[UsageRecord]:
    """Claude Code Analytics API: per-user (actor) daily metrics including
    'estimated_cost' (cents or USD — we assume a USD float field
    'estimated_cost_usd'; estimates per Anthropic docs)."""
    records = []
    for actor in payload.get("data", []):
        email = actor.get("actor_email") or actor.get("actor_id")
        cost = float(actor.get("estimated_cost_usd", 0.0))
        tokens = float(actor.get("total_tokens", 0.0))
        records.append(UsageRecord(
            user=email, period=period, provider="claude_code",
            cost_usd=cost, raw_units=tokens, unit_type="tokens"))
    return records


def parse_copilot_billing(payload: dict, period: str) -> list[UsageRecord]:
    """GitHub enhanced billing platform usage report, filtered to Copilot
    SKUs (usage-based billing since June 1, 2026). Line items carry
    'netAmount' (USD) and, when GitHub attributes them, a 'username'.
    Org-level reports may omit per-user attribution (documented gap) —
    those rows become unattributed records."""
    records = []
    for item in payload.get("usageItems", []):
        sku = item.get("sku", "")
        if "copilot" not in sku.lower():
            continue
        records.append(UsageRecord(
            user=item.get("username"),
            period=period, provider="copilot",
            cost_usd=float(item.get("netAmount", 0.0)),
            raw_units=float(item.get("quantity", 0.0)),
            unit_type="premium_requests"))
    return records


def parse_litellm_spend(payload: list, period: str) -> list[UsageRecord]:
    """LiteLLM /spend/logs (or /user daily activity) rows: 'user' (or
    'end_user') and 'spend' in USD, 'total_tokens'."""
    records = []
    for row in payload:
        user = row.get("user") or row.get("end_user")
        records.append(UsageRecord(
            user=user, period=period, provider="litellm",
            cost_usd=float(row.get("spend", 0.0)),
            raw_units=float(row.get("total_tokens", 0.0)),
            unit_type="tokens"))
    return records


# ------------------------------------------------------- live fetch helpers
# Thin, untested-by-CI wrappers; credentials via env vars. Schema validation
# against live responses is op-5 scope.


def _get_json(url: str, headers: dict[str, str]):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_anthropic_cost(period: str, starting_at: str, ending_at: str):
    """Requires ANTHROPIC_ADMIN_KEY (an Admin API key, not a regular key)."""
    key = os.environ["ANTHROPIC_ADMIN_KEY"]
    payload = _get_json(
        "https://api.anthropic.com/v1/organizations/cost_report"
        f"?starting_at={starting_at}&ending_at={ending_at}",
        {"x-api-key": key, "anthropic-version": "2023-06-01"})
    return parse_anthropic_cost(payload, period)


def fetch_copilot_billing(org: str, year: int, month: int, period: str):
    """Requires GITHUB_TOKEN with org billing scope."""
    token = os.environ["GITHUB_TOKEN"]
    payload = _get_json(
        f"https://api.github.com/organizations/{org}/settings/billing/usage"
        f"?year={year}&month={month}",
        {"Authorization": f"Bearer {token}",
         "Accept": "application/vnd.github+json"})
    return parse_copilot_billing(payload, period)


def fetch_litellm_spend(base_url: str, period: str, start: str, end: str):
    """Requires LITELLM_MASTER_KEY."""
    key = os.environ["LITELLM_MASTER_KEY"]
    payload = _get_json(
        f"{base_url}/spend/logs?start_date={start}&end_date={end}",
        {"Authorization": f"Bearer {key}"})
    return parse_litellm_spend(payload, period)


def _get_text(url: str, headers: dict[str, str]) -> str:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


# -------------------------------------------- connector core (pv-4a)
# Fixture-testable adapters: pass `getter` in tests; the live path (env
# credentials) is exercised only in pv-4's live-tenant work.


def fetch_graph_copilot_user_detail(period: str = "D90",
                                    getter=None) -> str:
    """M365 Copilot usage user-detail CSV via Graph reports.

    Live path requires GRAPH_TOKEN with Reports.Read.All. Returns CSV text
    consumable by parse_graph_copilot_activity. NOTE: if the tenant's
    report-anonymization setting is on (the default), the CSV arrives
    pseudonymized — detect with demo.looks_pseudonymized.
    """
    url = ("https://graph.microsoft.com/v1.0/reports/"
           f"getMicrosoft365CopilotUsageUserDetail(period='{period}')")
    if getter is None:
        token = os.environ["GRAPH_TOKEN"]
        return _get_text(url, {"Authorization": f"Bearer {token}"})
    return getter(url)


def fetch_github_copilot_seats(org: str, getter=None) -> dict:
    """All Copilot seats for an org, paginated and merged into one payload
    consumable by parse_github_copilot_seats.

    Live path requires GITHUB_TOKEN (org admin / manage_billing:copilot).
    """
    base = f"https://api.github.com/orgs/{org}/copilot/billing/seats"
    if getter is None:
        token = os.environ["GITHUB_TOKEN"]
        headers = {"Authorization": f"Bearer {token}",
                   "Accept": "application/vnd.github+json"}
        getter = lambda u: _get_json(u, headers)  # noqa: E731
    seats: list = []
    page = 1
    total = 0
    while True:
        payload = getter(f"{base}?per_page=100&page={page}")
        total = payload.get("total_seats", 0)
        batch = payload.get("seats", [])
        seats.extend(batch)
        if not batch or len(seats) >= total:
            break
        page += 1
    return {"total_seats": total, "seats": seats}
