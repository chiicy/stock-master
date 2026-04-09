from __future__ import annotations

import unittest
import time
from typing import Any

from stock_master.datasource import DataSource
from stock_master.datasource.interface import StockDataProvider


class StubBackend:
    def __init__(self) -> None:
        self.opencli_available = False

    def check_module(self, name: str) -> bool:
        return False


class MemoryCache:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}

    def get(self, key: str, ttl_seconds: int = 60) -> Any:
        return self.data.get(key)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value


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

    def get_money_flow(self, symbol: str) -> Any:
        return self._dispatch('get_money_flow', symbol)

    def get_north_flow(self) -> Any:
        return self._dispatch('get_north_flow')

    def get_sector_money_flow(self) -> Any:
        return self._dispatch('get_sector_money_flow')

    def get_financial(self, symbol: str) -> Any:
        return self._dispatch('get_financial', symbol)

    def get_report(self, symbol: str) -> Any:
        return self._dispatch('get_report', symbol)

    def get_income_statement(self, symbol: str, period: str = 'yearly') -> Any:
        return self._dispatch('get_income_statement', symbol, period)

    def get_balance_sheet(self, symbol: str, period: str = 'yearly') -> Any:
        return self._dispatch('get_balance_sheet', symbol, period)

    def get_cash_flow(self, symbol: str, period: str = 'yearly') -> Any:
        return self._dispatch('get_cash_flow', symbol, period)

    def get_announcements(self, symbol: str, days: int = 180) -> Any:
        return self._dispatch('get_announcements', symbol, days)

    def get_main_holders(self, symbol: str) -> Any:
        return self._dispatch('get_main_holders', symbol)

    def get_shareholder_changes(self, symbol: str) -> Any:
        return self._dispatch('get_shareholder_changes', symbol)

    def get_dividend(self, symbol: str) -> Any:
        return self._dispatch('get_dividend', symbol)

    def get_sector_list(self) -> Any:
        return self._dispatch('get_sector_list')

    def get_sector_members(self, sector_code: str) -> Any:
        return self._dispatch('get_sector_members', sector_code)

    def get_limit_up(self, date: str | None = None) -> Any:
        return self._dispatch('get_limit_up', date)

    def get_limit_down(self, date: str | None = None) -> Any:
        return self._dispatch('get_limit_down', date)

    def get_news(self, symbol: str | None = None) -> Any:
        return self._dispatch('get_news', symbol)

    def get_research(self, symbol: str) -> Any:
        return self._dispatch('get_research', symbol)


