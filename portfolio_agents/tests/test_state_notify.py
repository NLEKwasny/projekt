import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from portfolio_agents import notify
from portfolio_agents.config import load_settings
from portfolio_agents.models import Alert
from portfolio_agents.state import State
from portfolio_agents.universe import Universe
from portfolio_agents.config import DATA_DIR


class StateTest(unittest.TestCase):
    def test_cooldown_blocks_repeat_alert(self):
        state = State({})
        now = datetime.now(timezone.utc)
        self.assertTrue(state.can_alert("AAPL", "BUY", 12, now))
        state.record_alert("AAPL", "BUY", now)
        self.assertFalse(state.can_alert("AAPL", "BUY", 12, now + timedelta(hours=1)))
        self.assertTrue(state.can_alert("AAPL", "BUY", 12, now + timedelta(hours=13)))
        self.assertTrue(state.can_alert("AAPL", "SELL", 12, now + timedelta(hours=1)))

    def test_save_and_load_roundtrip_keeps_holdings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "state.json"
            state = State({})
            state.mark("insider", "0001-26-000001")
            state.set_holdings("0001067983", "0001-26-000002", {"037833100": ["APPLE INC", "037833100", 1.0]})
            state.save(path)
            loaded = State.load(path)
            self.assertTrue(loaded.seen("insider", "0001-26-000001"))
            self.assertEqual(loaded.holdings("0001067983")["accession"], "0001-26-000002")
            json.loads(path.read_text(encoding="utf-8"))  # plik jest poprawnym JSON-em

    def test_corrupted_file_starts_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text("{nie-json", encoding="utf-8")
            self.assertFalse(State.load(path).seen("news", "x"))


class NotifyTest(unittest.TestCase):
    def setUp(self):
        self.settings = replace(load_settings(), ntfy_topic="test-topic-123")
        self.alert = Alert("DJT", "BUY", 0.41, ["[insider] Trump Donald J kupił 10 000 szt."], strong=True)

    def test_render_contains_reasons_and_disclaimer(self):
        body = notify.render(self.alert)
        self.assertIn("Wynik: +0.41", body)
        self.assertIn("• [insider]", body)
        self.assertIn("nie rekomendacja", body)

    def test_send_posts_json_with_priority_and_topic(self):
        with patch.object(notify, "post_json") as post:
            notify.send(self.alert, self.settings)
        server, payload = post.call_args.args
        self.assertEqual(server, "https://ntfy.sh")
        self.assertEqual(payload["topic"], "test-topic-123")
        self.assertEqual(payload["title"], "BUY DJT")
        self.assertEqual(payload["priority"], 4)

    def test_send_requires_topic(self):
        with self.assertRaises(RuntimeError):
            notify.send(self.alert, replace(self.settings, ntfy_topic=""))


class UniverseTest(unittest.TestCase):
    def setUp(self):
        self.universe = Universe.load(DATA_DIR / "xtb_universe.csv")

    def test_text_matching_by_name_alias_and_ticker(self):
        self.assertEqual(self.universe.match_text("Apple unveils new iPhone"), {"AAPL"})
        self.assertEqual(self.universe.match_text("Trump Media posts loss"), {"DJT"})
        self.assertEqual(self.universe.match_text("DJT shares jump"), {"DJT"})
        self.assertEqual(self.universe.match_text("Nothing relevant here"), set())

    def test_issuer_matching_for_13f_names(self):
        self.assertEqual(self.universe.match_issuer("NVIDIA CORP"), "NVDA")
        self.assertEqual(self.universe.match_issuer("ALPHABET INC"), "GOOGL")
        self.assertIsNone(self.universe.match_issuer("UNKNOWN WIDGETS LTD"))

    def test_has_is_case_insensitive(self):
        self.assertTrue(self.universe.has("aapl"))
        self.assertFalse(self.universe.has("ZZZZ"))


if __name__ == "__main__":
    unittest.main()
