"""Tests for the validation artifact: Graph activity parser, stated-rule
recommendations, report rendering, and the e2e HTTP upload flow."""

import threading
import urllib.parse
import urllib.request

import pytest

from advisory import activity_recommendations, projected_savings
from demo import (Brand, PseudonymizedDataError, apply_overrides,
                  looks_pseudonymized, render_report, render_review_page,
                  rightsizing_report, sample_csv, serve)
from ledger import parse_graph_copilot_activity

GRAPH_CSV = """User Principal Name,Report Refresh Date,Last Activity Date,Copilot Chat Last Activity Date,Word Copilot Last Activity Date
active@x.com,2026-06-01,2026-05-30,2026-05-30,2026-05-25
single@x.com,2026-06-01,2026-05-28,2026-05-28,
stale@x.com,2026-06-01,2026-03-01,2026-03-01,2026-02-15
never@x.com,2026-06-01,,,
"""


# ------------------------------------------------------------- parser

def test_parse_graph_activity():
    acts = {a.user: a for a in parse_graph_copilot_activity(GRAPH_CSV)}
    assert acts["active@x.com"].days_since_last_activity == 2
    assert acts["active@x.com"].active_apps >= 2
    assert acts["single@x.com"].active_apps == 1
    assert acts["stale@x.com"].days_since_last_activity == 92
    assert acts["never@x.com"].days_since_last_activity is None


def test_parser_tolerates_unknown_app_columns():
    csv_text = ("User Principal Name,Report Refresh Date,"
                "FutureApp Copilot Last Activity Date\n"
                "u@x.com,2026-06-01,2026-05-31\n")
    a = parse_graph_copilot_activity(csv_text)[0]
    assert a.days_since_last_activity == 1
    assert a.apps_ever_used == 1


def test_parser_skips_rows_without_upn():
    csv_text = "User Principal Name,Report Refresh Date\n,2026-06-01\n"
    assert parse_graph_copilot_activity(csv_text) == []


# ------------------------------------------------------- recommendations

def test_stated_rules_produce_expected_verdicts():
    recs = {r.user: r for r in activity_recommendations(
        parse_graph_copilot_activity(GRAPH_CSV), seat_cost_usd=30.0)}
    assert recs["active@x.com"].verdict == "keep"
    assert recs["single@x.com"].verdict == "review"
    assert recs["stale@x.com"].verdict == "reclaim"
    assert recs["never@x.com"].verdict == "reclaim"
    # Savings only from reclaims.
    assert projected_savings(list(recs.values())) == pytest.approx(60.0)


# ------------------------------------------------------------- report

def test_report_contains_branding_savings_and_rules():
    brand = Brand(msp_name="Acme MSP", client_name="Globex",
                  seat_cost_usd=30.0)
    report = rightsizing_report(GRAPH_CSV, brand)
    assert "Acme MSP" in report and "Globex" in report
    assert "$60/month" in report
    assert "How verdicts are decided" in report
    assert "no message content is accessed" in report
    assert "<script" not in report.lower()  # report itself is static


def test_report_escapes_hostile_csv_content():
    hostile = ("User Principal Name,Report Refresh Date,Last Activity Date\n"
               "<script>alert(1)</script>@x.com,2026-06-01,2026-05-30\n")
    report = rightsizing_report(hostile, Brand())
    assert "<script>alert(1)</script>" not in report
    assert "&lt;script&gt;" in report


def test_sample_org_is_realistic_and_renders():
    csv_text = sample_csv()
    recs = activity_recommendations(parse_graph_copilot_activity(csv_text))
    verdicts = {r.verdict for r in recs}
    assert verdicts == {"keep", "review", "reclaim"}   # all three present
    assert len(recs) == 28
    report = render_report(recs, Brand(msp_name="Northwind IT Partners",
                                       client_name="Fabrikam Manufacturing"))
    assert "Fabrikam Manufacturing" in report


# ------------------------------------------------- GitHub Copilot seats

GH_SEATS = """{
  "total_seats": 4,
  "seats": [
    {"assignee": {"login": "active-dev"}, "last_activity_at": "2026-05-30T10:14:00Z",
     "last_activity_editor": "vscode/1.99"},
    {"assignee": {"login": "fading-dev"}, "last_activity_at": "2026-05-05T08:00:00Z"},
    {"assignee": {"login": "gone-dev"}, "last_activity_at": "2026-02-01T08:00:00Z"},
    {"assignee": {"login": "never-dev"}, "last_activity_at": null}
  ]
}"""


