"""Główna pętla: uruchamia agentów, łączy zdarzenia w sygnały, wysyła alerty i zapisuje stan."""

from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime, timezone
from typing import Any

from . import notify, technicals
from .agents import holdings, insider, manual, news
from .config import DATA_DIR, load_settings
from .models import Event
from .signals import build_alerts
from .state import State
from .universe import Universe

log = logging.getLogger("portfolio_agents")


def _llm_client(api_key: str) -> Any:
    if not api_key:
        log.info("Brak ANTHROPIC_API_KEY - agent newsowy używa słów kluczowych")
        return None
    import anthropic

    return anthropic.Anthropic(api_key=api_key)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agenci śledzący portfele i generujący sygnały XTB")
    parser.add_argument("--dry-run", action="store_true", help="wypisz alerty zamiast wysyłać; nie zapisuj stanu")
    parser.add_argument("--no-llm", action="store_true", help="agent newsowy bez Claude (słowa kluczowe)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    settings = load_settings()
    universe = Universe.load(DATA_DIR / "xtb_universe.csv")
    state = State.load(settings.state_path)
    now = datetime.now(timezone.utc)
    llm = None if args.no_llm else _llm_client(settings.anthropic_api_key)

    agents = {
        "insider": lambda: insider.collect(settings, universe, state),
        "holdings": lambda: holdings.collect(settings, universe, state),
        "news": lambda: news.collect(settings, universe, state, llm=llm, now=now),
        "manual": lambda: manual.collect(universe, state),
    }
    events: list[Event] = []
    failed: list[str] = []
    for name, run in agents.items():
        try:
            events += run()
        except Exception:  # awaria jednego agenta nie zatrzymuje pozostałych
            failed.append(name)
            log.exception("Agent %s nie powiódł się", name)

    views = {}
    for ticker in sorted({e.symbol for e in events}):
        price_symbol = universe.price_symbol(ticker)
        if not price_symbol:
            log.info("Brak symbolu do notowań dla %s - analiza techniczna pominięta", ticker)
            continue
        try:
            view = technicals.technical_view(price_symbol)
        except Exception as exc:
            log.warning("Analiza techniczna %s pominięta: %s", ticker, exc)
            view = None
        if view is not None:
            views[ticker] = view
        time.sleep(0.3)

    sent = 0
    for alert in build_alerts(events, views, settings):
        if alert.action == "WATCH":
            log.info("OBSERWUJ %s (wynik %+.2f)", alert.symbol, alert.score)
            continue
        if not state.can_alert(alert.symbol, alert.action, settings.cooldown_hours, now):
            log.info("Cooldown: pomijam %s %s", alert.action, alert.symbol)
            continue
        if args.dry_run:
            print(f"--- {alert.action} {alert.symbol}\n{notify.render(alert)}\n")
        else:
            try:
                notify.send(alert, settings)
            except Exception:
                log.exception("Nie udało się wysłać alertu %s %s", alert.action, alert.symbol)
                continue
            state.record_alert(alert.symbol, alert.action, now)
        sent += 1

    if not args.dry_run:
        state.save(settings.state_path)
    log.info("Zdarzenia: %d, alerty: %d, błędy agentów: %s", len(events), sent, failed or "brak")
    return 1 if len(failed) == len(agents) else 0
