"""Lista instrumentów XTB i dopasowanie tekstu oraz emitentów (13F) do tickerów."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

LEGAL_SUFFIXES = {
    "INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED", "PLC",
    "SA", "NV", "LLC", "HOLDINGS", "HOLDING", "GROUP", "THE", "CL", "CLASS", "COM", "NEW", "ORD", "SHS",
}


def _norm(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + " "


def _issuer_key(name: str) -> str:
    words = re.sub(r"[^A-Z0-9 ]+", " ", name.upper()).split()
    return " ".join(w for w in words if w not in LEGAL_SUFFIXES)


@dataclass(frozen=True)
class Instrument:
    xtb_symbol: str
    ticker: str
    name: str
    aliases: tuple[str, ...]
    cusip: str


class Universe:
    def __init__(self, instruments: list[Instrument]):
        self.instruments = instruments
        self.tickers = {i.ticker for i in instruments}
        self._phrases: list[tuple[str, str]] = []
        self._issuers: dict[str, str] = {}
        self._cusips: dict[str, str] = {}
        for inst in instruments:
            if inst.cusip:
                self._cusips[inst.cusip] = inst.ticker
            self._issuers[_issuer_key(inst.name)] = inst.ticker
            for phrase in {inst.name, _issuer_key(inst.name), *inst.aliases}:
                norm = _norm(phrase)
                if len(norm.strip()) >= 4:
                    self._phrases.append((norm, inst.ticker))

    @classmethod
    def load(cls, path: Path) -> "Universe":
        with path.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        instruments = [
            Instrument(
                xtb_symbol=row["symbol"].strip(),
                ticker=row["ticker"].strip().upper(),
                name=row["name"].strip(),
                aliases=tuple(a.strip() for a in row.get("aliases", "").split(";") if a.strip()),
                cusip=(row.get("cusip") or "").strip().upper(),
            )
            for row in rows
            if row.get("ticker")
        ]
        return cls(instruments)

    def has(self, ticker: str) -> bool:
        return ticker.upper() in self.tickers

    def match_text(self, text: str) -> set[str]:
        """Tickery, których nazwa/alias lub ticker (WIELKIMI LITERAMI) występuje w tekście."""
        found: set[str] = set()
        norm = _norm(text)
        for phrase, ticker in self._phrases:
            if phrase in norm:
                found.add(ticker)
        for token in re.findall(r"(?<![A-Za-z])[A-Z]{2,5}(?![A-Za-z])", text):
            if token in self.tickers:
                found.add(token)
        return found

    def match_issuer(self, name: str, cusip: str = "") -> str | None:
        if cusip and cusip in self._cusips:
            return self._cusips[cusip]
        return self._issuers.get(_issuer_key(name))
