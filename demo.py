"""The validation artifact: upload a Graph Copilot usage CSV, get back a
branded 'AI License Right-Sizing Report'.

  python demo.py sample            -> SAMPLE_REPORT.html (fake 28-user org)
  python demo.py serve [port]      -> local upload page at http://localhost:8400

The report is self-contained HTML with print CSS — 'Save as PDF' from any
browser produces the client deliverable. (Deliberate choice: stdlib has no
PDF writer; print-to-PDF on clean print CSS is the validation-stage answer.)
The upload page POSTs the raw CSV text (no multipart; Python 3.13 removed
cgi), so the server stays stdlib-only and the file never leaves the machine
it runs on — a selling point for MSP trust, stated on the page.
"""

from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass, replace
from http.server import BaseHTTPRequestHandler, HTTPServer

from advisory import (ACTIVITY_RULES, SeatRecommendation,
                      activity_recommendations, projected_savings)
from ledger import parse_github_copilot_seats, parse_graph_copilot_activity


@dataclass(frozen=True)
class Brand:
    msp_name: str = "Your MSP"
    accent: str = "#1f6feb"          # brandable accent color
    client_name: str = "Client"
    seat_cost_usd: float = 30.0      # Copilot seat list price default


VERDICT_STYLE = {"keep": ("Keep", "#2e5f33"), "review": ("Review", "#7d5311"),
                 "reclaim": ("Reclaim", "#a02128")}


# ---------------------------------------------------- Federal Memo chrome
# The design law from gui/src/tokens.css (think:63), translated for
# self-contained stdlib HTML: system-safe font stacks, no webfonts, no SVG
# filters, print-to-PDF clean. Manila stock, carbon ink, double-strike
# rules, stamped verdicts with deterministic tilt.

MEMO_CSS = """
 :root { --paper:#f0e6d2; --sheet:#f7efdd; --ink:#211d16; --muted:#564e3f;
         --hairline:#c0b194; --accent:ACCENT_HEX; }
 body { background:#4a5248
        radial-gradient(ellipse at 50% 30%, rgba(255,255,255,.05),
        rgba(0,0,0,.28) 95%); color:var(--ink); margin:0; padding:2rem 1rem;
        min-height:100vh;
        font:15px/1.55 'Archivo','Helvetica Neue',Arial,sans-serif; }
 .doc { max-width:860px; margin:0 auto; background:var(--sheet)
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' \
width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence \
type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3CfeColorMatrix \
values='0 0 0 0 0.13 0 0 0 0 0.11 0 0 0 0 0.08 0 0 0 0.6 0'/%3E%3C/filter%3E\
%3Crect width='160' height='160' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E");
        border:1px solid var(--hairline); padding:2.5rem 3rem;
        box-shadow:0 1px 2px rgba(20,24,18,.45), 0 10px 36px rgba(20,24,18,.3),
        inset 0 0 24px rgba(60,48,25,.07); }
 h1,h2,.disp { text-transform:uppercase; letter-spacing:.07em;
        font-weight:900; line-height:1.15; }
 .rule2 { border:none; border-top:2px solid var(--ink);
        box-shadow:0 2.5px 0 -1px var(--ink); margin:.5rem 0 1.2rem; }
 .mono { font-family:'IBM Plex Mono','Courier New',monospace;
        font-variant-numeric:tabular-nums; }
 .meta { color:var(--muted); }
 .lh { display:flex; align-items:center; gap:1rem; }
 .lh .agency { font-size:1rem; }
 .lh .docket { font-size:.72rem; color:var(--muted); letter-spacing:.08em; }
 .stamp { display:inline-block; font-weight:900; text-transform:uppercase;
        letter-spacing:.12em; font-size:.74em; padding:1px 8px 0;
        border:2.5px solid currentColor; }
 table { border-collapse:collapse; width:100%; }
 th { text-transform:uppercase; font-size:.72rem; letter-spacing:.07em; }
 th,td { text-align:left; padding:.5rem .6rem;
        border-bottom:1px solid var(--hairline); }
 .num { text-align:right; }
 .rules { border:1px solid var(--hairline); padding:.8rem 1.2rem;
        margin:1.2rem 0; }
 footer { margin-top:2rem; padding-top:.8rem; color:var(--muted);
        border-top:1px solid var(--hairline); font-size:.8em; }
 button { font:inherit; font-weight:600; text-transform:uppercase;
        letter-spacing:.07em; font-size:.82em; color:var(--ink);
        background:var(--sheet); border:2px solid var(--ink); border-radius:0;
        padding:.4rem 1rem; cursor:pointer; }
 @media print { body { background:#fff; padding:0; }
        .doc { border:none; box-shadow:none; background:#fff; }
        .noprint { display:none; } }
"""

