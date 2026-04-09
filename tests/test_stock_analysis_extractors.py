from __future__ import annotations

import unittest

from stock_master.analysis.extractors import extract_closes_and_volumes, extract_rows, pick


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


if __name__ == '__main__':
    unittest.main()