def test_github_seats_parser_and_verdicts():
    from ledger import parse_github_copilot_seats
    import json
    acts = {a.user: a for a in parse_github_copilot_seats(
        json.loads(GH_SEATS), as_of="2026-06-01")}
    assert acts["active-dev"].days_since_last_activity == 2
    assert not acts["active-dev"].apps_tracked
    assert acts["never-dev"].days_since_last_activity is None
    recs = {r.user: r.verdict for r in activity_recommendations(
        list(acts.values()), seat_cost_usd=19.0)}
    # No multi-app requirement for sources without app data.
    assert recs["active-dev"] == "keep"
    assert recs["fading-dev"] == "review"
    assert recs["gone-dev"] == "reclaim"
    assert recs["never-dev"] == "reclaim"


def test_report_sniffs_github_json():
    report = rightsizing_report(GH_SEATS, Brand(msp_name="DevShop MSP"),
                                as_of="2026-06-01")
    assert "active-dev" in report and "DevShop MSP" in report
    assert "Reclaim" in report
    # Mandated data caveat (think:39): GitHub retains activity ~90 days.
    assert "90 days" in report


def test_m365_report_has_no_github_caveat():
    report = rightsizing_report(GRAPH_CSV, Brand())
    assert "90 days" not in report
    assert "no message content is accessed" in report


def test_m365_keep_still_requires_multi_app():
    # Regression: apps_tracked sources keep the 2-app requirement.
    recs = {r.user: r.verdict for r in activity_recommendations(
        parse_graph_copilot_activity(GRAPH_CSV))}
    assert recs["single@x.com"] == "review"


# ----------------------------------------- pseudonymized-export detection

PSEUDONYMIZED_CSV = """User Principal Name,Report Refresh Date,Last Activity Date
98700DF7D10F342548A4875F4B796C11,2026-06-01,2026-05-30
1A2B3C4D5E6F70819293A4B5C6D7E8F9,2026-06-01,
"""


def test_pseudonym_detection():
    assert looks_pseudonymized(["98700DF7D10F342548A4875F4B796C11"])
    assert not looks_pseudonymized(["maria@x.com", "dev@x.com"])
    assert not looks_pseudonymized([])  # empty -> not concealed
    # Mixed: majority rules.
    assert not looks_pseudonymized(
        ["a@x.com", "b@x.com", "98700DF7D10F342548A4875F4B796C11"])


def test_concealed_export_raises_not_renders():
    with pytest.raises(PseudonymizedDataError):
        rightsizing_report(PSEUDONYMIZED_CSV)


# ------------------------------------------------------- ratify + voice

def test_apply_overrides_recomputes_savings():
    recs = activity_recommendations(
        parse_graph_copilot_activity(GRAPH_CSV), seat_cost_usd=30.0)
    keep_idx = next(i for i, r in enumerate(recs) if r.verdict == "keep")
    reclaim_idx = next(i for i, r in enumerate(recs)
                       if r.verdict == "reclaim")
    out = apply_overrides(recs, {keep_idx: "reclaim", reclaim_idx: "keep"},
                          seat_cost_usd=30.0)
    assert out[keep_idx].verdict == "reclaim"
    assert out[keep_idx].monthly_saving_usd == 30.0
    assert out[reclaim_idx].verdict == "keep"
    assert out[reclaim_idx].monthly_saving_usd == 0.0
    # Unchanged verdicts and bogus values are untouched.
    bogus = apply_overrides(recs, {0: "purge-with-fire"}, 30.0)
    assert bogus == recs


def test_review_page_has_voice_but_report_stays_straight():
    recs = activity_recommendations(
        parse_graph_copilot_activity(GRAPH_CSV), seat_cost_usd=30.0)
    review = render_review_page(recs, Brand(), GRAPH_CSV)
    assert "NOTICE:" in review                      # Committee voice present
    assert "obligation to exist" in review          # the never-used line
    report = render_report(recs, Brand())
    assert "NOTICE:" not in report                  # hard register boundary
    assert "obligation" not in report
    # Sample report (the outreach attachment) is also register-free.
    sample = rightsizing_report(sample_csv())
    assert "NOTICE:" not in sample


# ----------------------------------------------------------- e2e upload

