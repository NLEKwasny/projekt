import tempfile
import unittest
from pathlib import Path

from portfolio_agents import xtb_export
from portfolio_agents.universe import Universe, Instrument

RECORDS = [
    {"symbol": "FIXA.US", "description": "Fixture Alpha Corp", "categoryName": "STC", "groupName": "Stocks"},
    {"symbol": "FIXB.US", "description": "Fixture Beta ETF", "categoryName": "ETF", "groupName": "ETF"},
]


class Scripted:
    """Transport z ustaloną odpowiedzią na każdą komendę. Wyjątek w odpowiedzi = błąd transportu."""

    def __init__(self, responses):
        self.responses = responses
        self.commands: list[str] = []

    def send(self, payload):
        self.commands.append(payload["command"])
        result = self.responses[payload["command"]]
        if isinstance(result, Exception):
            raise result
        return result

    def close(self):
        pass


def _ok(**extra):
    return {"status": True, **extra}


class LogoutTest(unittest.TestCase):
    def test_logout_transport_error_keeps_fetched_records(self):
        transport = Scripted({
            "login": _ok(), "getAllSymbols": _ok(returnData=RECORDS),
            "logout": TimeoutError("socket timeout"),
        })
        records = xtb_export.fetch_symbols(transport, "1", "pw")
        self.assertEqual(len(records), 2)

    def test_logout_transport_error_does_not_mask_xapi_error(self):
        transport = Scripted({
            "login": _ok(), "getAllSymbols": {"status": False, "errorCode": "EX001", "errorDescr": "nope"},
            "logout": TimeoutError("socket timeout"),
        })
        with self.assertRaises(xtb_export.XtbError) as ctx:
            xtb_export.fetch_symbols(transport, "1", "pw")
        self.assertIn("EX001", str(ctx.exception))


class ShapeTest(unittest.TestCase):
    def test_return_data_must_be_list_of_objects(self):
        for bad in ({"symbols": RECORDS}, "FIXA.US", [1, 2], None):
            transport = Scripted({"login": _ok(), "getAllSymbols": _ok(returnData=bad), "logout": _ok()})
            with self.subTest(bad=bad), self.assertRaises(xtb_export.XtbError):
                xtb_export.fetch_symbols(transport, "1", "pw")

    def test_null_fields_do_not_become_the_string_none(self):
        rows = xtb_export.build_rows([
            {"symbol": None, "description": None},
            {"symbol": "FIXC.US", "description": None},
        ])
        self.assertEqual([r["symbol"] for r in rows], ["FIXC.US"])
        self.assertEqual(rows[0]["name"], "")

    def test_symbol_without_alphanumerics_is_skipped(self):
        self.assertEqual(xtb_export.build_rows([{"symbol": "..."}]), [])


class CollisionTest(unittest.TestCase):
    def test_equity_beats_cfd_with_same_ticker(self):
        rows = xtb_export.build_rows([
            {"symbol": "FIXZ", "description": "Fixture CFD"},
            {"symbol": "FIXZ.DE", "description": "Fixture Zeta (DE)"},
        ])
        self.assertEqual([(r["symbol"], r["asset_type"]) for r in rows], [("FIXZ.DE", "equity")])


class EmptyResultTest(unittest.TestCase):
    def test_empty_result_refuses_to_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "xtb_universe.csv"
            out.write_text("symbol,ticker\nKEEP.US,KEEP\n", encoding="utf-8")
            transport = Scripted({"login": _ok(), "getAllSymbols": _ok(returnData=[]), "logout": _ok()})
            code = xtb_export.run_export(transport, "1", "pw", out)
            self.assertEqual(code, 1)
            self.assertIn("KEEP.US", out.read_text(encoding="utf-8"))

    def test_successful_run_writes_file_and_removes_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "xtb_universe.csv"
            transport = Scripted({"login": _ok(), "getAllSymbols": _ok(returnData=RECORDS), "logout": _ok()})
            self.assertEqual(xtb_export.run_export(transport, "1", "pw", out), 0)
            self.assertTrue(out.exists())
            self.assertFalse((Path(tmp) / "xtb_universe.csv.tmp").exists())

    def test_lone_surrogate_in_name_does_not_break_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "xtb_universe.csv"
            rows = xtb_export.build_rows([{"symbol": "FIXD.US", "description": "Bad \ud800 name"}])
            xtb_export.write_csv(rows, out)
            self.assertTrue(out.exists())


class ClassificationRegressionTest(unittest.TestCase):
    def test_cfd_index_with_digits_does_not_match_equity_ticker(self):
        universe = Universe([
            Instrument("DE.US", "DE", "Deere & Co", ("Deere",), "", "equity", "DE"),
            Instrument("DE40", "DE40", "Germany 40 Index", (), "", "other", ""),
        ])
        self.assertEqual(universe.match_text("DE40 index falls sharply"), {"DE40"})
        self.assertEqual(universe.match_text("Deere cuts guidance"), {"DE"})


if __name__ == "__main__":
    unittest.main()
