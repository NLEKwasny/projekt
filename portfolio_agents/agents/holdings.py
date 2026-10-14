"""Agent funduszy: pozycje z raportów 13F-HR (kwartalnie). Porównuje kolejne raporty i wykrywa zmiany."""

from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date

from ..config import Settings, sec_user_agent
from ..models import Event
from ..net import find_text, get_bytes, get_json, local_name, to_float
from ..state import State
from ..universe import Universe

log = logging.getLogger(__name__)
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
INDEX_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc}/index.json"
CHANGE_THRESHOLD = 0.25  # zmiana o mniej niż 25% pomijamy jako szum

STRENGTH = {"NOWA": 0.6, "ZAMKNIETA": 0.7, "ZWIEKSZENIE": 0.5, "ZMNIEJSZENIE": 0.5}
DIRECTION = {"NOWA": 1, "ZWIEKSZENIE": 1, "ZMNIEJSZENIE": -1, "ZAMKNIETA": -1}


@dataclass(frozen=True)
class Change:
    symbol: str
    name: str
    kind: str  # NOWA | ZWIEKSZENIE | ZMNIEJSZENIE | ZAMKNIETA
    before: float
    after: float


def parse_info_table(xml_bytes: bytes) -> dict[str, list]:
    """Zwraca {klucz: [nazwa, cusip, akcje]}. Kluczem jest CUSIP, a gdy go brak - nazwa. Pomija opcje."""
    root = ET.fromstring(xml_bytes)
    positions: dict[str, list] = {}
    for row in root.iter():
        if local_name(row.tag) != "infoTable" or find_text(row, "putCall"):
            continue
        name = find_text(row, "nameOfIssuer")
        cusip = find_text(row, "cusip").upper()
        shares = to_float(find_text(row, "sshPrnamt"))
        key = cusip or name.upper()
        previous = positions.get(key)
        positions[key] = [name, cusip, shares + (previous[2] if previous else 0.0)]
    return positions


def latest_13f(submissions: dict) -> tuple[str, str] | None:
    recent = submissions["filings"]["recent"]
    for form, accession, filed in zip(recent["form"], recent["accessionNumber"], recent["filingDate"]):
        if form in ("13F-HR", "13F-HR/A"):
            return accession, filed
    return None


def info_table_url(cik: str, accession: str, user_agent: str) -> str:
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"
    index = get_json(base + "index.json", user_agent=user_agent)
    names = [item["name"] for item in index["directory"]["item"]]
    xmls = [n for n in names if n.lower().endswith(".xml") and "primary" not in n.lower()]
    tables = [n for n in xmls if "info" in n.lower()] or xmls
    if not tables:
        raise RuntimeError(f"Brak pliku infoTable w zgłoszeniu {accession}")
    return base + tables[0]


def diff_positions(previous: dict[str, list], current: dict[str, list], universe: Universe) -> list[Change]:
    changes: list[Change] = []
    for key, (name, cusip, shares) in current.items():
        symbol = universe.match_issuer(name, cusip)
        if not symbol:
            continue
        old = previous.get(key, [name, cusip, 0.0])[2]
        if old == 0 and shares > 0:
            kind = "NOWA"
        elif old > 0 and shares > old * (1 + CHANGE_THRESHOLD):
            kind = "ZWIEKSZENIE"
        elif old > 0 and shares < old * (1 - CHANGE_THRESHOLD):
            kind = "ZMNIEJSZENIE"
        else:
            continue
        changes.append(Change(symbol, name, kind, old, shares))
    for key, (name, cusip, old_shares) in previous.items():
        if key in current or old_shares <= 0:
            continue
        symbol = universe.match_issuer(name, cusip)
        if symbol:
            changes.append(Change(symbol, name, "ZAMKNIETA", old_shares, 0.0))
    return changes


def collect(settings: Settings, universe: Universe, state: State, today: date | None = None) -> list[Event]:
    today = today or date.today()
    ua = sec_user_agent(settings)
    events: list[Event] = []
    for investor in settings.investors:
        if investor.kind != "fund" or not investor.cik:
            continue
        try:
            events += _collect_fund(investor.name, investor.cik.zfill(10), settings, universe, state, today, ua)
        except Exception:  # jeden fundusz nie blokuje pozostałych
            log.exception("Nie udało się pobrać 13F dla %s", investor.name)
    log.info("holdings: %d zdarzeń", len(events))
    return events


def _collect_fund(name: str, cik: str, settings: Settings, universe: Universe, state: State,
                  today: date, ua: str) -> list[Event]:
    latest = latest_13f(get_json(SUBMISSIONS_URL.format(cik=cik), user_agent=ua))
    if not latest:
        return []
    accession, filed = latest
    snapshot = state.holdings(cik)
    if snapshot and snapshot["accession"] == accession:
        return []
    time.sleep(0.15)
    current = parse_info_table(get_bytes(info_table_url(cik, accession, ua), user_agent=ua))
    fresh = (today - date.fromisoformat(filed)).days <= settings.holdings_max_age_days
    events: list[Event] = []
    if snapshot is not None and fresh:
        events = [_to_event(name, change, accession) for change in diff_positions(snapshot["positions"], current, universe)]
    # Pierwszy odczyt tylko tworzy punkt odniesienia - zmiany liczymy przy kolejnym raporcie.
    state.set_holdings(cik, accession, current)
    return events


def _to_event(fund: str, change: Change, accession: str) -> Event:
    verbs = {
        "NOWA": "otworzył nową pozycję w",
        "ZAMKNIETA": "zamknął pozycję w",
        "ZWIEKSZENIE": "zwiększył pozycję w",
        "ZMNIEJSZENIE": "zmniejszył pozycję w",
    }
    title = f"{fund} {verbs[change.kind]} {change.symbol}: {change.before:,.0f} → {change.after:,.0f} akcji (13F)"
    return Event(
        source="holdings",
        symbol=change.symbol,
        direction=DIRECTION[change.kind],
        strength=STRENGTH[change.kind],
        title=title,
        actor=fund,
        key=f"{accession}:{change.symbol}:{change.kind}",
    )