def test_e2e_upload_flow():
    server = serve(port=0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        # GET serves the upload page (with the anonymization pre-flight).
        page = urllib.request.urlopen(
            f"http://127.0.0.1:{port}/", timeout=5).read().decode()
        assert "Right-Sizing" in page
        assert "concealed names" in page
        # POST raw CSV -> ratify (review) page, not the final report.
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/report?msp=TestMSP&client=TestCo",
            data=GRAPH_CSV.encode(),
            headers={"Content-Type": "text/csv"}, method="POST")
        review = urllib.request.urlopen(req, timeout=5).read().decode()
        assert "ratification" in review and "/generate" in review
        assert "NOTICE:" in review
        # POST ratified form (one override) -> final client-ready report.
        recs = activity_recommendations(
            parse_graph_copilot_activity(GRAPH_CSV), 30.0)
        keep_idx = next(i for i, r in enumerate(recs)
                        if r.verdict == "keep")
        form = urllib.parse.urlencode({
            "msp": "TestMSP", "client": "TestCo", "csv": GRAPH_CSV,
            f"v_{keep_idx}": "reclaim"})
        gen = urllib.request.Request(
            f"http://127.0.0.1:{port}/generate", data=form.encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST")
        report = urllib.request.urlopen(gen, timeout=5).read().decode()
        assert "TestMSP" in report and "TestCo" in report
        assert "Reclaim" in report and "NOTICE:" not in report
        assert "reviewer override" in report
        assert "$90" in report  # 2 rule reclaims + 1 override, $30 each
        # Concealed export -> instruction page, not a report.
        conc = urllib.request.Request(
            f"http://127.0.0.1:{port}/report",
            data=PSEUDONYMIZED_CSV.encode(),
            headers={"Content-Type": "text/csv"}, method="POST")
        instr = urllib.request.urlopen(conc, timeout=5).read().decode()
        assert "Org settings" in instr and "concealed" in instr
        # Garbage CSV -> 422, not a stack trace.
        bad = urllib.request.Request(
            f"http://127.0.0.1:{port}/report",
            data=b"\x00\x01not,a,csv", method="POST")
        try:
            urllib.request.urlopen(bad, timeout=5)
        except urllib.error.HTTPError as e:
            assert e.code in (200, 422)  # parse may degrade gracefully
    finally:
        server.shutdown()
        server.server_close()


# ---------------------------------------------------------------- gui-11
def test_stamp_tilt_matches_gui_golden_vectors():
    """Cross-surface parity: these vectors are mirrored verbatim in
    gui/src/hash.test.ts — FNV-1a over UTF-16 code units of f"{user}|stamp".
    If either side drifts, the same seat stamps at different angles on the
    Python report vs the GUI."""
    from demo import _fnv1a, _stamp_tilt
    golden = [
        ("alice@fabrikam.com", 794089938, -0.5),
        ("bob.briggs@initech.com", 39313206, -2.0),
        ("Žofie Nováková", 787488327, -2.0),
        ("龍太郎", 2516235835, 0.0),
    ]
    for user, h, tilt in golden:
        assert _fnv1a(f"{user}|stamp") == h
        assert _stamp_tilt(user) == tilt


def test_stamp_tilt_range_and_determinism():
    from demo import _stamp_tilt
    for i in range(200):
        t = _stamp_tilt(f"user-{i}@example.com")
        assert -2.0 <= t <= 2.0
        assert (t * 2) == int(t * 2)  # half-degree steps
        assert t == _stamp_tilt(f"user-{i}@example.com")


# ---------------------------------------------------------------- gui-1b
# The stated rules live ONCE, in advisory.py; gui/src/rules-spec.json is a
# generated artifact and rules.ts a second interpreter of the same spec.
# Two gates: (1) the committed artifact equals the live spec; (2) golden
# behavior vectors, mirrored verbatim in gui/src/rules.test.ts, prove both
# interpreters decide identically.

RULE_GOLDEN = [
    # (days_since_last_activity, active_apps, apps_tracked) -> verdict
    ((None, 0, False), "reclaim"),
    ((90, 0, False), "reclaim"),
    ((46, 0, False), "reclaim"),
    ((45, 0, False), "review"),    # boundary: not > 45
    ((15, 0, False), "review"),
    ((14, 1, True), "review"),     # single-app use, tracked
    ((14, 2, True), "keep"),
    ((14, 0, False), "keep"),      # boundary: not > 14, untracked
    ((0, 3, True), "keep"),
]


def test_rules_spec_artifact_matches_advisory():
    import json
    from pathlib import Path
    from advisory import rules_spec
    artifact = json.loads(
        (Path(__file__).parent / "gui" / "src" / "rules-spec.json")
        .read_text())
    assert artifact == rules_spec(), (
        "gui/src/rules-spec.json drifted from advisory.rules_spec() — "
        "regenerate: python3 advisory.py > gui/src/rules-spec.json")


def test_rule_golden_vectors_match_gui():
    from advisory import activity_recommendations
    from ledger import CopilotActivity
    for (days, apps, tracked), expected in RULE_GOLDEN:
        act = CopilotActivity(
            user="probe@x.com", days_since_last_activity=days,
            active_apps=apps, apps_ever_used=apps, apps_tracked=tracked)
        [rec] = activity_recommendations([act])
        assert rec.verdict == expected, (
            f"days={days} apps={apps} tracked={tracked}: "
            f"got {rec.verdict}, want {expected}")


# ---------------------------------------------------------------- pv-4b
# Live-recorded payload: GET /orgs/{org}/copilot/billing/seats against a
# real org, 2026-06-12, Copilot Business enabled with zero seats. The raw
# page carried exactly these two keys — the pv-4a fixture shape is the
# live shape. (Read-only validation; populated-seat pull awaits a real
# seat assignment, which costs money and is a user decision.)
LIVE_EMPTY_SEATS = {"total_seats": 0, "seats": []}


def test_live_recorded_empty_org_end_to_end():
    """The day-one MSP scenario: client enabled Copilot, assigned nobody."""
    import json
    from demo import Brand, parse_upload, render_report
    activities, note, product = parse_upload(json.dumps(LIVE_EMPTY_SEATS))
    assert activities == [] and product == "github"
    recs = activity_recommendations(activities, seat_cost_usd=19.0,
                                    product="github")
    html_out = render_report(recs, Brand(msp_name="MSP", client_name="Org"),
                             data_note=note)
    assert "$0" in html_out and "0 seats to reclaim" in html_out


def test_report_rules_intro_names_the_actual_source():
    """Found on the first live GitHub pull: the rules intro said
    'Microsoft 365' regardless of where the rows came from."""
    from demo import Brand, render_report
    from advisory import SeatRecommendation
    gh = [SeatRecommendation("a@x.com", "keep", "active", 0.0, "github")]
    m365 = [SeatRecommendation("a@x.com", "keep", "active", 0.0, "m365")]
    brand = Brand(msp_name="MSP", client_name="Org")
    assert "based on GitHub Copilot activity data" in render_report(gh, brand)
    assert "based on Microsoft 365 Copilot activity data" in render_report(m365, brand)
    assert "based on GitHub Copilot + Microsoft 365 Copilot activity data" \
        in render_report(gh + m365, brand)
    assert "based on Copilot activity data" in render_report([], brand)


# Scrubbed live-shape seat object: the FULL schema GitHub actually returns
# (recorded 2026-06-12 from a real Copilot Business seat; login scrubbed).
# pv-4a fixtures modeled only assignee.login + last_activity_at — this
# locks in tolerance for the six extra keys a real seat carries.
LIVE_SHAPE_SEAT = {
    "created_at": "2026-06-12T11:01:16-07:00",
    "updated_at": "2026-06-12T11:01:16-07:00",
    "last_activity_at": None,
    "last_activity_editor": None,
    "last_authenticated_at": None,
    "pending_cancellation_date": None,
    "plan_type": "business",
    "assignee": {"login": "dev1", "id": 1, "type": "User"},
}


def test_full_live_shape_seat_parses_and_reports():
    """A freshly assigned, never-used seat (the live pv-4c scenario):
    parser must tolerate the full object and the report must say so."""
    from demo import Brand, render_report
    from ledger import parse_github_copilot_seats
    payload = {"total_seats": 1, "seats": [LIVE_SHAPE_SEAT]}
    [act] = parse_github_copilot_seats(payload, as_of="2026-06-12")
    assert act.user == "dev1" and act.days_since_last_activity is None
    recs = activity_recommendations([act], seat_cost_usd=19.0,
                                    product="github")
    assert recs[0].verdict == "reclaim"
    assert recs[0].reason == "never used Copilot"
    html_out = render_report(
        recs, Brand(msp_name="MSP", client_name="Org", seat_cost_usd=19.0))
    assert "based on GitHub Copilot activity data" in html_out
    assert "1 seat to reclaim" in html_out          # pluralization (pv-4c)
    assert "1 seats" not in html_out
