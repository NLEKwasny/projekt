"""Koordynator portfela: łączy zdarzenia agentów w sygnały KUP / SPRZEDAJ / OBSERWUJ."""

from __future__ import annotations

from collections import defaultdict

from .config import Settings
from .models import Alert, Event, TechnicalView

# Źródła, które pojedynczo mogą uzasadnić alert, jeśli zdarzenie jest mocne.
STRONG_SOURCES = {"insider", "manual"}
STRONG_STRENGTH = 0.8


def _technical_gate(action: str, view: TechnicalView) -> tuple[str, str | None]:
    if action == "BUY":
        if view.trend < 0:
            return "WATCH", "Filtr techniczny: trend spadkowy, czekaj na potwierdzenie"
        if view.rsi14 is not None and view.rsi14 > 75:
            return "WATCH", "Filtr techniczny: RSI powyżej 75 (wykupienie)"
    if action == "SELL":
        if view.trend > 0:
            return "WATCH", "Filtr techniczny: trend wzrostowy, sprzedaż może być przedwczesna"
        if view.rsi14 is not None and view.rsi14 < 25:
            return "WATCH", "Filtr techniczny: RSI poniżej 25 (wyprzedanie)"
    return action, None


def decide(symbol: str, events: list[Event], technical: TechnicalView | None, settings: Settings) -> Alert | None:
    if not events:
        return None
    raw = sum(settings.weights.get(e.source, 0.0) * e.direction * e.strength for e in events)
    score = max(-1.0, min(1.0, raw))
    bull = {e.source for e in events if e.direction > 0}
    bear = {e.source for e in events if e.direction < 0}
    strong_bull = any(e.direction > 0 and e.source in STRONG_SOURCES and e.strength >= STRONG_STRENGTH for e in events)
    strong_bear = any(e.direction < 0 and e.source in STRONG_SOURCES and e.strength >= STRONG_STRENGTH for e in events)

    action = "WATCH"
    if score >= settings.signal_threshold and (len(bull) >= 2 or strong_bull):
        action = "BUY"
    elif score <= -settings.signal_threshold and (len(bear) >= 2 or strong_bear):
        action = "SELL"
    elif abs(score) < settings.watch_threshold:
        return None

    strong = strong_bull if action == "BUY" else strong_bear if action == "SELL" else False
    reasons = [
        f"[{e.source}] {e.title}"
        for e in sorted(events, key=lambda e: -abs(settings.weights.get(e.source, 0.0) * e.strength))
    ][:6]
    if technical is not None:
        action, note = _technical_gate(action, technical)
        if note:
            reasons.append(note)
        rsi_text = f"{technical.rsi14:.0f}" if technical.rsi14 is not None else "brak"
        trend_text = {1: "wzrostowy", -1: "spadkowy", 0: "neutralny"}[technical.trend]
        reasons.append(f"Technika: kurs {technical.last:.2f}, RSI {rsi_text}, trend {trend_text}")
    return Alert(symbol, action, round(score, 3), reasons, strong, technical)


def build_alerts(events: list[Event], technicals: dict[str, TechnicalView], settings: Settings) -> list[Alert]:
    by_symbol: dict[str, list[Event]] = defaultdict(list)
    for event in events:
        by_symbol[event.symbol].append(event)
    alerts: list[Alert] = []
    for symbol, symbol_events in by_symbol.items():
        alert = decide(symbol, symbol_events, technicals.get(symbol), settings)
        if alert is None:
            continue
        # Sprzedaż ma sens tylko dla pozycji, które faktycznie masz (gdy lista jest ustawiona).
        if alert.action == "SELL" and settings.my_positions and symbol not in settings.my_positions:
            continue
        alerts.append(alert)
    return sorted(alerts, key=lambda a: -abs(a.score))
