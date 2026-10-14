"""Ręczne sygnały z config/manual_signals.json.

Służy do wpisywania transakcji, które nie mają API (np. raporty 278-T prezydenta USA publikowane jako PDF).
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, timedelta
from pathlib import Path

from ..config import DATA_DIR
from ..models import Event
from ..state import State
from ..universe import Universe

log = logging.getLogger(__name__)
MAX_AGE_DAYS = 30


def collect(universe: Universe, state: State, path: Path = DATA_DIR / "manual_signals.json",
            today: date | None = None) -> list[Event]:
    if not path.exists():
        return []
    today = today or date.today()
    events: list[Event] = []
    for entry in json.loads(path.read_text(encoding="utf-8")):
        symbol = entry["symbol"].strip().upper()
        if not universe.has(symbol):
            continue
        if date.fromisoformat(entry["date"]) < today - timedelta(days=MAX_AGE_DAYS):
            continue
        key = hashlib.sha1(json.dumps(entry, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        if state.seen("manual", key):
            continue
        state.mark("manual", key)
        events.append(Event(
            source="manual",
            symbol=symbol,
            direction=1 if entry["action"].upper() == "BUY" else -1,
            strength=float(entry.get("strength", 0.9)),
            title=entry.get("title", "Ręczny sygnał"),
            actor=entry.get("actor", ""),
            url=entry.get("source_url", ""),
            key=key,
        ))
    log.info("manual: %d zdarzeń", len(events))
    return events
