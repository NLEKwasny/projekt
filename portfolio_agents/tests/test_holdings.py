import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from portfolio_agents.agents import holdings
from portfolio_agents.agents.holdings import diff_positions, latest_13f, parse_info_table
from portfolio_agents.config import Investor, load_settings
from portfolio_agents.state import State
from portfolio_agents.universe import Universe

DATA = Path(__file__).resolve().parent.parent / "data"

INFO_TABLE = b"""<?xml version="1.0"?>
<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
  <infoTable>
    <nameOfIssuer>APPLE INC</nameOfIssuer>
    <cusip>037833100</cusip>
    <value>1000</value>
    <shrsOrPrnAmt><sshPrnamt>400000</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
  </infoTable>
  <infoTable>
    <nameOfIssuer>APPLE INC</nameOfIssuer>
    <cusip>037833100</cusip>
    <shrsOrPrnAmt><sshPrnamt>100000</sshPrnamt></shrsOrPrnAmt>
  </infoTable>
  <infoTable>
    <nameOfIssuer>APPLE INC</nameOfIssuer>
    <cusip>037833100</cusip>
    <putCall>PUT</putCall>
    <shrsOrPrnAmt><sshPrnamt>5</sshPrnamt></shrsOrPrnAmt>
  </infoTable>
</informationTable>
"""


class HoldingsTest(unittest.TestCase):
    def setUp(self):
        self.universe = Universe.load(DATA / "xtb_universe.csv")

    def test_parse_sums_lines_and_skips_options(self):
        positions = parse_info_table(INFO_TABLE)
        self.assertEqual(positions, {"037833100": ["APPLE INC", "037833100", 500000.0]})

    def test_diff_detects_new_increased_and_closed_positions(self):
        previous = {
            "037833100": ["APPLE INC", "037833100", 400000.0],
            "88160R101": ["TESLA INC", "88160R101", 50000.0],
        }
        current = {
            "037833100": ["APPLE INC", "037833100", 600000.0],
            "67066G104": ["NVIDIA CORP", "67066G104", 100000.0],
        }
        changes = {c.symbol: c.kind for c in diff_positions(previous, current, self.universe)}
        self.assertEqual(changes, {"AAPL": "ZWIEKSZENIE", "NVDA": "NOWA", "TSLA": "ZAMKNIETA"})

    def test_small_change_is_ignored(self):
        previous = {"037833100": ["APPLE INC", "037833100", 400000.0]}
        current = {"037833100": ["APPLE INC", "037833100", 410000.0]}
        self.assertEqual(diff_positions(previous, current, self.universe), [])

    def test_failing_fund_does_not_stop_the_others(self):
        settings = replace(load_settings(), investors=[
            Investor("Fund A", "0000000001", "fund"),
            Investor("Fund B", "0000000002", "fund"),
        ])
        empty_submissions = {"filings": {"recent": {"form": [], "accessionNumber": [], "filingDate": []}}}
        calls = []

        def fake_get_json(url, **kwargs):
            calls.append(url)
            if "0000000001" in url:
                raise RuntimeError("SEC niedostępne")
            return empty_submissions

        with patch.object(holdings, "get_json", side_effect=fake_get_json), \
                self.assertLogs("portfolio_agents.agents.holdings", level="ERROR"):
            events = holdings.collect(settings, self.universe, State({}))
        self.assertEqual(events, [])
        self.assertEqual(len(calls), 2)  # fundusz B został odpytany mimo błędu A

    def test_latest_13f_picks_newest_report(self):
        submissions = {"filings": {"recent": {
            "form": ["8-K", "13F-HR", "13F-HR"],
            "accessionNumber": ["0001-26-000009", "0001-26-000005", "0001-25-000001"],
            "filingDate": ["2026-10-01", "2026-08-14", "2025-11-14"],
        }}}
        self.assertEqual(latest_13f(submissions), ("0001-26-000005", "2026-08-14"))


if __name__ == "__main__":
    unittest.main()
