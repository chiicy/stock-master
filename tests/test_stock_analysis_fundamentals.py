from __future__ import annotations

import unittest

from stock_master.analysis.fundamentals import analyze_dupont, calc_cagr, calc_dcf, calc_peg, calc_roe, safe_div


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


if __name__ == '__main__':
    unittest.main()
