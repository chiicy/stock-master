from __future__ import annotations

import unittest
from typing import Any

from stock_master.analysis.cli import parse_args
from stock_master.analysis.render import render_text
from stock_master.analysis.report import build_analysis_report, build_report


class FakeDataSource:
    def __init__(
        self,
        bundle: dict[str, Any],
        *,
        search_result: dict[str, Any] | None = None,
        deep_bundle: dict[str, Any] | None = None,
    ) -> None:
        self.bundle = bundle
        self.search_result = search_result or {'items': []}
        self.deep_bundle = deep_bundle or {}
        self.calls: list[tuple[str, int]] = []
        self.market_calls: list[str | None] = []
        self.search_calls: list[str] = []
        self.deep_calls: list[str] = []

    def get_bundle(self, symbol: str, days: int = 120) -> dict[str, Any]:
        self.calls.append((symbol, days))
        return self.bundle

    def get_market_bundle(self, *, date: str | None = None) -> dict[str, Any]:
        self.market_calls.append(date)
        return self.bundle

    def get_search(self, query: str) -> dict[str, Any]:
        self.search_calls.append(query)
        return self.search_result

    def get_deep_fundamental_bundle(self, symbol: str, *, period: str = 'yearly', announcement_days: int = 180) -> dict[str, Any]:
        self.deep_calls.append(symbol)
        return self.deep_bundle


def sample_bundle() -> dict[str, Any]:
    prices = list(range(10, 40))
    volumes = [1000 + i * 10 for i in range(len(prices))]
    return {
        'quote': {
            'price': prices[-1],
            'percent': 3.21,
            'amount': 123456789,
            'turnoverRate': 5.67,
            'name': '测试股份',
        },
        'snapshot': {
            'price': prices[-1],
        },
        'kline': {
            'items': [
                {
                    'date': f'2026-03-{row_index + 1:02d}',
                    'close': close,
                    'high': close + 0.8,
                    'low': close - 0.7,
                    'volume': volume,
                }
                for row_index, (close, volume) in enumerate(zip(prices, volumes, strict=True))
            ],
        },
        'money_flow': {
            'items': [
                {
                    'mainNetInflow': 1200000,
                    'superLargeNetInflow': 900000,
                    'smallNetInflow': -200000,
                }
            ],
        },
        'north_flow': {'items': [{'净流入': 100}]},
        'sector_flow': {'items': [{'板块': '算力'}]},
        'financial': {
            'status': 'error',
            'error': 'source missing',
        },
        'report': {
            'status': 'placeholder',
        },
        'announcements': {
            'status': 'ok',
            'items': [
                {
                    '公告标题': '关于2025年年度业绩快报的公告',
                    '公告时间': '2026-04-07',
                },
                {
                    '公告标题': '公司完成股份回购公告',
                    '公告时间': '2026-04-08',
                },
                {
                    '公告标题': '关于股份回购进展的公告',
                    '公告时间': '2026-04-06',
                },
                {
                    '公告标题': '关于股东减持计划的公告',
                    '公告时间': '2026-04-05',
                },
            ],
        },
        'news': {
            'status': 'ok',
            'items': [
                {
                    '新闻标题': '板块主力资金净流入，概念涨3.2%',
                    '发布时间': '2026-04-08 15:00:00',
                    '新闻内容': '概念涨幅居前，主力资金净流入。',
                },
                {
                    '新闻标题': '公司完成股份回购',
                    '发布时间': '2026-04-08 10:00:00',
                    '新闻内容': '公司公告回购实施完毕。',
                },
                {
                    '新闻标题': '测试股份股东拟减持部分股份',
                    '发布时间': '2026-04-08 11:00:00',
                    '新闻内容': '公司披露减持计划，短线需留意抛压。',
                }
            ],
        },
        'research': {
            'status': 'ok',
            'items': [
                {
                    '报告名称': '光刻胶树脂国产化加速推进',
                    '机构': '中邮证券',
                    '东财评级': '买入',
                }
            ],
        },
    }


