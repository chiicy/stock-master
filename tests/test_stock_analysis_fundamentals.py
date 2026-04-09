from __future__ import annotations

import unittest

from stock_master.analysis.fundamentals import (
    analyze_dupont,
    build_detective_readiness,
    calc_cagr,
    calc_cash_conversion_ratio,
    calc_dcf,
    calc_days_inventory_outstanding,
    calc_days_sales_outstanding,
    calc_free_cash_flow,
    calc_margin,
    calc_net_debt,
    calc_net_debt_ratio,
    calc_peg,
    calc_roe,
    safe_div,
)


class StockAnalysisFundamentalsTests(unittest.TestCase):
    def test_safe_div_and_roe(self) -> None:
        self.assertEqual(safe_div(10, 2), 5.0)
        self.assertEqual(calc_roe(12, 3), 4.0)
        self.assertIsNone(safe_div(10, 0))

    def test_cagr_and_dcf(self) -> None:
        self.assertAlmostEqual(calc_cagr([100, 121], years=2) or 0.0, 0.1, places=6)
        self.assertAlmostEqual(calc_dcf([100, 100], 0.1) or 0.0, 173.553719, places=5)

    def test_peg_and_dupont(self) -> None:
        self.assertEqual(calc_peg(20, 0.2), 1.0)
        self.assertTrue(analyze_dupont(0.2, 0.1, 1.1, 2.0)['complete'])
        self.assertFalse(analyze_dupont(0.2, None, 1.1, 2.0)['complete'])

    def test_value_detective_helper_metrics(self) -> None:
        self.assertEqual(calc_margin(20, 100), 0.2)
        self.assertAlmostEqual(calc_days_sales_outstanding(365, 10) or 0.0, 10.0, places=6)
        self.assertAlmostEqual(calc_days_inventory_outstanding(365, 5) or 0.0, 5.0, places=6)
        self.assertEqual(calc_cash_conversion_ratio(120, 100), 1.2)
        self.assertEqual(calc_free_cash_flow(100, 30), 70.0)
        self.assertEqual(calc_net_debt(80, 20), 60.0)
        self.assertEqual(calc_net_debt_ratio(80, 20, 120), 0.5)

    def test_build_detective_readiness_summarizes_ready_and_missing_items(self) -> None:
        readiness = build_detective_readiness(
            {
                '利润表': True,
                '资产负债表': True,
                '现金流量表': False,
                '同业对比': False,
            }
        )

        self.assertEqual(readiness['label'], '部分完整')
        self.assertIn('利润表', readiness['ready_items'])
        self.assertIn('现金流量表', readiness['missing_items'])


if __name__ == '__main__':
    unittest.main()
