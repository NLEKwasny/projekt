"""Lista instrumentów XTB i dopasowanie tekstu oraz emitentów (13F) do tickerów.

Uniwersum to wszystko, co można kupić w XTB: akcje, ETF-y, indeksy, towary, waluty, krypto.
Klucz w całym systemie to ticker. Gdy dwa instrumenty mają ten sam ticker, zostaje pierwszy.
"""

from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

LEGAL_SUFFIXES = {
    "INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED", "PLC",
    "SA", "NV", "LLC", "HOLDINGS", "HOLDING", "GROUP", "THE", "CL", "CLASS", "COM", "NEW", "ORD", "SHS",
}


def _norm(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + " "


def _issuer_key(name: str) -> str:
    """Nazwa emitenta bez końcowych sufiksów prawnych ("Target Corp" -> "TARGET", "New York Times Co" -> "NEW YORK TIMES")."""
    words = re.sub(r"[^A-Z0-9 ]+", " ", name.upper()).split()
    while words and words[-1] in LEGAL_SUFFIXES:
        words.pop()
    while words and words[0] == "THE":
        words.pop(0)
    return " ".join(words)


def classify_symbol(symbol: str) -> tuple[str, str]:
    """Zwraca (asset_type, ticker). Akcje i ETF-y mają sufiks giełdy, np. AAPL.US -> ("equity", "AAPL").
    Reszta (indeksy, CFD, towary, waluty) dostaje ticker równy symbolowi, np. US500 -> ("other", "US500")."""
    base, dot, suffix = symbol.strip().rpartition(".")
    if dot and base and 2 <= len(suffix) <= 3 and suffix.isalpha() and suffix.isupper():
        return "equity", base.upper()
    return "other", symbol.strip().upper()


def default_price_symbol(symbol: str, asset_type: str, ticker: str) -> str:
    """Symbol do notowań w Yahoo. Na razie tylko dla amerykańskich akcji i ETF-ów (ticker == symbol Yahoo).
    Pozostałe giełdy i CFD wymagają ręcznego uzupełnienia w pliku, bez zgadywania."""
    return ticker if asset_type == "equity" and symbol.strip().upper().endswith(".US") else ""


@dataclass(frozen=True)
class Instrument:
    xtb_symbol: str
    ticker: str
    name: str
    aliases: tuple[str, ...]
    cusip: str
    asset_type: str = "equity"  # "equity" | "other"
    price_symbol: str = ""      # symbol w Yahoo Finance; pusty = brak analizy technicznej


class Universe:
    def __init__(self, instruments: list[Instrument]):
        unique: dict[str, Instrument] = {}
        for inst in instruments:
            unique.setdefault(inst.ticker, inst)
        if len(unique) != len(instruments):
            log.warning("Pominięto %d instrumentów o zduplikowanym tickerze", len(instruments) - len(unique))
        self.instruments = list(unique.values())
        self.by_ticker = unique
        self.tickers = set(unique)
        self._phrases: list[tuple[str, str]] = []
        self._issuers: dict[str, str] = {}
        self._cusips: dict[str, str] = {}
        for inst in self.instruments:
            if inst.cusip:
                self._cusips[inst.cusip] = inst.ticker
            issuer = _issuer_key(inst.name)
            self._issuers[issuer] = inst.ticker
            # Jednowyrazowa nazwa emitenta ("Target") jest zbyt ogólna, żeby ją szukać w newsach.
            # Taki emitent trafia do newsów tylko przez pełną nazwę albo alias.
            phrases = {inst.name, *inst.aliases}
            if len(issuer.split()) >= 2:
                phrases.add(issuer)
            for phrase in phrases:
                norm = _norm(phrase)
                if len(norm.strip()) >= 4:
                    self._phrases.append((norm, inst.ticker))

    @classmethod
    def load(cls, path: Path) -> "Universe":
        with path.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        instruments = []
        for row in rows:
            if not row.get("ticker"):
                continue
            symbol = row["symbol"].strip()
            ticker = row["ticker"].strip().upper()
            asset_type = (row.get("asset_type") or "").strip() or classify_symbol(symbol)[0]
            price_symbol = (row.get("price_symbol") or "").strip() or default_price_symbol(symbol, asset_type, ticker)
            instruments.append(Instrument(
                xtb_symbol=symbol,
                ticker=ticker,
                name=row["name"].strip(),
                aliases=tuple(a.strip() for a in (row.get("aliases") or "").split(";") if a.strip()),
                cusip=(row.get("cusip") or "").strip().upper(),
                asset_type=asset_type,
                price_symbol=price_symbol,
            ))
        return cls(instruments)

    def has(self, ticker: str) -> bool:
        return ticker.upper() in self.tickers

    def price_symbol(self, ticker: str) -> str:
        inst = self.by_ticker.get(ticker.upper())
        return inst.price_symbol if inst else ""

    def match_text(self, text: str) -> set[str]:
        """Tickery, których nazwa/alias lub ticker (WIELKIMI LITERAMI) występuje w tekście."""
        found: set[str] = set()
        norm = _norm(text)
        for phrase, ticker in self._phrases:
            if phrase in norm:
                found.add(ticker)
        # Tickery mogą zawierać cyfry (DE40 to indeks, nie Deere), więc tokenem jest cały ciąg liter i cyfr.
        for token in re.findall(r"(?<![A-Za-z0-9])[A-Z][A-Z0-9]{1,5}(?![A-Za-z0-9])", text):
            if token in self.tickers:
                found.add(token)
        return found

    def match_issuer(self, name: str, cusip: str = "") -> str | None:
        if cusip and cusip in self._cusips:
            return self._cusips[cusip]
        return self._issuers.get(_issuer_key(name))
