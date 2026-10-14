"""Konfiguracja: watchlista (config/watchlist.json) i zmienne środowiskowe (sekrety z GitHub Actions)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
DEFAULT_STATE_PATH = PACKAGE_DIR / "state" / "state.json"


@dataclass(frozen=True)
class Investor:
    name: str
    cik: str   # numer CIK z EDGAR; pusty = pomijamy
    kind: str  # "insider" -> Form 4 (transakcje), "fund" -> 13F-HR (portfel kwartalny)
    note: str = ""


@dataclass(frozen=True)
class Settings:
    investors: list[Investor]
    news_feeds: list[str]
    weights: dict[str, float]
    signal_threshold: float
    watch_threshold: float
    cooldown_hours: float
    news_lookback_hours: float
    insider_lookback_days: int
    holdings_max_age_days: int
    my_positions: frozenset[str]
    claude_model: str
    anthropic_api_key: str
    ntfy_server: str
    ntfy_topic: str
    sec_contact: str
    state_path: Path


def load_settings(path: Path = DATA_DIR / "watchlist.json") -> Settings:
    raw = json.loads(path.read_text(encoding="utf-8"))
    th = raw["thresholds"]
    return Settings(
        investors=[Investor(**item) for item in raw["investors"]],
        news_feeds=list(raw["news_feeds"]),
        weights={k: float(v) for k, v in raw["weights"].items()},
        signal_threshold=float(th["signal"]),
        watch_threshold=float(th["watch"]),
        cooldown_hours=float(th["cooldown_hours"]),
        news_lookback_hours=float(th["news_lookback_hours"]),
        insider_lookback_days=int(th["insider_lookback_days"]),
        holdings_max_age_days=int(th["holdings_max_age_days"]),
        my_positions=frozenset(s.strip().upper() for s in raw.get("my_positions", []) if s.strip()),
        claude_model=os.environ.get("CLAUDE_MODEL", "claude-opus-5-5"),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        ntfy_server=os.environ.get("NTFY_SERVER", "https://ntfy.sh"),
        ntfy_topic=os.environ.get("NTFY_TOPIC", ""),
        sec_contact=os.environ.get("SEC_CONTACT_EMAIL", ""),
        state_path=Path(os.environ.get("PA_STATE_PATH", DEFAULT_STATE_PATH)),
    )


def sec_user_agent(settings: Settings) -> str:
    # SEC wymaga identyfikującego User-Agent z kontaktem; ogólne UA bywa blokowane.
    return f"portfolio-agents/1.0 ({settings.sec_contact or 'ustaw SEC_CONTACT_EMAIL'})"
