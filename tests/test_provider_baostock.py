from __future__ import annotations

import unittest
from typing import Any

from stock_master.datasource.providers.baostock import BaoStockProvider


class BackendStub:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls: list[tuple[str, str, dict[str, Any], int]] = []

    def run_module_json(self, module: str, action: str, payload: dict[str, Any], timeout: int = 90) -> Any:
        self.calls.append((module, action, payload, timeout))
        return self.response


class BaoStockProviderTests(unittest.TestCase):
    def test_quote_uses_baostock_symbol(self) -> None:
        backend = BackendStub({'price': 1})
        provider = BaoStockProvider(backend, True)

        result = provider.get_quote('603966')

        self.assertEqual(result['price'], 1)
        self.assertEqual(
            backend.calls,
            [('stock_master.datasource.providers.baostock', 'get_quote', {'symbol': 'sh.603966'}, 120)],
        )

    def test_kline_sends_symbol_and_code(self) -> None:
        backend = BackendStub({'items': [{'close': 1}]})
        provider = BaoStockProvider(backend, True)

        provider.get_kline('SZ000001', 10)

        self.assertEqual(
            backend.calls,
            [('stock_master.datasource.providers.baostock', 'get_kline', {'symbol': 'sz.000001', 'code': '000001', 'days': 10}, 120)],
        )

    def test_unavailable_provider_short_circuits(self) -> None:
        provider = BaoStockProvider(BackendStub({'price': 1}), False)

        self.assertFalse(provider.get_search('603966'))


if __name__ == '__main__':
    unittest.main()
