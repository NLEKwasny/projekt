"""Agent newsowy: nagłówki z RSS (Wall Street, Forbes, Google News) oceniane przez Claude."""

from __future__ import annotations

import hashlib
import html
import json
import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from pydantic import BaseModel

from ..config import Settings
from ..models import Event
from ..net import get_bytes, local_name
from ..state import State
from ..universe import Universe

log = logging.getLogger(__name__)
MAX_LLM_ITEMS = 40  # limit nagłówków na jedno uruchomienie (koszt i czas)

SYSTEM_PROMPT = """Jesteś analitykiem rynku akcji. Dostajesz nagłówki wiadomości finansowych oraz listę kandydatów-tickerów dla każdego z nich.
Dla każdej pary (nagłówek, ticker), która jest realnym tematem wiadomości, oceń:
- sentiment: od -1 (wyraźnie negatywne dla kursu spółki) do +1 (wyraźnie pozytywne); 0 gdy neutralne lub niejasne.
- relevance: od 0 do 1, jak istotna jest wiadomość dla kursu tej spółki w najbliższych dniach. Plotki, komentarze i wiadomości poboczne dostają niskie wartości.
- reason: jedno krótkie zdanie po polsku.
Pomijaj pary, w których spółka nie jest tematem wiadomości. Nie dopowiadaj faktów spoza nagłówka i streszczenia."""

POSITIVE_WORDS = ("beats", "surges", "soars", "record", "upgrade", "buyback", "raises guidance", "jumps",
                  "rallies", "wins", "approval", "profit rises", "tops estimates")
NEGATIVE_WORDS = ("plunges", "falls", "downgrade", "lawsuit", "probe", "recall", "misses", "cuts guidance",
                  "slumps", "tumbles", "bankruptcy", "fraud", "sell-off", "layoffs", "investigation")


@dataclass(frozen=True)
class NewsItem:
    id: str
    title: str
    summary: str
    link: str
    source: str
    published: datetime | None


class NewsVerdict(BaseModel):
    item_id: str
    symbol: str
    sentiment: float
    relevance: float
    reason: str


class NewsVerdicts(BaseModel):
    verdicts: list[NewsVerdict]


def parse_feed(xml_bytes: bytes, feed_url: str) -> list[NewsItem]:
    """Obsługuje RSS 2.0 (<item>) i Atom (<entry>)."""
    root = ET.fromstring(xml_bytes)
    source = urllib.parse.urlparse(feed_url).netloc
    items: list[NewsItem] = []
    for node in root.iter():
        if local_name(node.tag) not in ("item", "entry"):
            continue
        title = _child_text(node, "title")
        if not title:
            continue
        link = _link(node)
        summary = _strip_html(_child_text(node, "description") or _child_text(node, "summary") or _child_text(node, "content"))
        published = _parse_date(_child_text(node, "pubDate") or _child_text(node, "published") or _child_text(node, "updated"))
        item_id = hashlib.sha1((link or title).encode("utf-8")).hexdigest()[:12]
        items.append(NewsItem(item_id, _strip_html(title), summary, link, source, published))
    return items


def _child_text(node: Any, name: str) -> str:
    for child in node:
        if local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _link(node: Any) -> str:
    for child in node:
        if local_name(child.tag) == "link":
            return child.get("href") or (child.text or "").strip()
    return ""


def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def _parse_date(text: str) -> datetime | None:
    if not text:
        return None
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def fetch_items(feeds: list[str]) -> list[NewsItem]:
    items: dict[str, NewsItem] = {}
    for url in feeds:
        try:
            for item in parse_feed(get_bytes(url), url):
                items.setdefault(item.id, item)
        except Exception as exc:  # jeden zepsuty kanał nie zatrzymuje reszty
            log.warning("RSS %s pominięty: %s", url, exc)
    return list(items.values())


def select_new(items: list[NewsItem], state: State, lookback_hours: float, now: datetime) -> list[NewsItem]:
    cutoff = now - timedelta(hours=lookback_hours)
    return [it for it in items if not state.seen("news", it.id) and (it.published is None or it.published >= cutoff)]


