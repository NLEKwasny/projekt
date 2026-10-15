"""Eksport pełnej listy instrumentów XTB przez xAPI (WebSocket).

Uruchamiasz lokalnie na swoim koncie. Dane logowania podajesz w terminalu (zmienne XTB_USER_ID i XTB_PASSWORD
albo pytanie), nigdy w repozytorium ani w czacie:

    XTB_USER_ID=12345678 python -m portfolio_agents.xtb_export            # konto realne
    python -m portfolio_agents.xtb_export --mode demo --out /tmp/demo.csv  # konto demo

Protokół zgodny z publicznymi klientami xAPI (ramka {"command", "arguments"}; odpowiedź ze "status"
oraz "returnData" albo "errorCode"/"errorDescr"). Nie był uruchamiany na żywym koncie w tej sesji.
"""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Protocol

from .config import DATA_DIR
from .universe import classify_symbol, default_price_symbol

log = logging.getLogger(__name__)
WS_URL = "wss://ws.xtb.com/{mode}"
MIN_INTERVAL_S = 0.2  # odstęp między zapytaniami, jak w publicznych klientach xAPI
CSV_FIELDS = ["symbol", "ticker", "name", "aliases", "cusip", "asset_type", "price_symbol", "category", "group"]


class XtbError(RuntimeError):
    pass


class Transport(Protocol):
    def send(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def close(self) -> None: ...


class WebSocketTransport:
    def __init__(self, mode: str):
        import websocket  # zależność potrzebna tylko do eksportu

        self._ws = websocket.create_connection(WS_URL.format(mode=mode), timeout=30)
        self._last = 0.0

    def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        wait = MIN_INTERVAL_S - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._ws.send(json.dumps(payload))
        response = json.loads(self._ws.recv())
        self._last = time.monotonic()
        return response

    def close(self) -> None:
        self._ws.close()


def _call(transport: Transport, command: str, **arguments: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"command": command}
    if arguments:
        payload["arguments"] = arguments
    response = transport.send(payload)
    if not response.get("status"):
        # Nie wypisujemy argumentów komendy: login zawiera hasło.
        raise XtbError(f"{command} odrzucone: {response.get('errorCode', '?')} {response.get('errorDescr', '')}")
    return response


def fetch_symbols(transport: Transport, user_id: str, password: str) -> list[dict[str, Any]]:
    _call(transport, "login", userId=user_id, password=password)
    try:
        return list(_call(transport, "getAllSymbols").get("returnData", []))
    finally:
        try:
            _call(transport, "logout")
        except XtbError as exc:
            log.warning("Wylogowanie nie powiodło się: %s", exc)


def build_rows(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows = []
    for record in records:
        symbol = str(record.get("symbol", "")).strip()
        if not symbol:
            continue
        asset_type, ticker = classify_symbol(symbol)
        rows.append({
            "symbol": symbol,
            "ticker": ticker,
            "name": str(record.get("description", "")).strip(),
            "aliases": "",
            "cusip": "",
            "asset_type": asset_type,
            "price_symbol": default_price_symbol(symbol, asset_type, ticker),
            "category": str(record.get("categoryName", "")),
            "group": str(record.get("groupName", "")),
        })
    return dedupe_by_ticker(rows)


def dedupe_by_ticker(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Jeden ticker = jeden wiersz. Przy kolizji (np. AAPL.US i AAPL.DE) zostaje notowanie w USA."""
    ordered = sorted(rows, key=lambda r: (not r["symbol"].upper().endswith(".US"), r["symbol"]))
    best: dict[str, dict[str, str]] = {}
    for row in ordered:
        best.setdefault(row["ticker"], row)
    if len(best) != len(rows):
        log.info("Pominięto %d wierszy o zduplikowanym tickerze", len(rows) - len(best))
    return list(best.values())


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Eksport listy instrumentów XTB do data/xtb_universe.csv")
    parser.add_argument("--mode", choices=["real", "demo"], default="real")
    parser.add_argument("--out", type=Path, default=DATA_DIR / "xtb_universe.csv")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    user_id = os.environ.get("XTB_USER_ID") or input("Numer konta XTB (userId): ").strip()
    password = os.environ.get("XTB_PASSWORD") or getpass.getpass("Hasło do xAPI: ")
    try:
        transport = WebSocketTransport(args.mode)
    except ImportError:
        print("Brak biblioteki websocket-client: pip install -r portfolio_agents/requirements.txt", file=sys.stderr)
        return 1
    try:
        records = fetch_symbols(transport, user_id, password)
    except XtbError as exc:
        print(f"Błąd xAPI: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # sieć, timeout, zerwane połączenie - bez śladu stosu, który mógłby zawierać dane sesji
        print(f"Nie udało się pobrać listy z XTB ({type(exc).__name__})", file=sys.stderr)
        return 1
    finally:
        transport.close()

    rows = build_rows(records)
    write_csv(rows, args.out)
    equities = sum(1 for r in rows if r["asset_type"] == "equity")
    print(f"Zapisano {len(rows)} instrumentów do {args.out} (akcje/ETF: {equities}, pozostałe: {len(rows) - equities})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
