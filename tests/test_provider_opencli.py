from __future__ import annotations

import unittest
from typing import Any

from stock_master.datasource.providers.opencli import (
    OpenCliProvider,
    OpenCliSinaFinanceProvider,
    OpenCliYahooFinanceProvider,
)


class BackendStub:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.opencli_calls: list[tuple[str, ...]] = []

    def opencli_json(self, *parts: str) -> Any:
        self.opencli_calls.append(parts)
        return self.responses.pop(0) if self.responses else None


class OpenCliProviderTests(unittest.TestCase):
    def test_search_falls_back_from_dc_to_xq(self) -> None:
        backend = BackendStub([None, [{'symbol': 'SH603966'}]])
        provider = OpenCliProvider(backend, True)

        result = provider.get_search('603966')

        self.assertEqual(result['items'][0]['symbol'], 'SH603966')
        self.assertEqual(result['items'][0]['代码'], '603966')
        self.assertEqual(result['items'][0]['kind'], 'search_result')
        self.assertEqual(result['capability'], 'search')
        self.assertEqual(result['items'][0]['meta']['capability'], 'search')
        self.assertEqual(
            backend.opencli_calls,
            [('dc', 'search', '--query', '603966'), ('xq', 'search', '--query', '603966')],
        )

    def test_search_prefers_iwc_first_for_natural_language_query(self) -> None:
        backend = BackendStub([{'answer': '宏观偏多'}])
        provider = OpenCliProvider(backend, True)

        result = provider.get_search('现在市场情绪怎么样？')

        self.assertEqual(result['items'][0]['title'], '现在市场情绪怎么样？')
        self.assertEqual(result['items'][0]['kind'], 'qa')
        self.assertEqual(result['items'][0]['source_channel'], 'iwc.query')
        self.assertEqual(result['items'][0]['answer'], '宏观偏多')
        self.assertEqual(
            backend.opencli_calls,
            [('iwc', 'query', '--question', '现在市场情绪怎么样？')],
        )

    def test_quote_falls_back_to_yahoo_for_non_a_share_symbol(self) -> None:
        backend = BackendStub([{'symbol': 'AAPL', 'regularMarketPrice': 188.3}])
        provider = OpenCliProvider(backend, True)

        result = provider.get_quote('AAPL')

        self.assertEqual(result['symbol'], 'AAPL')
        self.assertEqual(result['regularMarketPrice'], 188.3)
        self.assertEqual(result['最新价'], 188.3)
        self.assertEqual(result['source_channel'], 'yahoo-finance.quote')
        self.assertEqual(result['capability'], 'quote')
        self.assertEqual(result['meta']['market'], 'global')
        self.assertEqual(
            backend.opencli_calls,
            [('yahoo-finance', 'quote', 'AAPL')],
        )

    def test_quote_tries_sinafinance_for_a_share_before_stopping(self) -> None:
        backend = BackendStub([None, None, None, {'symbol': 'SH603966', 'name': '法兰泰克', 'price': '13.900', 'changePercent': '0.58%'}])
        provider = OpenCliProvider(backend, True)

        result = provider.get_quote('603966')

        self.assertEqual(result['symbol'], 'SH603966')
        self.assertEqual(result['name'], '法兰泰克')
        self.assertEqual(result['最新价'], 13.9)
        self.assertEqual(result['percent'], 0.58)
        self.assertEqual(result['meta']['market'], 'a_share')
        self.assertEqual(
            backend.opencli_calls,
            [
                ('xq', 'quote', '--symbol', 'SH603966'),
                ('dc', 'quote', '--symbol', 'SH603966'),
                ('xueqiu', 'stock', 'SH603966'),
                ('sinafinance', 'stock', 'SH603966'),
            ],
        )

    def test_sinafinance_quote_rejects_global_symbol(self) -> None:
        backend = BackendStub([{'symbol': 'AAPL', 'price': 1}])
        provider = OpenCliSinaFinanceProvider(backend, True)

        result = provider.get_quote('AAPL')

        self.assertFalse(result)
        self.assertEqual(backend.opencli_calls, [])

    def test_yahoo_quote_rejects_a_share_symbol(self) -> None:
        backend = BackendStub([{'symbol': 'SH603966', 'regularMarketPrice': 10.2}])
        provider = OpenCliYahooFinanceProvider(backend, True)

        result = provider.get_quote('603966')

        self.assertFalse(result)
        self.assertEqual(backend.opencli_calls, [])

    def test_kline_adds_xueqiu_fallback_without_yahoo_history(self) -> None:
        backend = BackendStub([None, None, [{'timestamp': '2024-01-01', 'close': 10.5}]])
        provider = OpenCliProvider(backend, True)

        result = provider.get_kline('603966', days=30)

        self.assertEqual(result['items'][0]['close'], 10.5)
        self.assertEqual(result['items'][0]['收盘'], 10.5)
        self.assertEqual(result['source_channel'], 'xueqiu.kline')
        self.assertEqual(result['items'][0]['kind'], 'kline')
        self.assertIn('raw', result['items'][0])
        self.assertEqual(
            backend.opencli_calls,
            [
                ('xq', 'history', '--symbol', 'SH603966', '--days', '30'),
                ('dc', 'history', '--symbol', 'SH603966', '--days', '30'),
                ('xueqiu', 'kline', 'SH603966'),
            ],
        )

    def test_news_merges_and_normalizes_items(self) -> None:
        backend = BackendStub([
            [{'title': 'Bloomberg Markets Brief', 'url': 'https://bbg.example/m1', 'published_at': '2024-04-02'}],
            [{'text': '雪球讨论帖', 'created_at': '2024-04-02T10:00:00', 'url': 'https://xq.example/post'}],
            [{'title': '新浪财经头条', 'url': 'https://sina.example/news', 'date': '2024-04-01'}],
            [{'title': '7x24快讯', 'link': 'https://sina.example/live', 'time': '2024-04-02 09:30'}],
        ])
        provider = OpenCliProvider(backend, True)

        result = provider.get_news('AAPL')

        self.assertEqual(len(result['items']), 4)
        self.assertEqual(result['items'][0]['source_channel'], 'bloomberg.markets')
        self.assertEqual(result['items'][0]['发布时间'], '2024-04-02')
        self.assertEqual(result['items'][1]['source_channel'], 'xueqiu.comments')
        self.assertEqual(result['items'][1]['title'], '雪球讨论帖')
        self.assertEqual(result['items'][1]['新闻标题'], '雪球讨论帖')
        self.assertEqual(result['items'][2]['source_channel'], 'sinafinance.news')
        self.assertEqual(result['items'][3]['source_channel'], 'sinafinance.rolling-news')
        self.assertEqual(result['capability'], 'news')
        self.assertEqual(result['items'][0]['kind'], 'market_news')
        self.assertEqual(
            backend.opencli_calls,
            [
                ('bloomberg', 'markets'),
                ('xueqiu', 'comments', 'AAPL'),
                ('sinafinance', 'news'),
                ('sinafinance', 'rolling-news'),
            ],
        )

    def test_research_returns_standardized_real_items(self) -> None:
        backend = BackendStub([
            [{'report_name': 'Q1 业绩点评', 'ctime': '2024-04-03', 'url': 'https://xq.example/c1'}],
            [{'earnings_date': '2024-05-10', 'company': 'Apple'}],
        ])
        provider = OpenCliProvider(backend, True)

        result = provider.get_research('AAPL')

        self.assertEqual(len(result['items']), 2)
        self.assertEqual(result['items'][0]['kind'], 'research')
        self.assertEqual(result['items'][0]['source_channel'], 'xueqiu.comments')
        self.assertEqual(result['items'][0]['报告名称'], 'Q1 业绩点评')
        self.assertEqual(result['items'][1]['kind'], 'earnings_date')
        self.assertEqual(result['items'][1]['source_channel'], 'xueqiu.earnings-date')
        self.assertEqual(result['items'][1]['date'], '2024-05-10')
        self.assertEqual(result['items'][1]['发布时间'], '2024-05-10')
        self.assertEqual(result['capability'], 'research')

    def test_announcements_returns_items_from_earnings_and_comments(self) -> None:
        backend = BackendStub([
            [{'earnings_date': '2024-05-10', 'title': '2024 Q1 Earnings'}],
            [{'text': '管理层电话会纪要', 'created_at': '2024-05-11', 'url': 'https://xq.example/c2'}],
        ])
        provider = OpenCliProvider(backend, True)

        result = provider.get_announcements('AAPL', days=30)

        self.assertEqual(len(result['items']), 2)
        self.assertEqual(result['items'][0]['kind'], 'announcement')
        self.assertEqual(result['items'][0]['source_channel'], 'xueqiu.earnings-date')
        self.assertEqual(result['items'][0]['公告标题'], '2024 Q1 Earnings')
        self.assertEqual(result['items'][1]['kind'], 'announcement_commentary')
        self.assertEqual(result['items'][1]['source_channel'], 'xueqiu.comments')
        self.assertEqual(result['capability'], 'announcements')

    def test_money_flow_summarizes_latest_row(self) -> None:
        backend = BackendStub([[{'mainNetInflow': 1}, {'mainNetInflow': 2, 'smallNetInflow': -1}]])
        provider = OpenCliProvider(backend, True)

        result = provider.get_money_flow('603966')

        self.assertEqual(result['mainNetInflow'], 2)
        self.assertEqual(result['smallNetInflow'], -1)

    def test_sector_list_wraps_list_payload(self) -> None:
        backend = BackendStub([[{'code': 'BK0428'}]])
        provider = OpenCliProvider(backend, True)

        result = provider.get_sector_list()

        self.assertEqual(result['items'][0]['code'], 'BK0428')


if __name__ == '__main__':
    unittest.main()
