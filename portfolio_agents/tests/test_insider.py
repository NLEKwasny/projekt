import unittest

from portfolio_agents.agents.insider import filing_url, parse_form4, trade_to_event

FORM4 = b"""<?xml version="1.0"?>
<ownershipDocument>
  <issuer>
    <issuerCik>0001849635</issuerCik>
    <issuerName>Trump Media &amp; Technology Group Corp.</issuerName>
    <issuerTradingSymbol>DJT</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>Trump Donald J</rptOwnerName></reportingOwnerId>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>2026-10-10</value></transactionDate>
      <transactionCoding><transactionFormType>4</transactionFormType><transactionCode>P</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>10000</value></transactionShares>
        <transactionPricePerShare><value>25.50</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <transactionDate><value>2026-10-10</value></transactionDate>
      <transactionCoding><transactionFormType>4</transactionFormType><transactionCode>M</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>500</value></transactionShares>
        <transactionPricePerShare><value>0</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <transactionDate><value>2026-10-11</value></transactionDate>
      <transactionCoding><transactionFormType>4</transactionFormType><transactionCode>S</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>2000</value></transactionShares>
        <transactionPricePerShare><value>24.00</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""


class InsiderTest(unittest.TestCase):
    def test_parse_reads_issuer_owner_and_transactions(self):
        trades = parse_form4(FORM4)
        self.assertEqual(len(trades), 3)
        buy = trades[0]
        self.assertEqual((buy.ticker, buy.owner, buy.code, buy.acq_disp), ("DJT", "Trump Donald J", "P", "A"))
        self.assertEqual((buy.shares, buy.price), (10000.0, 25.5))
        self.assertEqual(trades[2].code, "S")

    def test_purchase_becomes_bullish_event_and_option_exercise_is_ignored(self):
        trades = parse_form4(FORM4)
        self.assertIsNone(trade_to_event(trades[1], "0001-26-000001", 1))
        event = trade_to_event(trades[0], "0001-26-000001", 0)
        self.assertEqual(event.direction, 1)
        self.assertEqual(event.source, "insider")
        self.assertTrue(0.7 < event.strength < 0.8)  # ok. 255 tys. USD

    def test_sale_becomes_bearish_event(self):
        event = trade_to_event(parse_form4(FORM4)[2], "0001-26-000001", 2)
        self.assertEqual(event.direction, -1)

    def test_filing_url_strips_xsl_directory(self):
        url = filing_url("0001849635", "0001234567-26-000123", "xslF345X05/wk-form4.xml")
        self.assertEqual(url, "https://www.sec.gov/Archives/edgar/data/1849635/000123456726000123/wk-form4.xml")


if __name__ == "__main__":
    unittest.main()