CREST_SVG = """<svg width="44" height="44" viewBox="0 0 44 44" role="img"
 aria-label="Office of Seat Utilization Review crest">
 <circle cx="22" cy="22" r="20" fill="none" stroke="currentColor" stroke-width="2.5"/>
 <circle cx="22" cy="22" r="15.5" fill="none" stroke="currentColor" stroke-width="1"/>
 <text x="22" y="20" text-anchor="middle" font-size="9" font-weight="900"
  font-family="Arial">OSUR</text>
 <text x="22" y="31" text-anchor="middle" font-size="9">&#9878;</text></svg>"""


def _memo_head(title: str, accent: str = "#27418f") -> str:
    return (f'<!doctype html><html><head><meta charset="utf-8">'
            f"<title>{html.escape(title)}</title>"
            f"<style>{MEMO_CSS.replace('ACCENT_HEX', accent)}</style></head>")


def _letterhead(docket_line: str) -> str:
    return (f'<div class="lh">{CREST_SVG}<div>'
            f'<div class="disp agency">Office of Seat Utilization Review</div>'
            f'<div class="docket mono">{html.escape(docket_line)}</div>'
            f"</div></div><hr class='rule2'>")


def _fnv1a(s: str) -> int:
    """FNV-1a over UTF-16 code units — byte-for-byte the GUI's stableHash
    (gui/src/hash.ts iterates charCodeAt), so both surfaces agree."""
    h = 0x811C9DC5
    data = s.encode("utf-16-le")
    for i in range(0, len(data), 2):
        h ^= data[i] | (data[i + 1] << 8)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def _stamp_tilt(user: str) -> float:
    """Deterministic ±2° per user — same hash, same input string, same tilt
    as the GUI's stampTilt (gui-11 unification; was crc32 before)."""
    return ((_fnv1a(f"{user}|stamp") % 9) - 4) * 0.5


def _stamp(verdict: str, user: str) -> str:
    label, color = VERDICT_STYLE[verdict]
    return (f"<span class='stamp' style='color:{color};"
            f"transform:rotate({_stamp_tilt(user)}deg)'>{label}</span>")


class PseudonymizedDataError(ValueError):
    """The export was produced with M365's concealed-names setting ON
    (the tenant default since Sept 2021): users appear as opaque hex IDs,
    so no seat can be named and the report would be useless."""


_PSEUDONYM = re.compile(r"^[0-9A-Fa-f]{16,}$")


def looks_pseudonymized(users: list[str]) -> bool:
    """True when a majority of non-empty user identifiers are hex blobs
    with no '@' — the shape M365 emits when report names are concealed."""
    named = [u for u in users if u]
    if not named:
        return False
    hits = sum(1 for u in named if "@" not in u and _PSEUDONYM.match(u))
    return hits * 2 >= len(named)


