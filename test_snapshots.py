"""Tests for the connector core: snapshot store (append-only, sealed
immutability, round-trip), per-product seat costs, fixture-tested fetch
adapters. No live API calls anywhere."""

import json

import pytest

from advisory import SeatRecommendation, activity_recommendations
from demo import Brand, render_report
from ledger import (CopilotActivity, fetch_github_copilot_seats,
                    fetch_graph_copilot_user_detail)
from snapshots import (PRODUCT_SEAT_COST_DEFAULTS, Client, PeriodSnapshot,
                       SealedSnapshotError, SnapshotStore)

RECS = (
    SeatRecommendation("a@x.com", "keep", "active", 0.0, "m365"),
    SeatRecommendation("b@x.com", "reclaim", "never used Copilot", 30.0, "m365"),
    SeatRecommendation("dev1", "reclaim", "inactive 80 days", 19.0, "github"),
)


# ----------------------------------------------------------- snapshot store

def make_store(tmp_path):
    store = SnapshotStore(tmp_path / "snaps")
    store.save_client(Client(id="contoso", name="Contoso Ltd"))
    return store


def test_client_roundtrip_and_default_costs(tmp_path):
    store = make_store(tmp_path)
    c = store.load_client("contoso")
    assert c.name == "Contoso Ltd"
    assert c.seat_costs == PRODUCT_SEAT_COST_DEFAULTS
    assert [x.id for x in store.clients()] == ["contoso"]


def test_snapshot_roundtrip_preserves_recs_and_savings(tmp_path):
    store = make_store(tmp_path)
    snap = PeriodSnapshot("contoso", "2026-06", RECS)
    store.save_draft(snap)
    back = store.load("contoso", "2026-06")
    assert back.recs == RECS
    assert back.savings_usd == pytest.approx(49.0)  # 30 m365 + 19 github
    assert not back.sealed


def test_drafts_rewritable_until_sealed(tmp_path):
    store = make_store(tmp_path)
    store.save_draft(PeriodSnapshot("contoso", "2026-06", RECS[:1]))
    store.save_draft(PeriodSnapshot("contoso", "2026-06", RECS))  # ok
    sealed = store.seal("contoso", "2026-06", sealed_at="2026-06-30T12:00:00Z")
    assert sealed.sealed and sealed.sealed_at == "2026-06-30T12:00:00Z"
    # Sealed is forever: draft writes, re-seals, and sneaky pre-sealed
    # snapshots all raise.
    with pytest.raises(SealedSnapshotError):
        store.save_draft(PeriodSnapshot("contoso", "2026-06", RECS[:1]))
    with pytest.raises(SealedSnapshotError):
        store.seal("contoso", "2026-06")
    with pytest.raises(SealedSnapshotError):
        store.save_draft(PeriodSnapshot("contoso", "2026-07", RECS, sealed=True))


def test_history_is_chronological_and_sealed_only(tmp_path):
    store = make_store(tmp_path)
    for period in ("2026-04", "2026-03", "2026-05"):
        store.save_draft(PeriodSnapshot("contoso", period, RECS))
        store.seal("contoso", period, sealed_at=f"{period}-28T00:00:00Z")
    store.save_draft(PeriodSnapshot("contoso", "2026-06", RECS))  # unsealed
    hist = store.history("contoso")
    assert [s.period for s in hist] == ["2026-03", "2026-04", "2026-05"]
    assert all(s.sealed for s in hist)  # QBR/history can't see drafts
    assert [s.period for s in store.history("contoso", sealed_only=False)][-1] == "2026-06"


def test_bad_period_rejected(tmp_path):
    store = make_store(tmp_path)
    with pytest.raises(ValueError):
        store.save_draft(PeriodSnapshot("contoso", "June 2026", RECS))


# ------------------------------------------------------- per-product costs

def test_product_flows_ledger_to_advisory_to_report():
    acts = [CopilotActivity(user="dev1", days_since_last_activity=None,
                            active_apps=0, apps_ever_used=0, apps_tracked=False)]
    gh_recs = activity_recommendations(
        acts, PRODUCT_SEAT_COST_DEFAULTS["github"], product="github")
    assert gh_recs[0].product == "github"
    assert gh_recs[0].monthly_saving_usd == 19.0
    m365_recs = activity_recommendations(acts, 30.0)  # default product
    assert m365_recs[0].product == "m365"
    # Mixed-product report shows the product glyphs; single-product doesn't.
    mixed = render_report(gh_recs + m365_recs, Brand())
    assert "ⓖ" in mixed and "Ⓜ" in mixed
    single = render_report(m365_recs, Brand())
    assert "Ⓜ" not in single


# --------------------------------------------------------- fetch adapters

def test_graph_fetch_adapter_uses_injected_getter():
    urls = []
    csv = "User Principal Name,Report Refresh Date\nu@x.com,2026-06-01\n"
    out = fetch_graph_copilot_user_detail(period="D90",
                                          getter=lambda u: urls.append(u) or csv)
    assert out == csv
    assert "getMicrosoft365CopilotUsageUserDetail(period='D90')" in urls[0]


def test_github_seats_adapter_paginates_and_merges():
    pages = {
        1: {"total_seats": 3, "seats": [{"assignee": {"login": "a"}},
                                        {"assignee": {"login": "b"}}]},
        2: {"total_seats": 3, "seats": [{"assignee": {"login": "c"}}]},
    }
    calls = []

    def getter(url):
        page = int(url.split("page=")[-1])
        calls.append(page)
        return pages[page]

    merged = fetch_github_copilot_seats("acme", getter=getter)
    assert merged["total_seats"] == 3
    assert [s["assignee"]["login"] for s in merged["seats"]] == ["a", "b", "c"]
    assert calls == [1, 2]  # stopped exactly when complete


def test_github_seats_adapter_handles_empty_org():
    merged = fetch_github_copilot_seats(
        "empty", getter=lambda u: {"total_seats": 0, "seats": []})
    assert merged == {"total_seats": 0, "seats": []}


def test_snapshot_json_is_stable_on_disk(tmp_path):
    """The on-disk shape is part of the moat contract — pin it."""
    store = make_store(tmp_path)
    store.save_draft(PeriodSnapshot("contoso", "2026-06", RECS[:1]))
    raw = json.loads((tmp_path / "snaps" / "contoso" / "2026-06.json").read_text())
    assert raw["period"] == "2026-06"
    assert raw["recs"][0] == {"user": "a@x.com", "verdict": "keep",
                              "reason": "active", "monthly_saving_usd": 0.0,
                              "product": "m365"}
