from __future__ import annotations

import unittest

from stock_master.analysis.indicators import calc_macd, calc_ma, calc_rsi, calc_volume_ratio, find_support_resistance


class StockAnalysisIndicatorsTests(unittest.TestCase):
    def test_calc_ma_returns_recent_average(self) -> None:
        self.assertEqual(calc_ma([1, 2, 3, 4, 5], 3), 4.0)

    def test_calc_rsi_handles_all_gains(self) -> None:
        self.assertEqual(calc_rsi(list(range(1, 17))), 100.0)

    def test_calc_macd_returns_payload_for_long_series(self) -> None:
        payload = calc_macd([float(index) for index in range(1, 60)])

        self.assertIn('dif', payload)
        self.assertIn('dea', payload)
        self.assertIn('hist', payload)

    def test_volume_ratio_and_support_resistance(self) -> None:
        volumes = [100.0 + index for index in range(25)]
        prices = [10.0 + index for index in range(25)]

        self.assertIsNotNone(calc_volume_ratio(volumes))
        self.assertEqual(find_support_resistance(prices), {'support': 15.0, 'resistance': 34.0, 'last': 34.0})


if __name__ == '__main__':
    unittest.main()