def parse_upload(text: str, as_of: str | None = None):
    """Sniff + parse either export. Returns (activities, data_note, product).

    JSON object => GitHub seats API payload; anything else => Microsoft
    Graph Copilot usage CSV. Raises PseudonymizedDataError when the CSV
    was exported with concealed names (M365 tenant default).
    """
    stripped = text.lstrip()
    if stripped.startswith("{"):
        import datetime
        import json as _json
        payload = _json.loads(stripped)
        activities = parse_github_copilot_seats(
            payload, as_of or datetime.date.today().isoformat())
        data_note = ("Activity data from GitHub's Copilot seats API, which "
                     "retains last-activity for roughly 90 days — “never "
                     "used” means no activity within that retained window.")
        product = "github"
    else:
        activities = parse_graph_copilot_activity(text)
        if looks_pseudonymized([a.user for a in activities]):
            raise PseudonymizedDataError(
                "usernames in this export are concealed")
        data_note = ("Activity data from the Microsoft 365 Copilot usage "
                     "report; no message content is accessed.")
        product = "m365"
    return activities, data_note, product


def rightsizing_report(text: str, brand: Brand = Brand(),
                       as_of: str | None = None) -> str:
    """M365 Copilot usage CSV OR GitHub Copilot seats JSON -> branded report.

    Raises PseudonymizedDataError on a concealed-names M365 export.
    """
    activities, data_note, product = parse_upload(text, as_of)
    recs = activity_recommendations(activities, brand.seat_cost_usd,
                                    product=product)
    return render_report(recs, brand, data_note=data_note)


def apply_overrides(recs: list[SeatRecommendation],
                    overrides: dict[int, str],
                    seat_cost_usd: float) -> list[SeatRecommendation]:
    """Reviewer verdict overrides, keyed by rec index. Savings are
    recomputed so projected_savings() stays the single source of truth."""
    out = []
    for i, r in enumerate(recs):
        v = overrides.get(i, r.verdict)
        if v not in VERDICT_STYLE or v == r.verdict:
            out.append(r)
        else:
            out.append(replace(
                r, verdict=v,
                monthly_saving_usd=seat_cost_usd if v == "reclaim" else 0.0,
                reason=f"{r.reason} — reviewer override"))
    return out


def _voice(rec: SeatRecommendation) -> str:
    """Committee-voice evidence line for the INTERNAL review page only.
    Data-payload-only: every line restates the rec's own true evidence.
    The client-facing report never renders these (hard register boundary)."""
    if rec.verdict == "reclaim":
        if "never" in rec.reason:
            return ("NOTICE: this seat has fulfilled its contractual "
                    "obligation to exist. Usage was at no point part of "
                    "the arrangement.")
        return (f"NOTICE: {html.escape(rec.reason)}. The license billed "
                "on time regardless.")
    return html.escape(rec.reason)


DEFAULT_DATA_NOTE = ("Activity data comes from the Microsoft 365 Copilot "
                     "usage report; no message content is accessed.")


