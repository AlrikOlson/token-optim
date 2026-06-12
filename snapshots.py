"""Client + PeriodSnapshot persistence — the data-moat primitive.

GitHub nils `last_activity_at` after 90 idle days and M365 reports look
back at most 180; monthly snapshots are how reclaim verdicts stay provable
after the vendor forgets. The store is append-only by construction: a
sealed (client, period) snapshot can never be rewritten — any attempt
raises SealedSnapshotError. The GUI's history strip, the sealed report
archive, and the QBR pack all read from here.

Layout: <root>/<client_id>/client.json + <root>/<client_id>/<YYYY-MM>.json
"""

from __future__ import annotations

import datetime
import json
import re
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from advisory import SeatRecommendation, projected_savings

#: Seat-list-price defaults per product (USD/month). Override per client.
PRODUCT_SEAT_COST_DEFAULTS = {"m365": 30.0, "github": 19.0}

_PERIOD = re.compile(r"^\d{4}-\d{2}$")


class SealedSnapshotError(RuntimeError):
    """Write attempted against a sealed (client, period) snapshot."""


@dataclass(frozen=True)
class Client:
    id: str                      # stable slug, used as the directory name
    name: str
    seat_costs: dict[str, float] = field(
        default_factory=lambda: dict(PRODUCT_SEAT_COST_DEFAULTS))


@dataclass(frozen=True)
class PeriodSnapshot:
    client_id: str
    period: str                  # YYYY-MM
    recs: tuple[SeatRecommendation, ...]
    sealed: bool = False
    sealed_at: str | None = None

    @property
    def savings_usd(self) -> float:
        return projected_savings(list(self.recs))


def _snapshot_to_json(s: PeriodSnapshot) -> dict:
    d = asdict(s)
    d["recs"] = [asdict(r) for r in s.recs]
    return d


def _snapshot_from_json(d: dict) -> PeriodSnapshot:
    return PeriodSnapshot(
        client_id=d["client_id"], period=d["period"],
        recs=tuple(SeatRecommendation(**r) for r in d["recs"]),
        sealed=d["sealed"], sealed_at=d.get("sealed_at"))


class SnapshotStore:
    """JSON-directory store. Drafts are rewritable; sealed is forever."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------- clients

    def save_client(self, client: Client) -> None:
        d = self.root / client.id
        d.mkdir(exist_ok=True)
        (d / "client.json").write_text(json.dumps(asdict(client), indent=1))

    def load_client(self, client_id: str) -> Client | None:
        p = self.root / client_id / "client.json"
        if not p.exists():
            return None
        return Client(**json.loads(p.read_text()))

    def clients(self) -> list[Client]:
        out = []
        for p in sorted(self.root.glob("*/client.json")):
            out.append(Client(**json.loads(p.read_text())))
        return out

    # --------------------------------------------------------- snapshots

    def _path(self, client_id: str, period: str) -> Path:
        if not _PERIOD.match(period):
            raise ValueError(f"period must be YYYY-MM, got {period!r}")
        return self.root / client_id / f"{period}.json"

    def load(self, client_id: str, period: str) -> PeriodSnapshot | None:
        p = self._path(client_id, period)
        if not p.exists():
            return None
        return _snapshot_from_json(json.loads(p.read_text()))

    def save_draft(self, snapshot: PeriodSnapshot) -> None:
        """Write/overwrite a draft. Refuses if that period is sealed,
        and refuses to write a snapshot already marked sealed (sealing
        goes through seal(), which is the only path to immutability)."""
        existing = self.load(snapshot.client_id, snapshot.period)
        if existing is not None and existing.sealed:
            raise SealedSnapshotError(
                f"{snapshot.client_id}/{snapshot.period} is sealed")
        if snapshot.sealed:
            raise SealedSnapshotError("use seal() to seal a draft")
        p = self._path(snapshot.client_id, snapshot.period)
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps(_snapshot_to_json(snapshot), indent=1))

    def seal(self, client_id: str, period: str,
             sealed_at: str | None = None) -> PeriodSnapshot:
        """Freeze the draft for (client, period). Idempotence is refused on
        purpose: sealing twice raises, so callers can't paper over a
        double-submit."""
        snap = self.load(client_id, period)
        if snap is None:
            raise FileNotFoundError(f"no draft for {client_id}/{period}")
        if snap.sealed:
            raise SealedSnapshotError(f"{client_id}/{period} already sealed")
        sealed = replace(
            snap, sealed=True,
            sealed_at=sealed_at
            or datetime.datetime.now(datetime.timezone.utc).isoformat())
        self._path(client_id, period).write_text(
            json.dumps(_snapshot_to_json(sealed), indent=1))
        return sealed

    def history(self, client_id: str,
                sealed_only: bool = True) -> list[PeriodSnapshot]:
        """Chronological snapshots — the moat. Sealed-only by default so
        downstream composition (history strip, QBR pack) structurally
        cannot include unsealed data."""
        d = self.root / client_id
        out = []
        for p in sorted(d.glob("????-??.json")):
            s = _snapshot_from_json(json.loads(p.read_text()))
            if s.sealed or not sealed_only:
                out.append(s)
        return out
