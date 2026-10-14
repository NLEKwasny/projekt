import unittest

from portfolio_agents.technicals import closes_from_chart, rsi, sma


class TechnicalsTest(unittest.TestCase):
    def test_sma_uses_last_n_values(self):
        self.assertEqual(sma([1, 2, 3, 4, 5], 3), 4.0)
        self.assertIsNone(sma([1, 2], 3))

    def test_rsi_extremes(self):
        rising = [float(i) for i in range(1, 40)]
        falling = [float(100 - i) for i in range(40)]
        self.assertEqual(rsi(rising), 100.0)
        self.assertEqual(rsi(falling), 0.0)
        self.assertIsNone(rsi([1.0] * 10))

    def test_closes_skip_missing_values(self):
        payload = {"chart": {"result": [{"indicators": {"quote": [{"close": [10.0, None, 12.5]}]}}]}}
        self.assertEqual(closes_from_chart(payload), [10.0, 12.5])


if __name__ == "__main__":
    unittest.main()