def render_report(recs: list[SeatRecommendation], brand: Brand,
                  data_note: str = DEFAULT_DATA_NOTE) -> str:
    monthly = projected_savings(recs)
    counts = {v: sum(1 for r in recs if r.verdict == v)
              for v in ("keep", "review", "reclaim")}
    e = html.escape
    glyph = {"m365": "Ⓜ ", "github": "ⓖ "}
    mixed = len({r.product for r in recs}) > 1
    rows = "\n".join(
        f"<tr><td class='mono'>{glyph.get(r.product, '') if mixed else ''}{e(r.user)}</td>"
        f"<td>{_stamp(r.verdict, r.user)}</td>"
        f"<td class='mono meta'>{e(r.reason)}</td>"
        f"<td class='num mono'>{'$%.0f' % r.monthly_saving_usd if r.monthly_saving_usd else '—'}</td></tr>"
        for r in sorted(recs, key=lambda r: ("reclaim review keep".split()
                                             .index(r.verdict), r.user)))
    rules = "".join(f"<li><b>{e(v.title())}:</b> {e(d)}</li>"
                    for v, d in ACTIVITY_RULES)
    # the rules intro must name the ACTUAL data source(s) of the rows —
    # found product-blind ("Microsoft 365") on the first live GitHub pull
    # (pv-4b); an empty pull falls back to the generic label
    src_name = {"m365": "Microsoft 365 Copilot", "github": "GitHub Copilot"}
    sources = sorted({src_name.get(r.product, r.product) for r in recs})
    source_label = " + ".join(sources) if sources else "Copilot"
    return f"""{_memo_head(f"AI License Right-Sizing — {brand.client_name}", brand.accent)}
<body><div class="doc">
{_letterhead(f"PREPARED BY {brand.msp_name.upper()} · {len(recs)} COPILOT SEATS ANALYZED")}
<h1 style="font-size:1.5rem;margin:.4rem 0">AI License Right-Sizing Report</h1>
<p class="meta">Prepared for <b>{e(brand.client_name)}</b> by
 <b>{e(brand.msp_name)}</b></p>
<p class="headline" style="font-size:1.5rem">Projected savings:
 <b class="mono" style="color:{brand.accent}">${monthly:,.0f}/month</b>
 (${monthly * 12:,.0f}/year) — {counts['reclaim']} seat{'' if counts['reclaim'] == 1 else 's'} to reclaim,
 {counts['review']} to review, {counts['keep']} actively used.</p>
<div class="rules"><b class="disp" style="font-size:.78rem">How verdicts are decided</b>
(based on {source_label} activity data; seat cost
${brand.seat_cost_usd:,.0f}/mo):
<ul>{rules}</ul></div>
<table><thead><tr><th>User</th><th>Verdict</th><th>Why</th>
<th class="num">Monthly saving</th></tr></thead><tbody>
{rows}
</tbody></table>
<footer class="mono">Generated by token-optim. {e(data_note)} Verdicts are
recommendations — review before reclaiming seats.</footer>
</div></body></html>"""


def render_review_page(recs: list[SeatRecommendation], brand: Brand,
                       csv_text: str) -> str:
    """The ratify step: every seat's suggested verdict as radio rows,
    savings recomputed live from the same per-seat figures the report
    uses. Internal surface — Committee voice allowed in evidence lines."""
    e = html.escape
    monthly = projected_savings(recs)
    order = "reclaim review keep".split()
    rows = "\n".join(
        f"<tr><td>{e(r.user)}</td>"
        f"<td class='ev'>{_voice(r)}</td>"
        + "".join(
            f"<td><label><input type='radio' name='v_{i}' value='{v}' "
            f"data-save='{brand.seat_cost_usd if v == 'reclaim' else 0:.0f}'"
            f"{' checked' if r.verdict == v else ''}> {v}</label></td>"
            for v in ("keep", "review", "reclaim"))
        + "</tr>"
        for i, r in sorted(enumerate(recs),
                           key=lambda p: (order.index(p[1].verdict),
                                          p[1].user)))
    return f"""{_memo_head(f"Ratify verdicts — {brand.client_name}")}
<body><div class="doc">
{_letterhead(f"{brand.client_name.upper()} · THE DOCKET · IN SESSION")}
<style>.ev {{ color: var(--muted); font-size: .88em;
 font-family:'IBM Plex Mono','Courier New',monospace; }}</style>
<h1 style="font-size:1.3rem">The docket — {len(recs)} seats await ratification</h1>
<p class="meter" style="font-size:1.4rem">Savings found:
 <b id="m" class="mono" style="color:#2e5f33">${monthly:,.0f}</b>/month
 (recomputed as you ratify; the report uses the same figures)</p>
<form method="post" action="/generate">
<input type="hidden" name="msp" value="{e(brand.msp_name)}">
<input type="hidden" name="client" value="{e(brand.client_name)}">
<textarea name="csv" hidden>{e(csv_text)}</textarea>
<table><thead><tr><th>User</th><th>Evidence</th>
<th colspan="3">Verdict</th></tr></thead><tbody>
{rows}
</tbody></table>
<p><button>Seal the report &#10142;</button>
 <span class="ev">The generated report is client-ready and plainly
 worded; these working notes stay on this page.</span></p>
</form>
<script>
function tally() {{
  let s = 0;
  document.querySelectorAll('input:checked').forEach(r => s += +r.dataset.save);
  document.getElementById('m').textContent = '$' + s.toLocaleString();
}}
document.querySelectorAll('input[type=radio]').forEach(r =>
  r.addEventListener('change', tally));
</script></div></body></html>"""