class AnalyzeStockTests(unittest.TestCase):
    def test_cli_parse_args_supports_existing_flags(self) -> None:
        args = parse_args(['603966', '--days', '30', '--format', 'text'])

        self.assertEqual(args.symbol, '603966')
        self.assertEqual(args.days, 30)
        self.assertEqual(args.format, 'text')

    def test_build_report_accepts_injected_datasource(self) -> None:
        fake = FakeDataSource(sample_bundle())

        report = build_report('603966', days=30, datasource=fake)

        self.assertEqual(fake.calls, [('603966', 30)])
        self.assertEqual(report['symbol'], 'SH603966')
        self.assertEqual(report['technical']['trend'], '多头排列，趋势偏强')

    def test_build_analysis_report_routes_market_query_to_market_overview(self) -> None:
        fake = FakeDataSource(
            {
                'north_flow': {'items': [{'净流入': 20}]},
                'sector_flow': {'items': [{'板块': 'AI算力'}, {'板块': '机器人'}]},
                'limit_up': {'items': [{'symbol': 'SH603966'}, {'symbol': 'SZ000001'}]},
                'limit_down': {'items': [{'symbol': 'SH600000'}]},
            }
        )

        report = build_analysis_report('今天A股市场怎么样', datasource=fake)
        text = render_text(report)

        self.assertEqual(report['report_type'], 'market')
        self.assertEqual(fake.market_calls, [None])
        self.assertEqual(report['market_overview']['bias'], '偏强')
        self.assertIn('【市场概览】', text)
        self.assertIn('强势板块：AI算力；机器人', text)
        self.assertIn('能力边界：当前市场报告主要基于资金流与涨跌停广度', text)

    def test_market_render_uses_placeholder_when_north_flow_missing(self) -> None:
        fake = FakeDataSource(
            {
                'north_flow': {'items': []},
                'sector_flow': {'items': []},
                'limit_up': {'items': [{'symbol': 'SH603966'}]},
                'limit_down': {'items': [{'symbol': 'SH600000'}]},
            }
        )

        text = render_text(build_analysis_report('今天A股市场怎么样', datasource=fake))

        self.assertIn('北向资金：暂无', text)

    def test_build_analysis_report_matches_sector_keyword_from_chinese_query(self) -> None:
        fake = FakeDataSource(
            {
                'north_flow': {'items': []},
                'sector_flow': {'items': [{'板块': '机器人'}, {'板块': 'AI算力'}]},
                'limit_up': {'items': []},
                'limit_down': {'items': []},
            }
        )

        report = build_analysis_report('机器人板块怎么看', datasource=fake)

        self.assertEqual(report['report_type'], 'sector')
        self.assertEqual(report['sector_overview']['matched_sectors'], ['机器人'])

    def test_build_analysis_report_resolves_name_query_via_search(self) -> None:
        fake = FakeDataSource(
            sample_bundle(),
            search_result={'items': [{'symbol': 'SH603966', 'name': '法兰泰克'}]},
        )

        report = build_analysis_report('法兰泰克走势怎么看', datasource=fake)

        self.assertEqual(fake.search_calls, ['法兰泰克走势怎么看'])
        self.assertEqual(fake.calls, [('SH603966', 120)])
        self.assertEqual(report['symbol'], 'SH603966')

    def test_prediction_mentions_rsi_and_fundamental_gap(self) -> None:
        fake = FakeDataSource(sample_bundle())

        report = build_report('603966', datasource=fake)
        baseline = report['prediction']['baseline_view']

        self.assertIn('短线偏强', baseline)
        self.assertIn('RSI 偏高', baseline)
        self.assertIn('基本面结论暂不完整', baseline)
        self.assertEqual(report['technical']['three_day_view']['baseline'], '震荡倾向')
        self.assertIn('跌破 20.00', report['prediction']['invalidations'][0])

    def test_build_analysis_report_enables_deep_technical_mode_for_a_share(self) -> None:
        fake = FakeDataSource(sample_bundle())

        report = build_analysis_report('像虾评一样分析 603966，看看支撑位压力位和未来三天', datasource=fake)

        self.assertEqual(report['technical']['mode'], 'deep_technical')
        self.assertEqual(report['intent']['mode'], 'deep_technical')
        self.assertIn('EMA50', render_text(report))

    def test_build_analysis_report_deep_fundamental_mode_collects_gate(self) -> None:
        fake = FakeDataSource(
            sample_bundle(),
            deep_bundle={
                'income_statement': {'status': 'ok', 'rows': [{'REPORT_DATE_NAME': '2024年报'}]},
                'balance_sheet': {'status': 'ok', 'rows': [{'REPORT_DATE_NAME': '2024年报'}]},
                'cash_flow': {'status': 'ok', 'rows': [{'REPORT_DATE_NAME': '2024年报'}]},
                'announcements': {'status': 'ok', 'items': [{'公告标题': '董事会决议公告'}]},
            },
        )

        report = build_analysis_report('用财报侦探方式分析 603966，做价值投资框架', datasource=fake)

        self.assertEqual(fake.deep_calls, ['SH603966'])
        self.assertEqual(report['fundamental']['analysis_mode'], '深度侦探模式（受限）')
        self.assertIn('MD&A / 管理层讨论', report['fundamental']['detective_readiness']['missing_items'])
        self.assertIn('逆向质疑', render_text(report))

    def test_render_text_contains_snapshot_flow_and_news_lines(self) -> None:
        text = render_text(build_report('603966', datasource=FakeDataSource(sample_bundle())))

        self.assertIn('【SH603966 综合分析】', text)
        self.assertIn('主力净流入：1,200,000', text)
        self.assertIn('状态：error', text)
        self.assertIn('缺口观察：当前工具未直接返回缺口明细', text)
        self.assertIn('模式：综合技术面', text)
        self.assertIn('EMA50 / EMA200', text)
        self.assertIn('五、消息面', text)
        self.assertIn('倾向：中性', text)
        self.assertIn('最新公告：公司完成股份回购公告', text)
        self.assertIn('公告分类：回购', text)
        self.assertIn('最新新闻：测试股份股东拟减持部分股份', text)
        self.assertIn('重点消息：公告[回购]：公司完成股份回购公告', text)
        self.assertIn('利多因子：回购公告：公司完成股份回购公告', text)
        self.assertIn('利空因子：减持公告：关于股东减持计划的公告', text)
        self.assertIn('研报机构/评级：中邮证券；买入', text)
        self.assertIn('T+2~T+3：震荡倾向', text)

    def test_build_report_summarizes_news_availability(self) -> None:
        report = build_report('603966', datasource=FakeDataSource(sample_bundle()))

        self.assertEqual(report['news']['status'], 'ok')
        self.assertEqual(report['news']['announcement_count'], 4)
        self.assertEqual(report['news']['news_count'], 2)
        self.assertEqual(report['news']['research_count'], 1)
        self.assertEqual(report['news']['bias'], '中性')
        self.assertEqual(report['news']['latest_announcement_title'], '公司完成股份回购公告')
        self.assertEqual(report['news']['latest_announcement_category'], '回购')
        self.assertEqual(report['news']['latest_news_title'], '测试股份股东拟减持部分股份')
        self.assertEqual(report['news']['latest_research_org'], '中邮证券')
        self.assertEqual(len(report['news']['top_events']), 3)
        self.assertIn('公告[回购]：公司完成股份回购公告', report['news']['event_summary'])
        self.assertIn('公告[业绩]：关于2025年年度业绩快报的公告', report['news']['event_summary'])
        self.assertNotIn('关于股份回购进展的公告', report['news']['event_summary'])
        self.assertIn('回购公告：公司完成股份回购公告', '；'.join(report['news']['bullish_factors']))
        self.assertIn('减持公告：关于股东减持计划的公告', '；'.join(report['news']['bearish_factors']))
        self.assertIn('利多：', report['news']['factor_summary'])
        self.assertIn('利空：', report['news']['factor_summary'])
        self.assertIn('最值得盯的三条', report['news']['conclusion'])

    def test_commentary_rows_do_not_override_actual_news_priority(self) -> None:
        bundle = sample_bundle()
        bundle['news'] = {
            'status': 'ok',
            'items': [
                {
                    'title': '$测试股份(SH603966)$ 走势讨论，短线偏强',
                    'content': '社区评论',
                    'publish_time': '2026-04-09T20:00:00.000Z',
                    'kind': 'commentary',
                    'source_channel': 'xueqiu.comments',
                },
                {
                    'title': '测试股份签下新订单',
                    'content': '公司公告新订单落地',
                    'publish_time': '2026-04-09 10:00:00',
                    'kind': 'news',
                    'source_channel': 'sinafinance.news',
                },
            ],
        }

        report = build_report('603966', datasource=FakeDataSource(bundle))

        self.assertEqual(report['news']['latest_news_title'], '测试股份签下新订单')


if __name__ == '__main__':
    unittest.main()
