import unittest
from dataclasses import replace

from portfolio_agents.config import load_settings
from portfolio_agents.models import Event, TechnicalView
from portfolio_agents.signals import build_alerts, decide


def _event(source, symbol, direction, strength):
    return Event(source=source, symbol=symbol, direction=direction, strength=strength, title=f"{source} {symbol}")


def _view(trend=0, rsi14=50.0):
    return TechnicalView(symbol="AAPL", last=100.0, sma20=99.0, sma50=95.0, rsi14=rsi14, trend=trend)


class SignalsTest(unittest.TestCase):
    def setUp(self):
        self.settings = load_settings()

    def test_single_weak_news_only_watches(self):
        alert = decide("AAPL", [_event("news", "AAPL", 1, 1.0)], None, self.settings)
        self.assertEqual(alert.action, "WATCH")

    def test_strong_insider_purchase_alone_is_buy(self):
        alert = decide("DJT", [_event("insider", "DJT", 1, 0.86)], None, self.settings)
        self.assertEqual(alert.action, "BUY")
        self.assertTrue(alert.strong)

    def test_two_agreeing_sources_are_buy(self):
        events = [_event("news", "AAPL", 1, 0.9), _event("holdings", "AAPL", 1, 0.6)]
        self.assertEqual(decide("AAPL", events, None, self.settings).action, "BUY")

    def test_disagreeing_sources_cancel_out(self):
        events = [_event("news", "AAPL", 1, 1.0), _event("news", "AAPL", -1, 1.0)]
        self.assertIsNone(decide("AAPL", events, None, self.settings))

    def test_falling_trend_downgrades_buy_to_watch(self):
        alert = decide("DJT", [_event("insider", "DJT", 1, 0.86)], _view(trend=-1), self.settings)
        self.assertEqual(alert.action, "WATCH")
        self.assertTrue(any("trend spadkowy" in r for r in alert.reasons))

    def test_overbought_rsi_downgrades_buy(self):
        alert = decide("DJT", [_event("insider", "DJT", 1, 0.86)], _view(trend=1, rsi14=80), self.settings)
        self.assertEqual(alert.action, "WATCH")

    def test_sell_is_filtered_when_not_in_my_positions(self):
        settings = replace(self.settings, my_positions=frozenset({"AAPL"}))
        events = [_event("insider", "TSLA", -1, 0.9)]
        self.assertEqual(build_alerts(events, {}, settings), [])

    def test_sell_is_kept_for_owned_position(self):
        settings = replace(self.settings, my_positions=frozenset({"TSLA"}))
        alerts = build_alerts([_event("insider", "TSLA", -1, 0.9)], {}, settings)
        self.assertEqual([(a.symbol, a.action) for a in alerts], [("TSLA", "SELL")])

    def test_build_alerts_groups_by_symbol_and_sorts_by_score(self):
        events = [
            _event("manual", "DJT", 1, 0.9),
            _event("news", "AAPL", 1, 0.9),
            _event("holdings", "AAPL", 1, 0.6),
        ]
        alerts = build_alerts(events, {}, self.settings)
        self.assertEqual([a.symbol for a in alerts], ["DJT", "AAPL"])


if __name__ == "__main__":
    unittest.main()
