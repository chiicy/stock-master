from __future__ import annotations

import unittest
from typing import Any

from stock_master.datasource.providers.adata import AdataProvider


class BackendStub:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls: list[tuple[str, str, dict[str, Any], int]] = []

    def run_module_json(self, module: str, action: str, payload: dict[str, Any], timeout: int = 90) -> Any:
        self.calls.append((module, action, payload, timeout))
        return self.response


class AdataProviderTests(unittest.TestCase):
    def test_search_calls_own_module(self) -> None:
        backend = BackendStub({'items': [{'代码': '603966'}]})
        provider = AdataProvider(backend, True)

        result = provider.get_search('603966')

        self.assertEqual(result['items'][0]['代码'], '603966')
        self.assertEqual(result['capability'], 'search')
        self.assertEqual(result['items'][0]['kind'], 'search_result')
        self.assertEqual(
            backend.calls,
            [('stock_master.datasource.providers.adata', 'get_search', {'query': '603966'}, 90)],
        )

    def test_financial_uses_secucode(self) -> None:
        backend = BackendStub({'status': 'ok', 'rows': []})
        provider = AdataProvider(backend, True)

        result = provider.get_financial('603966')

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['capability'], 'financial')
        self.assertEqual(result['source_channel'], 'adata.financial')
        self.assertEqual(
            backend.calls,
            [('stock_master.datasource.providers.adata', 'get_financial', {'symbol': '603966.SH'}, 90)],
        )

    def test_empty_payload_returns_false(self) -> None:
        provider = AdataProvider(BackendStub({'status': 'empty'}), True)

        self.assertFalse(provider.get_quote('603966'))


if __name__ == '__main__':
    unittest.main()