ANONYMIZED_PAGE = (
    _memo_head("This export has concealed names")
    + '<body><div class="doc">'
    + _letterhead("PRE-FLIGHT NOTICE · EXPORT SETTINGS")
    + '<h1 style="font-size:1.3rem">This export has concealed names</h1>')
ANONYMIZED_PAGE += """
<p>Every user in this CSV appears as an anonymous ID (for example
<code>98700DF7&hellip;</code>). Microsoft 365 conceals usernames in usage
reports <b>by default</b>, so a right-sizing report can't name a single
seat. This is a one-time tenant setting, not a problem with your file.</p>
<p><b>To export with names</b> (global admin, takes a minute):</p>
<ol>
<li>Microsoft 365 admin center &rarr; <b>Settings</b> &rarr;
 <b>Org settings</b> &rarr; <b>Services</b> &rarr; <b>Reports</b></li>
<li>Uncheck <i>"Display concealed user, group, and site names in all
 reports"</i> and save</li>
<li>Re-export the Copilot usage report and upload it here again</li>
</ol>
<p class="meta">Names are processed on this machine only and are
never sent anywhere. The setting change is logged in your tenant's audit
trail, and you can re-enable concealment after exporting.</p>
<p><a href="/">&larr; back to upload</a></p>
</div></body></html>"""


# ----------------------------------------------------------------- server

UPLOAD_PAGE = (
    _memo_head("token-optim — AI License Right-Sizing")
    + '<body><div class="doc">'
    + _letterhead("INTAKE DESK · UPLOAD AN EXPORT")
    + '<h1 style="font-size:1.3rem">AI License Right-Sizing</h1>')
UPLOAD_PAGE += """
<p>Upload either export — both produce the same report:</p>
<ul>
<li><b>Microsoft 365 Copilot</b>: usage report CSV
 (Admin Center &rarr; Reports &rarr; Usage &rarr; Copilot &rarr; Export).
 <b>Pre-flight:</b> M365 conceals usernames in reports by default — turn off
 <i>Settings &rarr; Org settings &rarr; Services &rarr; Reports &rarr;
 concealed names</i> first, or the export can't name seats (we'll detect
 this and show the steps).</li>
<li><b>GitHub Copilot</b>: seats JSON
 (<code>gh api /orgs/&lt;org&gt;/copilot/billing/seats</code>)</li>
</ul>
<p>Processing happens on this machine only — the file is never sent anywhere.</p>
<input type="file" id="f" accept=".csv,.json">
<label>MSP name <input id="msp" value="Your MSP"></label>
<label>Client name <input id="client" value="Client"></label>
<button onclick="go()">Generate report</button>
<script>
async function go() {
  const file = document.getElementById('f').files[0];
  if (!file) return alert('pick a CSV');
  const text = await file.text();
  const q = new URLSearchParams({msp: msp.value, client: client.value});
  const resp = await fetch('/report?' + q, {method: 'POST',
    headers: {'Content-Type': 'text/csv'}, body: text});
  document.open(); document.write(await resp.text()); document.close();
}
</script></div></body></html>"""


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._send(200, UPLOAD_PAGE)

    def do_POST(self):
        from urllib.parse import parse_qs, urlparse
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        if self.path.startswith("/report"):
            # upload -> ratify page (the review step before any report)
            q = parse_qs(urlparse(self.path).query)
            brand = Brand(msp_name=q.get("msp", ["Your MSP"])[0],
                          client_name=q.get("client", ["Client"])[0])
            try:
                activities, _, product = parse_upload(body)
            except PseudonymizedDataError:
                return self._send(200, ANONYMIZED_PAGE)
            except Exception as exc:  # bad CSV -> honest 422, no stack trace
                return self._send(422, f"could not parse that CSV: {exc}")
            recs = activity_recommendations(activities, brand.seat_cost_usd,
                                            product=product)
            return self._send(200, render_review_page(recs, brand, body))
        if self.path.startswith("/generate"):
            # ratified verdicts -> final client-ready report
            form = parse_qs(body)
            brand = Brand(msp_name=form.get("msp", ["Your MSP"])[0],
                          client_name=form.get("client", ["Client"])[0])
            csv_text = form.get("csv", [""])[0]
            try:
                activities, data_note, product = parse_upload(csv_text)
            except Exception as exc:
                return self._send(422, f"could not parse that CSV: {exc}")
            recs = activity_recommendations(activities, brand.seat_cost_usd,
                                            product=product)
            overrides = {}
            for key, vals in form.items():
                if key.startswith("v_") and key[2:].isdigit():
                    overrides[int(key[2:])] = vals[0]
            recs = apply_overrides(recs, overrides, brand.seat_cost_usd)
            return self._send(200, render_report(recs, brand,
                                                 data_note=data_note))
        self._send(404, "not found")

    def _send(self, code: int, body: str):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # quiet
        pass


