from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from stock_master.common.cache import cache_get, cache_set
from stock_master.common.symbols import code_only, normalize_symbol


class StockCommonTests(unittest.TestCase):
    def test_normalize_symbol_and_code_only(self) -> None:
        self.assertEqual(normalize_symbol('603966'), 'SH603966')
        self.assertEqual(normalize_symbol('000001'), 'SZ000001')
        self.assertEqual(code_only('SH603966'), '603966')

    def test_cache_round_trip_and_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_set('quote', {'price': 1}, cache_dir=temp_dir)
            self.assertEqual(cache_get('quote', ttl_seconds=60, cache_dir=temp_dir), {'price': 1})

            path = Path(temp_dir) / 'quote.json'
            path.write_text('{"_ts": 1, "data": {"price": 2}}')
            self.assertIsNone(cache_get('quote', ttl_seconds=1, cache_dir=temp_dir))


if __name__ == '__main__':
    unittest.main()
