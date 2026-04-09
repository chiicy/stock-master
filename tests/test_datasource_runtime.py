from __future__ import annotations

import time
import unittest
from typing import Any

from stock_master.datasource.interface import StockDataProvider
from stock_master.datasource.runtime import ProviderRouter, is_provider_success


class FakeProvider(StockDataProvider):
    def __init__(self, name: str, **behaviors: Any) -> None:
        self.name = name
        self.available = True
        self.behaviors = behaviors

    def _dispatch(self, capability: str, *args: Any) -> Any:
        behavior = self.behaviors.get(capability, False)
        if callable(behavior):
            return behavior(*args)
        return behavior

    def get_search(self, query: str) -> Any:
        return self._dispatch('get_search', query)

    def get_quote(self, symbol: str) -> Any:
        return self._dispatch('get_quote', symbol)

    def get_kline(self, symbol: str, days: int = 120) -> Any:
        return self._dispatch('get_kline', symbol, days)

    def get_news(self, symbol: str | None = None) -> Any:
        return self._dispatch('get_news', symbol)

    def get_research(self, symbol: str) -> Any:
        return self._dispatch('get_research', symbol)

    def get_announcements(self, symbol: str, days: int = 180) -> Any:
        return self._dispatch('get_announcements', symbol, days)

    def get_sector_members(self, sector_code: str) -> Any:
        return self._dispatch('get_sector_members', sector_code)


