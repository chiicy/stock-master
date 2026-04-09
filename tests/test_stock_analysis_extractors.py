from __future__ import annotations

import unittest

from stock_master.analysis.extractors import extract_closes_and_volumes, extract_ohlcv_series, extract_rows, pick


class StockAnalysisExtractorTests(unittest.TestCase):
    def test_pick_returns_first_meaningful_key(self) -> None:
        payload = {'a': '', 'b': None, 'c': 3}

        self.assertEqual(pick(payload, 'a', 'b', 'c', default=0), 3)

    def test_extract_rows_supports_list_and_container_dict(self) -> None:
        items = [{'x': 1}, {'x': 2}]

        self.assertEqual(extract_rows(items), items)
        self.assertEqual(extract_rows({'rows': items}), items)
        self.assertEqual(extract_rows({'items': items}), items)
        self.assertEqual(extract_rows({'value': items}), [])

    def test_extract_closes_and_volumes_skips_invalid_rows(self) -> None:
        kline = {
            'items': [
                {'close': '10.5', 'volume': '100'},
                {'收盘': 11.2, '成交量': 130},
                {'close': 'bad-number', 'volume': 200},
                {'close': 12.0},
            ]
        }

        closes, volumes, rows = extract_closes_and_volumes(kline)

        self.assertEqual(rows[0]['close'], '10.5')
        self.assertEqual(closes, [10.5, 11.2, 12.0])
        self.assertEqual(volumes, [100.0, 130.0])

    def test_extract_ohlcv_series_keeps_high_low_close_aligned(self) -> None:
        kline = {
            'items': [
                {'high': '10.8', 'low': '9.9', 'close': '10.5', 'volume': '100'},
                {'low': 10.4, 'close': 11.2, 'volume': 120},
                {'high': 12.6, 'low': 11.8, 'close': 12.1, 'volume': 150},
            ]
        }

        highs, lows, closes, volumes, rows = extract_ohlcv_series(kline)

        self.assertEqual(highs, [10.8, 12.6])
        self.assertEqual(lows, [9.9, 11.8])
        self.assertEqual(closes, [10.5, 12.1])
        self.assertEqual(volumes, [100.0, 150.0])
        self.assertEqual(len(rows), 2)


if __name__ == '__main__':
    unittest.main()
