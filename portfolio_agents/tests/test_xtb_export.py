import csv
import tempfile
import unittest
from pathlib import Path

from portfolio_agents import xtb_export
from portfolio_agents.universe import Universe, classify_symbol, default_price_symbol

# Rekordy SYNTETYCZNE (fixtury), kształtem zgodne z polami SYMBOL_RECORD. Nie są danymi XTB.
RECORDS = [
    {"symbol": "FIXA.US", "description": "Fixture Alpha Corp", "categoryName": "STC", "groupName": "Stocks"},
    {"symbol": "FIXA.DE", "description": "Fixture Alpha Corp (DE)", "categoryName": "STC", "groupName": "Stocks"},
    {"symbol": "FIXB.US", "description": "Fixture Beta ETF", "categoryName": "ETF", "groupName": "ETF"},
    {"symbol": "FIXIDX500", "description": "Fixture Index 500", "categoryName": "IND", "groupName": "Indices"},
]


class FakeTransport:
    def __init__(self, responses):
        self.responses = responses
        self.sent: list[dict] = []
        self.closed = False

    def send(self, payload):
        self.sent.append(payload)
        return self.responses[payload["command"]]

    def close(self):
        self.closed = True


def _ok(**extra):
    return {"status": True, **extra}


class ClassifyTest(unittest.TestCase):
    def test_exchange_suffix_means_equity(self):
        self.assertEqual(classify_symbol("AAPL.US"), ("equity", "AAPL"))
        self.assertEqual(classify_symbol("SAP.DE"), ("equity", "SAP"))

    def test_indices_and_cfds_are_other(self):
        self.assertEqual(classify_symbol("US500"), ("other", "US500"))
        self.assertEqual(classify_symbol("EURUSD"), ("other", "EURUSD"))

    def test_price_symbol_only_for_us_equities(self):
        self.assertEqual(default_price_symbol("AAPL.US", "equity", "AAPL"), "AAPL")
        self.assertEqual(default_price_symbol("SAP.DE", "equity", "SAP"), "")
        self.assertEqual(default_price_symbol("US500", "other", "US500"), "")


class ExportTest(unittest.TestCase):
    def _transport(self, login=None):
        return FakeTransport({
            "login": login or _ok(streamSessionId="x"),
            "getAllSymbols": _ok(returnData=RECORDS),
            "logout": _ok(),
        })

    def test_fetch_runs_login_symbols_logout_in_order(self):
        transport = self._transport()
        records = xtb_export.fetch_symbols(transport, "1", "pw")
        self.assertEqual([p["command"] for p in transport.sent], ["login", "getAllSymbols", "logout"])
        self.assertEqual(len(records), 4)

    def test_failed_login_raises_without_leaking_password(self):
        transport = self._transport(login={"status": False, "errorCode": "BE005", "errorDescr": "Bad login"})
        with self.assertRaises(xtb_export.XtbError) as ctx:
            xtb_export.fetch_symbols(transport, "1", "super-secret")
        self.assertNotIn("super-secret", str(ctx.exception))
        self.assertEqual([p["command"] for p in transport.sent], ["login"])

    def test_rows_dedupe_by_ticker_and_prefer_us_listing(self):
        rows = xtb_export.build_rows(RECORDS)
        tickers = [r["ticker"] for r in rows]
        self.assertEqual(sorted(tickers), sorted(set(tickers)))
        alpha = next(r for r in rows if r["ticker"] == "FIXA")
        self.assertEqual(alpha["symbol"], "FIXA.US")
        self.assertEqual(alpha["price_symbol"], "FIXA")
        index = next(r for r in rows if r["ticker"] == "FIXIDX500")
        self.assertEqual((index["asset_type"], index["price_symbol"]), ("other", ""))

    def test_csv_roundtrip_loads_into_universe(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "xtb_universe.csv"
            xtb_export.write_csv(xtb_export.build_rows(RECORDS), path)
            with path.open(encoding="utf-8", newline="") as fh:
                header = next(csv.reader(fh))
            self.assertEqual(header, xtb_export.CSV_FIELDS)
            universe = Universe.load(path)
            self.assertTrue(universe.has("FIXB"))
            self.assertEqual(universe.price_symbol("FIXB"), "FIXB")
            self.assertEqual(universe.price_symbol("FIXIDX500"), "")
            self.assertEqual(universe.match_text("Fixture Beta ETF rallies"), {"FIXB"})


if __name__ == "__main__":
    unittest.main()