class ProviderRuntimeTests(unittest.TestCase):
    def test_false_payload_is_not_success(self) -> None:
        self.assertFalse(is_provider_success(False))

    def test_placeholder_payload_is_success(self) -> None:
        self.assertTrue(is_provider_success({'status': 'placeholder'}))

    def test_router_falls_back_after_false(self) -> None:
        router = ProviderRouter(
            [
                FakeProvider('akshare', get_quote=False),
                FakeProvider('opencli', get_quote={'price': 10.2}),
            ],
            per_provider_timeout=0.2,
        )

        result = router.dispatch('get_quote', 'SH603966')

        self.assertEqual(result['source'], 'opencli')
        self.assertEqual(result['fallback_path'], ['akshare', 'opencli'])
        self.assertEqual(result['price'], 10.2)

    def test_router_handles_provider_exception(self) -> None:
        def explode(symbol: str) -> Any:
            raise RuntimeError('boom')

        router = ProviderRouter(
            [
                FakeProvider('akshare', get_quote=explode),
                FakeProvider('adata', get_quote={'price': 9.9}),
            ],
            per_provider_timeout=0.2,
        )

        result = router.dispatch('get_quote', 'SH603966')

        self.assertEqual(result['source'], 'adata')
        self.assertEqual(result['fallback_path'], ['akshare', 'adata'])

    def test_router_handles_timeout_as_false(self) -> None:
        def slow(symbol: str) -> Any:
            time.sleep(0.2)
            return {'price': 1}

        router = ProviderRouter(
            [
                FakeProvider('slow', get_quote=slow),
                FakeProvider('fast', get_quote={'price': 2}),
            ],
            per_provider_timeout=0.05,
        )

        result = router.dispatch('get_quote', 'SH603966')

        self.assertEqual(result['source'], 'fast')
        self.assertEqual(result['fallback_path'], ['slow', 'fast'])
        self.assertEqual(result['price'], 2)

    def test_router_returns_empty_after_all_providers_fail(self) -> None:
        router = ProviderRouter(
            [
                FakeProvider('akshare', get_kline=False),
                FakeProvider('adata', get_kline=False),
            ],
            per_provider_timeout=0.05,
        )

        result = router.dispatch('get_kline', 'SH603966', 20)

        self.assertEqual(result['status'], 'empty')
        self.assertEqual(result['fallback_path'], ['akshare', 'adata'])

    def test_router_skips_unavailable_providers_in_path(self) -> None:
        disabled = FakeProvider('disabled', get_quote={'price': 1})
        disabled.available = False
        router = ProviderRouter(
            [
                disabled,
                FakeProvider('opencli', get_quote={'price': 2}),
            ],
            per_provider_timeout=0.05,
        )

        result = router.dispatch('get_quote', 'SH603966')

        self.assertEqual(result['source'], 'opencli')
        self.assertEqual(result['fallback_path'], ['opencli'])

    def test_first_success_stops_after_first_provider_success(self) -> None:
        calls = {'first': 0, 'second': 0}

        def first(symbol: str) -> Any:
            calls['first'] += 1
            return {'price': 12.3}

        def second(symbol: str) -> Any:
            calls['second'] += 1
            return {'price': 99.9}

        router = ProviderRouter(
            [
                FakeProvider('akshare', get_quote=first),
                FakeProvider('adata', get_quote=second),
            ],
            per_provider_timeout=0.05,
        )

        result = router.dispatch('get_quote', 'SH603966', strategy='first_success')

        self.assertEqual(result['source'], 'akshare')
        self.assertEqual(result['price'], 12.3)
        self.assertEqual(calls, {'first': 1, 'second': 0})

    def test_dispatch_uses_explicit_provider_sequence_and_routing_hint(self) -> None:
        calls: list[str] = []

        def second(symbol: str) -> Any:
            calls.append('second')
            return {'price': 8.8}

        def first(symbol: str) -> Any:
            calls.append('first')
            return {'price': 9.9}

        provider_first = FakeProvider('first', get_quote=first)
        provider_second = FakeProvider('second', get_quote=second)
        router = ProviderRouter([provider_first, provider_second], per_provider_timeout=0.05)

        result = router.dispatch(
            'get_quote',
            'AAPL',
            providers=[provider_second, provider_first],
            routing_hint={'market': 'global', 'capability': 'get_quote'},
        )

        self.assertEqual(calls, ['second'])
        self.assertEqual(result['source'], 'second')
        self.assertEqual(result['routing_hint']['market'], 'global')

    def test_first_success_skips_insufficient_quote_payload(self) -> None:
        router = ProviderRouter(
            [
                FakeProvider('opencli-xq', get_quote={'symbol': 'SH603966', 'name': '法兰泰克'}),
                FakeProvider('akshare', get_quote={'price': 10.2}),
            ],
            per_provider_timeout=0.05,
        )

        result = router.dispatch('get_quote', 'SH603966')

        self.assertEqual(result['source'], 'akshare')
        self.assertEqual(result['fallback_path'], ['opencli-xq', 'akshare'])

    def test_first_success_skips_insufficient_search_payload(self) -> None:
        router = ProviderRouter(
            [
                FakeProvider('opencli-dc', get_search={'query': '603966'}),
                FakeProvider('opencli-xq', get_search={'items': [{'symbol': 'SH603966'}]}),
            ],
            per_provider_timeout=0.05,
        )

        result = router.dispatch('get_search', '603966')

        self.assertEqual(result['source'], 'opencli-xq')
        self.assertEqual(result['fallback_path'], ['opencli-dc', 'opencli-xq'])

    def test_merge_strategy_calls_multiple_providers_and_merges_items(self) -> None:
        router = ProviderRouter(
            [
                FakeProvider('akshare', get_news={'status': 'ok', 'items': [{'id': 'a'}, {'id': 'b'}]}),
                FakeProvider('opencli', get_news={'status': 'ok', 'items': [{'id': 'c'}]}),
            ],
            per_provider_timeout=0.05,
        )

        result = router.dispatch('get_news', 'SH603966', strategy='merge')

        self.assertEqual(result['source'], 'merged')
        self.assertEqual(result['sources'], ['akshare', 'opencli'])
        self.assertEqual(result['fallback_path'], ['akshare', 'opencli'])
        self.assertEqual(result['items'], [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}])

    def test_merge_strategy_returns_success_when_some_providers_fail(self) -> None:
        router = ProviderRouter(
            [
                FakeProvider('akshare', get_research=False),
                FakeProvider('adata', get_research={'status': 'ok', 'rows': [{'title': 'coverage'}]}),
                FakeProvider('opencli', get_research=False),
            ],
            per_provider_timeout=0.05,
        )

        result = router.dispatch('get_research', 'SH603966', strategy='merge')

        self.assertEqual(result['source'], 'merged')
        self.assertEqual(result['sources'], ['adata'])
        self.assertEqual(result['fallback_path'], ['akshare', 'adata', 'opencli'])
        self.assertEqual(result['rows'], [{'title': 'coverage'}])

    def test_merge_strategy_deduplicates_rows(self) -> None:
        router = ProviderRouter(
            [
                FakeProvider('akshare', get_announcements={'status': 'ok', 'rows': [{'title': '公告', 'date': '2025-01-01'}]}),
                FakeProvider(
                    'opencli',
                    get_announcements={
                        'status': 'ok',
                        'rows': [
                            {'date': '2025-01-01', 'title': '公告'},
                            {'title': '补充公告', 'date': '2025-01-02'},
                        ],
                    },
                ),
            ],
            per_provider_timeout=0.05,
        )

        result = router.dispatch('get_announcements', 'SH603966', 30, strategy='merge')

        self.assertEqual(result['source'], 'merged')
        self.assertEqual(
            result['rows'],
            [
                {'title': '补充公告', 'date': '2025-01-02'},
                {'title': '公告', 'date': '2025-01-01'},
            ],
        )


if __name__ == '__main__':
    unittest.main()
