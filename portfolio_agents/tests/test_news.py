import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from portfolio_agents.agents import news
from portfolio_agents.config import load_settings
from portfolio_agents.state import State
from portfolio_agents.universe import Universe

DATA = Path(__file__).resolve().parent.parent / "data"

RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Feed</title>
<item>
  <title>Apple beats earnings estimates</title>
  <link>https://example.com/a</link>
  <description>&lt;p&gt;iPhone sales rose&lt;/p&gt;</description>
  <pubDate>Wed, 14 Oct 2026 12:00:00 GMT</pubDate>
</item>
</channel></rss>
"""

ATOM = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Tesla falls after probe</title>
    <link href="https://example.com/b"/>
    <updated>2026-10-14T10:00:00Z</updated>
    <summary>Investigation widens</summary>
  </entry>
</feed>
"""


def _item(item_id, title, summary=""):
    return news.NewsItem(item_id, title, summary, f"https://example.com/{item_id}", "example.com",
                         datetime.now(timezone.utc))


class NewsTest(unittest.TestCase):
    def setUp(self):
        self.universe = Universe.load(DATA / "xtb_universe.csv")
        self.settings = load_settings()

    def test_parse_rss_item(self):
        items = news.parse_feed(RSS, "https://feeds.example.com/rss")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Apple beats earnings estimates")
        self.assertEqual(items[0].summary, "iPhone sales rose")
        self.assertEqual(items[0].published, datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc))

    def test_parse_atom_entry(self):
        items = news.parse_feed(ATOM, "https://feeds.example.com/atom")
        self.assertEqual(items[0].link, "https://example.com/b")
        self.assertEqual(items[0].published.hour, 10)

    def test_select_new_skips_seen_and_old_items(self):
        now = datetime.now(timezone.utc)
        state = State({})
        fresh = _item("fresh", "Apple news")
        old = news.NewsItem("old", "Old", "", "", "x", now - timedelta(days=2))
        seen = _item("seen", "Seen news")
        state.mark("news", "seen")
        selected = news.select_new([fresh, old, seen], state, lookback_hours=6, now=now)
        self.assertEqual([i.id for i in selected], ["fresh"])

    def test_attach_candidates_matches_aliases(self):
        batch = news.attach_candidates([_item("1", "Trump Media posts quarterly loss")], self.universe)
        self.assertEqual(batch[0][1], ["DJT"])

    def test_lexicon_fallback_and_event_mapping(self):
        batch = [(_item("1", "Apple beats estimates, record profit"), ["AAPL"])]
        verdicts = news.lexicon_verdicts(batch)
        events = news.verdicts_to_events(verdicts, batch)
        self.assertEqual(len(events), 1)
        self.assertEqual((events[0].symbol, events[0].direction), ("AAPL", 1))

    def test_verdicts_outside_candidates_or_weak_are_dropped(self):
        batch = [(_item("1", "Apple news"), ["AAPL"])]
        verdicts = [
            news.NewsVerdict(item_id="1", symbol="TSLA", sentiment=0.9, relevance=0.9, reason="obca"),
            news.NewsVerdict(item_id="1", symbol="AAPL", sentiment=0.9, relevance=0.2, reason="szum"),
            news.NewsVerdict(item_id="1", symbol="AAPL", sentiment=0.9, relevance=0.8, reason="istotne"),
        ]
        events = news.verdicts_to_events(verdicts, batch)
        self.assertEqual(len(events), 1)
        self.assertIn("istotne", events[0].title)

    def test_classify_with_llm_uses_structured_parse(self):
        verdicts = news.NewsVerdicts(verdicts=[
            news.NewsVerdict(item_id="1", symbol="AAPL", sentiment=0.7, relevance=0.9, reason="wyniki")
        ])
        client = SimpleNamespace(messages=SimpleNamespace(parse=lambda **kwargs: SimpleNamespace(parsed_output=verdicts)))
        result = news.classify_with_llm(client, "claude-opus-5-5", [(_item("1", "Apple beats"), ["AAPL"])])
        self.assertEqual(result[0].symbol, "AAPL")

    def test_collect_without_llm_uses_lexicon(self):
        items = [_item("1", "Tesla falls after probe", "Investigation widens")]
        state = State({})
        with patch.object(news, "fetch_items", return_value=items):
            events = news.collect(self.settings, self.universe, state)
        self.assertEqual([(e.symbol, e.direction) for e in events], [("TSLA", -1)])
        self.assertTrue(state.seen("news", "1"))


if __name__ == "__main__":
    unittest.main()
