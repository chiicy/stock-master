from __future__ import annotations

import unittest

from stock_master.analysis.intents import (
    INTENT_MARKET,
    INTENT_SECTOR,
    INTENT_STOCK,
    MODE_DEEP_FUNDAMENTAL,
    MODE_DEEP_TECHNICAL,
    parse_analysis_intent,
)


class AnalysisIntentTests(unittest.TestCase):
    def test_numeric_symbol_routes_to_stock_report(self) -> None:
        intent = parse_analysis_intent('603966')

        self.assertEqual(intent.kind, INTENT_STOCK)
        self.assertEqual(intent.symbol, 'SH603966')

    def test_market_query_routes_to_market_overview(self) -> None:
        intent = parse_analysis_intent('今天A股市场怎么样')

        self.assertEqual(intent.kind, INTENT_MARKET)
        self.assertTrue(intent.wants_market_context)

    def test_sector_query_routes_to_sector_overview(self) -> None:
        intent = parse_analysis_intent('AI板块轮动怎么看')

        self.assertEqual(intent.kind, INTENT_SECTOR)
        self.assertTrue(intent.wants_sector_context)
        self.assertTrue(intent.wants_market_context)

    def test_stock_name_query_still_routes_to_stock_report(self) -> None:
        intent = parse_analysis_intent('平安银行财报怎么看')

        self.assertEqual(intent.kind, INTENT_STOCK)
        self.assertEqual(intent.search_query, '平安银行财报怎么看')

    def test_deep_technical_query_extracts_symbol_and_mode(self) -> None:
        intent = parse_analysis_intent('像虾评一样分析 603966，看看支撑位压力位和未来三天')

        self.assertEqual(intent.kind, INTENT_STOCK)
        self.assertEqual(intent.symbol, 'SH603966')
        self.assertEqual(intent.mode, MODE_DEEP_TECHNICAL)

    def test_deep_fundamental_query_marks_non_a_share_as_unsupported(self) -> None:
        intent = parse_analysis_intent('用价值投资方法深度分析 AAPL，做 DCF 和 ROIC/WACC')

        self.assertEqual(intent.kind, INTENT_STOCK)
        self.assertEqual(intent.mode, MODE_DEEP_FUNDAMENTAL)
        self.assertFalse(intent.supported)
        self.assertIn('仅面向 A 股', '；'.join(intent.notes))


if __name__ == '__main__':
    unittest.main()
