"""Powiadomienia push na telefon przez ntfy.sh (aplikacja ntfy na Androida i iOS)."""

from __future__ import annotations

from .config import Settings
from .models import Alert
from .net import post_json

DISCLAIMER = "Sygnał informacyjny, nie rekomendacja inwestycyjna."


def render(alert: Alert) -> str:
    lines = [f"Wynik: {alert.score:+.2f}"]
    lines += [f"• {reason}" for reason in alert.reasons]
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def send(alert: Alert, settings: Settings) -> None:
    if not settings.ntfy_topic:
        raise RuntimeError("Brak NTFY_TOPIC - nie mam dokąd wysłać powiadomienia")
    payload = {
        "topic": settings.ntfy_topic,
        "title": f"{alert.action} {alert.symbol}",
        "message": render(alert),
        "priority": 4 if alert.strong else 3,
        "tags": ["chart_with_upwards_trend" if alert.action == "BUY" else "chart_with_downwards_trend"],
    }
    post_json(settings.ntfy_server, payload)
