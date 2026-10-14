"""Agent insiderów: transakcje z formularzy SEC Form 4 (kupno P / sprzedaż S na rynku)."""

from __future__ import annotations

import logging
import math
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, timedelta

from ..config import Settings, sec_user_agent
from ..models import Event
from ..net import find_text, get_bytes, get_json, local_name, to_float
from ..state import State
from ..universe import Universe

log = logging.getLogger(__name__)
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc}/{doc}"


@dataclass(frozen=True)
class Trade:
    ticker: str
    issuer: str
    owner: str
    code: str      # P = zakup na rynku, S = sprzedaż na rynku, reszta (granty, opcje) ignorujemy
    acq_disp: str  # A = nabycie, D = zbycie
    shares: float
    price: float
    date: str


def parse_form4(xml_bytes: bytes) -> list[Trade]:
    root = ET.fromstring(xml_bytes)
    ticker = find_text(root, "issuerTradingSymbol").upper()
    issuer = find_text(root, "issuerName")
    owner = find_text(root, "rptOwnerName")
    trades = []
    for txn in root.iter():
        if local_name(txn.tag) != "nonDerivativeTransaction":
            continue
        trades.append(
            Trade(
                ticker=ticker,
                issuer=issuer,
                owner=owner,
                code=find_text(txn, "transactionCode"),
                acq_disp=find_text(txn, "transactionAcquiredDisposedCode"),
                shares=to_float(find_text(txn, "transactionShares")),
                price=to_float(find_text(txn, "transactionPricePerShare")),
                date=find_text(txn, "transactionDate"),
            )
        )
    return trades


def trade_to_event(trade: Trade, accession: str, index: int) -> Event | None:
    if trade.code == "P" and trade.acq_disp in ("A", ""):
        direction = 1
    elif trade.code == "S":
        direction = -1
    else:
        return None
    value = trade.shares * trade.price
    # Siła rośnie z logarytmem wartości: ~1 mln USD daje ok. 0.86, ~10 tys. USD ok. 0.57.
    strength = min(1.0, math.log10(max(value, 1.0)) / 7.0)
    verb = "kupił" if direction > 0 else "sprzedał"
    title = f"{trade.owner} {verb} {trade.shares:,.0f} szt. {trade.ticker} po {trade.price:.2f} USD (≈{value:,.0f} USD)"
    return Event(
        source="insider",
        symbol=trade.ticker,
        direction=direction,
        strength=round(strength, 3),
        title=title,
        actor=trade.owner,
        key=f"{accession}:{index}",
    )


def filing_url(cik: str, accession: str, primary_doc: str) -> str:
    # SEC w polu primaryDocument podaje wersję XSL (np. "xslF345X05/plik.xml");
    # surowy XML leży pod tą samą nazwą pliku, bez katalogu.
    doc = primary_doc.rsplit("/", 1)[-1]
    return ARCHIVE_URL.format(cik_int=int(cik), acc=accession.replace("-", ""), doc=doc)


def collect(settings: Settings, universe: Universe, state: State, today: date | None = None) -> list[Event]:
    today = today or date.today()
    cutoff = today - timedelta(days=settings.insider_lookback_days)
    ua = sec_user_agent(settings)
    events: list[Event] = []
    for investor in settings.investors:
        if investor.kind != "insider" or not investor.cik:
            continue
        try:
            events += _collect_person(investor.cik.zfill(10), cutoff, ua, universe, state)
        except Exception:  # jedna osoba nie blokuje pozostałych
            log.exception("Nie udało się pobrać Form 4 dla %s", investor.name)
    log.info("insider: %d zdarzeń", len(events))
    return events


def _collect_person(cik: str, cutoff: date, ua: str, universe: Universe, state: State) -> list[Event]:
    recent = get_json(SUBMISSIONS_URL.format(cik=cik), user_agent=ua)["filings"]["recent"]
    events: list[Event] = []
    for form, accession, filed, doc in zip(
        recent["form"], recent["accessionNumber"], recent["filingDate"], recent["primaryDocument"]
    ):
        if form != "4" or date.fromisoformat(filed) < cutoff or state.seen("insider", accession):
            continue
        time.sleep(0.15)  # SEC dopuszcza ok. 10 żądań na sekundę
        trades = parse_form4(get_bytes(filing_url(cik, accession, doc), user_agent=ua))
        for index, trade in enumerate(trades):
            if not universe.has(trade.ticker):
                continue
            event = trade_to_event(trade, accession, index)
            if event:
                events.append(event)
        state.mark("insider", accession)
    return events
