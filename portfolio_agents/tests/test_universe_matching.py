import unittest

from portfolio_agents.universe import Instrument, Universe, _issuer_key


class UniverseMatchingTest(unittest.TestCase):
    def setUp(self):
        self.universe = Universe([
            Instrument("TGT.US", "TGT", "Target Corp", (), "", "equity", "TGT"),
            Instrument("NYT.US", "NYT", "New York Times Co", (), "", "equity", "NYT"),
        ])

    def test_single_word_issuer_name_is_not_a_news_phrase(self):
        # "Target" to zwykłe słowo; bez aliasu nie może wskazywać spółki w każdym artykule.
        self.assertEqual(self.universe.match_text("Target shares rise at store openings"), set())

    def test_full_name_still_matches(self):
        self.assertEqual(self.universe.match_text("Target Corp reports earnings"), {"TGT"})

    def test_issuer_key_strips_only_trailing_suffixes(self):
        self.assertEqual(_issuer_key("New York Times Co"), "NEW YORK TIMES")
        self.assertEqual(_issuer_key("The Coca-Cola Company"), "COCA COLA")

    def test_issuer_lookup_for_13f_names_still_works(self):
        self.assertEqual(self.universe.match_issuer("TARGET CORP"), "TGT")


if __name__ == "__main__":
    unittest.main()