def serve(port: int = 8400) -> HTTPServer:
    server = HTTPServer(("127.0.0.1", port), DemoHandler)
    return server


# ----------------------------------------------------------------- sample

def sample_csv() -> str:
    """Realistic fake 28-user org: a productive core, single-app dabblers,
    and a long tail of never/stale seats (matches the heavy-tailed adoption
    pattern from the research phases)."""
    refresh = "2026-06-01"
    header = ("User Principal Name,Report Refresh Date,"
              "Last Activity Date,Copilot Chat Last Activity Date,"
              "Word Copilot Last Activity Date,Teams Copilot Last Activity Date")
    rows = [header]

    def row(u, last, chat="", word="", teams=""):
        rows.append(f"{u}@fabrikam-demo.com,{refresh},{last},{chat},{word},{teams}")

    actives = ["maria.chen", "dev.patel", "sofia.reyes", "james.okafor",
               "lena.fischer", "tom.nguyen", "ana.silva", "kate.morris"]
    for i, u in enumerate(actives):
        d = f"2026-05-{28 - i:02d}"
        row(u, d, chat=d, word=f"2026-05-{20 - i:02d}", teams=d)
    dabblers = ["raj.kumar", "emily.watts", "chris.lee", "nina.petrov",
                "omar.hassan", "julia.brandt"]
    for i, u in enumerate(dabblers):
        d = f"2026-05-{10 - i:02d}"
        row(u, d, chat=d)
    stale = ["mark.olsen", "tina.gomez", "pete.sullivan", "amy.zhao",
             "dan.murphy", "rosa.lima"]
    for i, u in enumerate(stale):
        d = f"2026-0{3 + i % 2}-1{i}"
        row(u, d, word=d)
    never = ["bob.tanner", "sue.ellis", "victor.cruz", "amanda.king",
             "hal.jordan", "iris.west", "ray.palmer", "kara.danvers"]
    for u in never:
        row(u, "")
    return "\n".join(rows) + "\n"


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "sample"
    if cmd == "sample":
        brand = Brand(msp_name="Northwind IT Partners",
                      client_name="Fabrikam Manufacturing")
        report = rightsizing_report(sample_csv(), brand)
        with open("SAMPLE_REPORT.html", "w") as f:
            f.write(report)
        print("wrote SAMPLE_REPORT.html (open in a browser; print to PDF)")
        return 0
    if cmd == "serve":
        port = int(argv[1]) if len(argv) > 1 else 8400
        print(f"upload page: http://127.0.0.1:{port}  (Ctrl-C to stop)")
        serve(port).serve_forever()
        return 0
    print("usage: python demo.py [sample|serve [port]]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
