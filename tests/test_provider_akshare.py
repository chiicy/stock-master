from __future__ import annotations

import unittest
from typing import Any

from stock_master.datasource.providers.akshare import AkshareProvider


class BackendStub:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls: list[tuple[str, str, dict[str, Any], int]] = []

    def run_module_json(self, module: str, action: str, payload: dict[str, Any], timeout: int = 90) -> Any:
        self.calls.append((module, action, payload, timeout))
        return self.response


class AkshareProviderTests(unittest.TestCase):
    def test_quote_uses_module_runner_and_normalizes_symbol(self) -> None:
        backend = BackendStub({'price': 1})
        provider = AkshareProvider(backend, True)

        result = provider.get_quote('603966')

        self.assertEqual(result['price'], 1)
        self.assertEqual(
            backend.calls,
            [('stock_master.datasource.providers.akshare', 'get_quote', {'symbol': 'SH603966'}, 90)],
        )

    def test_kline_uses_code_only_symbol(self) -> None:
        backend = BackendStub({'items': [{'close': 1}]})
        provider = AkshareProvider(backend, True)

        result = provider.get_kline('SH603966', 20)

        self.assertEqual(result['items'][0]['close'], 1)
        self.assertEqual(
            backend.calls,
            [('stock_master.datasource.providers.akshare', 'get_kline', {'symbol': '603966', 'days': 20}, 90)],
        )

    def test_error_payload_becomes_false(self) -> None:
        provider = AkshareProvider(BackendStub({'error': 'boom'}), True)

        self.assertFalse(provider.get_financial('603966'))

    def test_new_deep_fundamental_calls_are_routed(self) -> None:
        backend = BackendStub({'status': 'ok', 'rows': [{'REPORT_DATE_NAME': '2024年报'}]})
        provider = AkshareProvider(backend, True)

        result = provider.get_income_statement('603966', 'yearly')

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(
            backend.calls,
            [('stock_master.datasource.providers.akshare', 'get_income_statement', {'symbol': 'SH603966', 'period': 'yearly'}, 180)],
        )


if __name__ == '__main__':
    unittest.main()