def attach_candidates(items: list[NewsItem], universe: Universe) -> list[tuple[NewsItem, list[str]]]:
    batch = []
    for item in items:
        symbols = sorted(universe.match_text(f"{item.title}. {item.summary}"))
        if symbols:
            batch.append((item, symbols))
    return batch


def classify_with_llm(client: Any, model: str, batch: list[tuple[NewsItem, list[str]]]) -> list[NewsVerdict]:
    payload = [
        {
            "item_id": item.id,
            "source": item.source,
            "title": item.title,
            "summary": item.summary[:400],
            "candidate_symbols": symbols,
        }
        for item, symbols in batch
    ]
    response = client.messages.parse(
        model=model,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        output_format=NewsVerdicts,
    )
    if response.parsed_output is None:
        raise RuntimeError("Claude nie zwrócił poprawnej odpowiedzi")
    return response.parsed_output.verdicts


def lexicon_verdicts(batch: list[tuple[NewsItem, list[str]]]) -> list[NewsVerdict]:
    """Tryb awaryjny bez LLM: prosty licznik słów kluczowych, relevance zawsze 0.5."""
    verdicts = []
    for item, symbols in batch:
        text = f"{item.title} {item.summary}".lower()
        pos = sum(word in text for word in POSITIVE_WORDS)
        neg = sum(word in text for word in NEGATIVE_WORDS)
        if pos == neg:
            continue
        sentiment = (pos - neg) / (pos + neg)
        for symbol in symbols:
            verdicts.append(NewsVerdict(item_id=item.id, symbol=symbol, sentiment=sentiment,
                                        relevance=0.5, reason="słowa kluczowe (tryb awaryjny)"))
    return verdicts


def verdicts_to_events(verdicts: list[NewsVerdict], batch: list[tuple[NewsItem, list[str]]]) -> list[Event]:
    allowed = {item.id: (item, set(symbols)) for item, symbols in batch}
    events = []
    for verdict in verdicts:
        if verdict.item_id not in allowed:
            continue
        item, symbols = allowed[verdict.item_id]
        if verdict.symbol not in symbols:  # odrzucamy tickery spoza kandydatów (halucynacje)
            continue
        sentiment = max(-1.0, min(1.0, verdict.sentiment))
        relevance = max(0.0, min(1.0, verdict.relevance))
        if abs(sentiment) < 0.2 or relevance < 0.4:
            continue
        events.append(Event(
            source="news",
            symbol=verdict.symbol,
            direction=1 if sentiment > 0 else -1,
            strength=round(abs(sentiment) * relevance, 3),
            title=f"{verdict.reason} — {item.title}",
            actor=item.source,
            url=item.link,
            key=f"{item.id}:{verdict.symbol}",
        ))
    return events


def collect(settings: Settings, universe: Universe, state: State, llm: Any = None,
            now: datetime | None = None) -> list[Event]:
    now = now or datetime.now(timezone.utc)
    fresh = select_new(fetch_items(settings.news_feeds), state, settings.news_lookback_hours, now)
    for item in fresh:
        state.mark("news", item.id)
    batch = attach_candidates(fresh, universe)
    if len(batch) > MAX_LLM_ITEMS:
        log.info("news: pomijam %d nagłówków ponad limit", len(batch) - MAX_LLM_ITEMS)
        batch = batch[:MAX_LLM_ITEMS]
    if not batch:
        return []
    verdicts: list[NewsVerdict] | None = None
    if llm is not None:
        try:
            verdicts = classify_with_llm(llm, settings.claude_model, batch)
        except Exception as exc:
            log.warning("Claude niedostępny (%s) - używam słów kluczowych", exc)
    if verdicts is None:
        verdicts = lexicon_verdicts(batch)
    events = verdicts_to_events(verdicts, batch)
    log.info("news: %d nagłówków z tickerami, %d zdarzeń", len(batch), len(events))
    return events
