import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from portfolio_agents.agents import news
from portfolio_agents.config import load_settings
from portfolio_agents.state import State
from portfolio_agents.universe import Universe

DATA = Path(__file__).resolve().parent.parent / "data"


def _item(item_id, title):
    return news.NewsItem(item_id, title, "", f"https://example.com/{item_id}", "example.com",
                         datetime.now(timezone.utc))


class OverflowTest(unittest.TestCase):
    def test_items_over_the_llm_cap_stay_unseen_for_the_next_run(self):
        universe = Universe.load(DATA / "xtb_universe.csv")
        settings = replace(load_settings(), news_feeds=[])
        items = [_item("a1", "Apple beats estimates"), _item("t1", "Tesla falls after probe")]
        state = State({})
        with patch.object(news, "fetch_items", return_value=items), patch.object(news, "MAX_LLM_ITEMS", 1):
            events = news.collect(settings, universe, state)
        self.assertTrue(state.seen("news", "a1"))
        self.assertFalse(state.seen("news", "t1"), "nagłówek ponad limit nie może zostać oznaczony jako przetworzony")
        self.assertEqual([e.symbol for e in events], ["AAPL"])


if __name__ == "__main__":
    unittest.main()
