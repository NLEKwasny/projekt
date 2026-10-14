"""Agent techniczny: dzienne notowania (Yahoo Finance) -> SMA i RSI. Filtr potwierdzający sygnały."""

from __future__ import annotations

from .models import TechnicalView
from .net import get_json

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d"
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def rsi(closes: list[float], period: int = 14) -> float | None:
    """RSI z wygładzaniem Wildera."""
    if len(closes) <= period:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    avg_gain = sum(max(d, 0.0) for d in deltas[:period]) / period
    avg_loss = sum(max(-d, 0.0) for d in deltas[:period]) / period
    for d in deltas[period:]:
        avg_gain = (avg_gain * (period - 1) + max(d, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-d, 0.0)) / period
    if avg_loss == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


def closes_from_chart(payload: dict) -> list[float]:
    result = payload["chart"]["result"][0]
    closes = result["indicators"]["quote"][0]["close"]
    return [float(c) for c in closes if c is not None]


def technical_view(symbol: str) -> TechnicalView | None:
    payload = get_json(CHART_URL.format(symbol=symbol), user_agent=BROWSER_UA)
    closes = closes_from_chart(payload)
    if len(closes) < 50:
        return None
    last = closes[-1]
    sma20, sma50 = sma(closes, 20), sma(closes, 50)
    trend = 0
    if sma20 and sma50:
        if last > sma20 > sma50:
            trend = 1
        elif last < sma20 < sma50:
            trend = -1
    return TechnicalView(symbol, last, sma20, sma50, rsi(closes), trend)
