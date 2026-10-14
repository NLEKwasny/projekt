"""Stan między uruchomieniami: deduplikacja zdarzeń, cooldown alertów, poprzednie pozycje funduszy."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Ile dni pamiętamy klucze w danym koszyku (newsy wygasają szybko, nagrania rzadziej).
RETENTION_DAYS = {"news": 3, "insider": 60, "holdings": 60, "manual": 365}
DEFAULT_RETENTION_DAYS = 60


def _now() -> datetime:
    return datetime.now(timezone.utc)


class State:
    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.data.setdefault("seen", {})
        self.data.setdefault("holdings", {})
        self.data.setdefault("alerts", {})

    @classmethod
    def load(cls, path: Path) -> "State":
        if path.exists():
            try:
                return cls(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                log.warning("Uszkodzony plik stanu %s - zaczynam od zera", path)
        return cls({})

    def save(self, path: Path) -> None:
        self.prune()
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, path)

    def seen(self, bucket: str, key: str) -> bool:
        return key in self.data["seen"].get(bucket, {})

    def mark(self, bucket: str, key: str) -> None:
        self.data["seen"].setdefault(bucket, {})[key] = _now().isoformat()

    def holdings(self, cik: str) -> dict[str, Any] | None:
        return self.data["holdings"].get(cik)

    def set_holdings(self, cik: str, accession: str, positions: dict[str, list]) -> None:
        self.data["holdings"][cik] = {"accession": accession, "positions": positions}

    def can_alert(self, symbol: str, action: str, cooldown_hours: float, now: datetime) -> bool:
        last = self.data["alerts"].get(f"{symbol}:{action}")
        if not last:
            return True
        return now - datetime.fromisoformat(last) >= timedelta(hours=cooldown_hours)

    def record_alert(self, symbol: str, action: str, now: datetime) -> None:
        self.data["alerts"][f"{symbol}:{action}"] = now.isoformat()

    def prune(self) -> None:
        now = _now()
        for bucket, keys in self.data["seen"].items():
            days = RETENTION_DAYS.get(bucket, DEFAULT_RETENTION_DAYS)
            cutoff = now - timedelta(days=days)
            for key in [k for k, ts in keys.items() if datetime.fromisoformat(ts) < cutoff]:
                del keys[key]
        cutoff = now - timedelta(days=2)
        alerts = self.data["alerts"]
        for key in [k for k, ts in alerts.items() if datetime.fromisoformat(ts) < cutoff]:
            del alerts[key]
