"""Wspólne typy danych: zdarzenia od agentów, analiza techniczna, alerty."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Event:
    source: str      # "insider" | "holdings" | "news" | "manual"
    symbol: str      # ticker z listy instrumentów XTB
    direction: int   # +1 sygnał kupna, -1 sygnał sprzedaży
    strength: float  # 0..1
    title: str       # opis czytelny dla człowieka
    actor: str = ""  # kto: osoba, fundusz, portal
    url: str = ""
    key: str = ""    # klucz deduplikacji (numer akcesji, hash nagłówka)


@dataclass(frozen=True)
class TechnicalView:
    symbol: str
    last: float
    sma20: float | None
    sma50: float | None
    rsi14: float | None
    trend: int  # +1 wzrostowy, -1 spadkowy, 0 neutralny


@dataclass
class Alert:
    symbol: str
    action: str  # "BUY" | "SELL" | "WATCH"
    score: float  # -1..1, dodatni = kupno
    reasons: list[str] = field(default_factory=list)
    strong: bool = False
    technical: TechnicalView | None = None