class DataSourceServiceTests(unittest.TestCase):
    def make_ds(
        self,
        providers: list[StockDataProvider],
        *,
        provider_available: dict[str, bool] | None = None,
        cache_enabled: bool = True,
        per_source_timeout: float = 0.1,
    ) -> tuple[DataSource, MemoryCache]:
        cache = MemoryCache()
        ds = DataSource(
            backend=StubBackend(),
            provider_available=provider_available or {},
            providers=providers,
            cache_reader=cache.get,
            cache_writer=cache.set,
            cache_enabled=cache_enabled,
            per_source_timeout=per_source_timeout,
        )
        return ds, cache

    def test_quote_is_cached_and_respects_priority(self) -> None:
        calls = {'first': 0, 'second': 0}

        def first(symbol: str) -> Any:
            calls['first'] += 1
            return False

        def second(symbol: str) -> Any:
            calls['second'] += 1
            return {'price': 18.8}

        ds, _ = self.make_ds(
            [
                FakeProvider('akshare', get_quote=first),
                FakeProvider('adata', get_quote=second),
            ]
        )

        first_result = ds.get_quote('603966')
        second_result = ds.get_quote('603966')

        self.assertEqual(calls, {'first': 1, 'second': 1})
        self.assertEqual(first_result['source'], 'adata')
        self.assertEqual(second_result['price'], 18.8)

    def test_routing_hint_reorders_a_share_quote_stack(self) -> None:
        calls: list[str] = []

        def yahoo(symbol: str) -> Any:
            calls.append('opencli-yahoo-finance')
            return {'regularMarketPrice': 188.3}

        def ak(symbol: str) -> Any:
            calls.append('akshare')
            return {'price': 19.9}

        ds, _ = self.make_ds(
            [
                FakeProvider('opencli-yahoo-finance', get_quote=yahoo),
                FakeProvider('akshare', get_quote=ak),
            ],
            cache_enabled=False,
        )

        result = ds.get_quote('603966')

        self.assertEqual(calls, ['akshare'])
        self.assertEqual(result['source'], 'akshare')
        self.assertEqual(result['routing_hint']['market'], 'a_share')

    def test_routing_hint_reorders_global_quote_stack(self) -> None:
        calls: list[str] = []

        def ak(symbol: str) -> Any:
            calls.append('akshare')
            return {'price': 19.9}

        def yahoo(symbol: str) -> Any:
            calls.append('opencli-yahoo-finance')
            return {'regularMarketPrice': 188.3}

        ds, _ = self.make_ds(
            [
                FakeProvider('akshare', get_quote=ak),
                FakeProvider('opencli-yahoo-finance', get_quote=yahoo),
            ],
            cache_enabled=False,
        )

        result = ds.get_quote('AAPL')

        self.assertEqual(calls, ['opencli-yahoo-finance'])
        self.assertEqual(result['source'], 'opencli-yahoo-finance')
        self.assertEqual(result['routing_hint']['market'], 'global')

    def test_search_prefers_iwc_for_natural_language_query(self) -> None:
        calls: list[str] = []

        def dc(query: str) -> Any:
            calls.append('opencli-dc')
            return {'items': [{'symbol': 'SH603966'}]}

        def iwc(query: str) -> Any:
            calls.append('opencli-iwc')
            return {'items': [{'title': query, 'answer': '偏多'}]}

        ds, _ = self.make_ds(
            [
                FakeProvider('opencli-dc', get_search=dc),
                FakeProvider('opencli-iwc', get_search=iwc),
            ],
            cache_enabled=False,
        )

        result = ds.get_search('现在市场情绪怎么样？')

        self.assertEqual(calls, ['opencli-iwc'])
        self.assertEqual(result['source'], 'opencli-iwc')
        self.assertEqual(result['routing_hint']['query_shape'], 'natural_language')

    def test_snapshot_uses_quote_short_circuit_and_global_routing(self) -> None:
        calls: list[str] = []

        def ak(symbol: str) -> Any:
            calls.append('akshare')
            return {'price': 19.9}

        def yahoo(symbol: str) -> Any:
            calls.append('opencli-yahoo-finance')
            return {'regularMarketPrice': 188.3}

        ds, _ = self.make_ds(
            [
                FakeProvider('akshare', get_quote=ak),
                FakeProvider('opencli-yahoo-finance', get_quote=yahoo),
            ],
            cache_enabled=False,
        )

        result = ds.get_snapshot('AAPL')

        self.assertEqual(calls, ['opencli-yahoo-finance'])
        self.assertEqual(result['source'], 'opencli-yahoo-finance')
        self.assertEqual(result['routing_hint']['capability'], 'get_quote')

    def test_research_aggregates_multiple_sources_for_a_share_symbol(self) -> None:
        calls: list[str] = []

        def ak(symbol: str) -> Any:
            calls.append('akshare')
            return {'status': 'ok', 'items': [{'title': '券商覆盖', 'date': '2026-04-09'}]}

        def xq(symbol: str) -> Any:
            calls.append('opencli-xueqiu')
            return {'status': 'ok', 'items': [{'title': '社区观点', 'date': '2026-04-10'}]}

        ds, _ = self.make_ds(
            [
                FakeProvider('opencli-xueqiu', get_research=xq),
                FakeProvider('akshare', get_research=ak),
            ],
            cache_enabled=False,
        )

        result = ds.get_research('603966')

        self.assertEqual(calls, ['opencli-xueqiu', 'akshare'])
        self.assertEqual(result['source'], 'merged')
        self.assertEqual(result['sources'], ['opencli-xueqiu', 'akshare'])
        self.assertEqual(result['routing_hint']['market'], 'a_share')
        self.assertEqual([item['title'] for item in result['items']], ['社区观点', '券商覆盖'])

    def test_news_aggregate_uses_a_share_routing_order(self) -> None:
        calls: list[str] = []

        def bloomberg(symbol: str | None = None) -> Any:
            calls.append('opencli-bloomberg')
            return {'status': 'ok', 'items': [{'id': 'bbg'}]}

        def sina(symbol: str | None = None) -> Any:
            calls.append('opencli-sinafinance')
            return {'status': 'ok', 'items': [{'id': 'sina'}]}

        def xueqiu(symbol: str | None = None) -> Any:
            calls.append('opencli-xueqiu')
            return {'status': 'ok', 'items': [{'id': 'xq'}]}

        ds, _ = self.make_ds(
            [
                FakeProvider('opencli-bloomberg', get_news=bloomberg),
                FakeProvider('opencli-sinafinance', get_news=sina),
                FakeProvider('opencli-xueqiu', get_news=xueqiu),
            ],
            cache_enabled=False,
        )

        result = ds.get_news('603966')

        self.assertEqual(calls, ['opencli-sinafinance', 'opencli-xueqiu', 'opencli-bloomberg'])
        self.assertEqual(result['sources'], ['opencli-sinafinance', 'opencli-xueqiu', 'opencli-bloomberg'])
        self.assertEqual(result['routing_hint']['market'], 'a_share')

    def test_search_and_kline_cache_keys_are_independent(self) -> None:
        calls = {'search': 0, 'kline': 0}

        def search(query: str) -> Any:
            calls['search'] += 1
            return {'items': [{'代码': query}]}

        def kline(symbol: str, days: int) -> Any:
            calls['kline'] += 1
            return {'items': [{'close': days}]}

        ds, _ = self.make_ds(
            [FakeProvider('akshare', get_search=search, get_kline=kline)]
        )

        ds.get_search('603966')
        ds.get_search('603966')
        ds.get_kline('603966', days=5)
        ds.get_kline('603966', days=10)

        self.assertEqual(calls, {'search': 1, 'kline': 2})

    def test_flow_methods_and_aliases_work(self) -> None:
        counts = {'quote': 0, 'money': 0, 'north': 0, 'sector': 0}

        def quote(symbol: str) -> Any:
            counts['quote'] += 1
            return {'price': 9.9}

        def money(symbol: str) -> Any:
            counts['money'] += 1
            return {'items': [{'mainNetInflow': 1}]}

        def north() -> Any:
            counts['north'] += 1
            return {'items': [{'净流入': 2}]}

        def sector() -> Any:
            counts['sector'] += 1
            return {'items': [{'板块': 'AI'}]}

        ds, _ = self.make_ds(
            [
                FakeProvider(
                    'akshare',
                    get_quote=quote,
                    get_money_flow=money,
                    get_north_flow=north,
                    get_sector_money_flow=sector,
                )
            ]
        )

        intraday = ds.get_intraday('603966')
        ds.get_money_flow('603966')
        ds.get_money_flow('603966')
        ds.get_north_flow()
        ds.get_sector_money_flow()

        self.assertEqual(intraday['price'], 9.9)
        self.assertEqual(counts, {'quote': 1, 'money': 1, 'north': 1, 'sector': 1})

    def test_report_news_and_research_placeholder_paths(self) -> None:
        ds, _ = self.make_ds([FakeProvider('akshare')])

        report = ds.get_report('603966')
        news = ds.get_news('603966')
        research = ds.get_research('603966')

        self.assertEqual(report['status'], 'placeholder')
        self.assertEqual(news['status'], 'placeholder')
        self.assertEqual(research['status'], 'placeholder')
        self.assertEqual(report['fallback_path'], ['akshare'])

    def test_merge_capabilities_use_merged_strategy_in_service(self) -> None:
        call_order: list[str] = []

        def ak_news(symbol: str | None = None) -> Any:
            call_order.append('akshare')
            return {'status': 'ok', 'items': [{'id': 'news-1'}]}

        def oc_news(symbol: str | None = None) -> Any:
            call_order.append('opencli')
            return {'status': 'ok', 'items': [{'id': 'news-2'}]}

        ds, _ = self.make_ds(
            [
                FakeProvider('akshare', get_news=ak_news),
                FakeProvider('opencli', get_news=oc_news),
            ],
            cache_enabled=False,
        )

        news = ds.get_news('603966')

        self.assertEqual(call_order, ['akshare', 'opencli'])
        self.assertEqual(news['source'], 'merged')
        self.assertEqual(news['sources'], ['akshare', 'opencli'])
        self.assertEqual([item['id'] for item in news['items']], ['news-1', 'news-2'])
        self.assertEqual(news['capability'], 'news')
        self.assertEqual(news['items'][0]['kind'], 'news')

    def test_announcements_merge_deduplicates_in_service(self) -> None:
        ds, _ = self.make_ds(
            [
                FakeProvider('akshare', get_announcements={'status': 'ok', 'items': [{'id': 'same'}, {'id': 'extra'}]}),
                FakeProvider('opencli', get_announcements={'status': 'ok', 'items': [{'id': 'same'}]}),
            ],
            cache_enabled=False,
        )

        announcements = ds.get_announcements('603966', days=30)

        self.assertEqual(announcements['source'], 'merged')
        self.assertEqual(announcements['sources'], ['akshare', 'opencli'])
        self.assertEqual([item['id'] for item in announcements['items']], ['same', 'extra'])
        self.assertEqual(announcements['items'][0]['kind'], 'announcement')

    def test_aggregate_capability_runs_providers_concurrently(self) -> None:
        def slow_news(provider_name: str) -> Any:
            def worker(symbol: str | None = None) -> Any:
                time.sleep(0.18)
                return {'status': 'ok', 'items': [{'id': provider_name}]}

            return worker

        ds, _ = self.make_ds(
            [
                FakeProvider('opencli-sinafinance', get_news=slow_news('sina')),
                FakeProvider('opencli-xueqiu', get_news=slow_news('xq')),
                FakeProvider('opencli-bloomberg', get_news=slow_news('bbg')),
            ],
            cache_enabled=False,
            per_source_timeout=0.25,
        )

        start = time.perf_counter()
        news = ds.get_news('603966')
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 0.4)
        self.assertEqual(news['sources'], ['opencli-sinafinance', 'opencli-xueqiu', 'opencli-bloomberg'])

    def test_sector_helpers_use_same_router_contract(self) -> None:
        ds, _ = self.make_ds(
            [
                FakeProvider(
                    'opencli',
                    get_sector_list={'items': [{'code': 'BK0428'}]},
                    get_sector_members={'items': [{'代码': '603966'}]},
                    get_limit_up={'items': [{'symbol': 'SH603966'}]},
                    get_limit_down={'items': [{'symbol': 'SH600000'}]},
                )
            ]
        )

        sector_list = ds.get_sector_list()
        members = ds.get_sector_members('BK0428')
        limit_up = ds.get_limit_up()
        limit_down = ds.get_limit_down()

        self.assertEqual(sector_list['source'], 'opencli')
        self.assertEqual(members['items'][0]['代码'], '603966')
        self.assertEqual(limit_up['items'][0]['symbol'], 'SH603966')
        self.assertEqual(limit_down['items'][0]['symbol'], 'SH600000')

    def test_market_bundle_collects_market_level_sections(self) -> None:
        ds, _ = self.make_ds(
            [
                FakeProvider(
                    'akshare',
                    get_north_flow={'items': [{'净流入': 3}]},
                    get_sector_money_flow={'items': [{'板块': '算力'}]},
                    get_limit_up={'items': [{'symbol': 'SH603966'}]},
                    get_limit_down={'items': [{'symbol': 'SH600000'}]},
                )
            ]
        )

        bundle = ds.get_market_bundle()

        self.assertEqual(bundle['north_flow']['source'], 'akshare')
        self.assertEqual(bundle['sector_flow']['items'][0]['板块'], '算力')
        self.assertEqual(bundle['limit_up']['items'][0]['symbol'], 'SH603966')
        self.assertEqual(bundle['limit_down']['items'][0]['symbol'], 'SH600000')

    def test_get_bundle_collects_all_sections(self) -> None:
        provider = FakeProvider(
            'akshare',
            get_quote={'price': 1},
            get_kline={'items': [{'close': 1}]},
            get_money_flow={'items': [{'mainNetInflow': 2}]},
            get_north_flow={'items': [{'净流入': 3}]},
            get_sector_money_flow={'items': [{'板块': '算力'}]},
            get_financial={'status': 'ok', 'rows': []},
            get_report={'status': 'ok', 'rows': []},
        )
        ds, _ = self.make_ds([provider])

        bundle = ds.get_bundle('603966', days=15)

        self.assertEqual(bundle['symbol'], 'SH603966')
        self.assertEqual(bundle['quote']['source'], 'akshare')
        self.assertEqual(bundle['snapshot']['price'], 1)
        self.assertEqual(bundle['kline']['source'], 'akshare')
        self.assertEqual(bundle['money_flow']['source'], 'akshare')
        self.assertEqual(bundle['north_flow']['source'], 'akshare')
        self.assertEqual(bundle['sector_flow']['source'], 'akshare')
        self.assertEqual(bundle['financial']['status'], 'ok')
        self.assertEqual(bundle['report']['status'], 'ok')
        self.assertEqual(bundle['news']['status'], 'placeholder')

    def test_deep_fundamental_bundle_collects_new_sections(self) -> None:
        provider = FakeProvider(
            'akshare',
            get_income_statement={'status': 'ok', 'rows': [{'REPORT_DATE_NAME': '2024年报'}]},
            get_balance_sheet={'status': 'ok', 'rows': [{'REPORT_DATE_NAME': '2024年报'}]},
            get_cash_flow={'status': 'ok', 'rows': [{'REPORT_DATE_NAME': '2024年报'}]},
            get_announcements={'status': 'ok', 'items': [{'公告标题': '董事会决议公告'}]},
            get_news={'status': 'ok', 'items': [{'新闻标题': '示例新闻'}]},
            get_research={'status': 'ok', 'items': [{'报告名称': '示例研报'}]},
            get_main_holders={'status': 'ok', 'items': [{'股东名称': '控股股东'}]},
            get_shareholder_changes={'status': 'ok', 'items': [{'变动股东': '某机构'}]},
            get_dividend={'status': 'ok', 'items': [{'派息': 1.2}]},
        )
        ds, _ = self.make_ds([provider])

        bundle = ds.get_deep_fundamental_bundle('603966', period='yearly', announcement_days=90)

        self.assertEqual(bundle['income_statement']['source'], 'akshare')
        self.assertEqual(bundle['balance_sheet']['rows'][0]['REPORT_DATE_NAME'], '2024年报')
        self.assertEqual(bundle['cash_flow']['rows'][0]['REPORT_DATE_NAME'], '2024年报')
        self.assertEqual(bundle['announcements']['items'][0]['公告标题'], '董事会决议公告')
        self.assertEqual(bundle['news']['items'][0]['新闻标题'], '示例新闻')
        self.assertEqual(bundle['research']['items'][0]['报告名称'], '示例研报')
        self.assertEqual(bundle['main_holders']['items'][0]['股东名称'], '控股股东')
        self.assertEqual(bundle['shareholder_changes']['items'][0]['变动股东'], '某机构')
        self.assertEqual(bundle['dividend']['items'][0]['派息'], 1.2)

    def test_diagnostics_reflect_provider_order(self) -> None:
        ds, _ = self.make_ds(
            [FakeProvider('adata'), FakeProvider('opencli')],
            provider_available={'adata': True, 'opencli': True},
        )

        diagnostics = ds.diagnostics()

        self.assertEqual(diagnostics['providers'], ['adata', 'opencli'])
        self.assertTrue(diagnostics['adata_available'])
        self.assertTrue(diagnostics['opencli_available'])


if __name__ == '__main__':
    unittest.main()
