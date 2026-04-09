#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from .extractors import extract_rows, pick


def fmt_num(value: Any, digits: int = 2) -> str:
    try:
        return f'{float(value):,.{digits}f}'
    except Exception:
        return str(value)


def fmt_join(values: Any) -> str:
    if isinstance(values, list):
        filtered = [str(value) for value in values if value not in (None, '', [])]
        return '；'.join(filtered) if filtered else '暂无'
    return str(values) if values not in (None, '') else '暂无'


def render_text(report: dict[str, Any]) -> str:
    symbol = report['symbol']
    quote = report.get('data_snapshot', {}).get('quote') or {}
    technical = report.get('technical') or {}
    fundamental = report.get('fundamental') or {}
    capital = report.get('capital_flow') or {}
    news = report.get('news') or {}
    prediction = report.get('prediction') or {}

    last = pick(quote, 'price', 'current', '最新价', default=technical.get('last'))
    pct = pick(quote, 'percent', '涨跌幅')
    amount = pick(quote, 'amount', '成交额')
    turn = pick(quote, 'turnoverRate', '换手率')

    lines = [
        f'【{symbol} 综合分析】',
        '',
        '一、基础数据快照',
        f'- 最新价：{fmt_num(last)}',
        f'- 涨跌幅：{fmt_num(pct)}%',
        f'- 换手率：{fmt_num(turn)}%',
        f'- 成交额：{fmt_num(amount, 0)}',
        '',
        '二、技术面',
        f'- 趋势：{technical.get("trend")}',
        f'- 强度：{technical.get("strength")}',
        f'- MA5 / MA10 / MA20：{fmt_num(technical.get("ma5"))} / {fmt_num(technical.get("ma10"))} / {fmt_num(technical.get("ma20"))}',
        f'- RSI14：{fmt_num(technical.get("rsi14"))}',
        f'- 关键信号：{fmt_join((technical.get("signals") or [])[:3])}',
    ]

    support_resistance = technical.get('support_resistance')
    if support_resistance:
        lines.append(f'- 支撑 / 压力：{fmt_num(support_resistance.get("support"))} / {fmt_num(support_resistance.get("resistance"))}')
    if technical.get('gap_view'):
        lines.append(f'- 缺口观察：{technical.get("gap_view")}')

    lines.extend(['', '三、资金面'])
    flow_rows = extract_rows(capital.get('main_flow'))
    if flow_rows:
        row = flow_rows[0]
        lines.extend(
            [
                f'- 主力净流入：{fmt_num(pick(row, "mainNetInflow", "主力净流入"), 0)}',
                f'- 超大单净流入：{fmt_num(pick(row, "superLargeNetInflow", "超大单净流入"), 0)}',
                f'- 小单净流入：{fmt_num(pick(row, "smallNetInflow", "小单净流入"), 0)}',
                f'- 资金结论：{capital.get("conclusion")}',
            ]
        )
    else:
        lines.append('- 个股资金流：暂无可用数据')

    lines.extend(
        [
            '',
            '四、基本面',
            f'- 状态：{fundamental.get("status")}',
            f'- 完整度：{fundamental.get("data_completeness")}',
            f'- 模式：{fundamental.get("analysis_mode")}',
            f'- 深度价投状态：{fundamental.get("detective_status")}',
            f'- 判断：{fundamental.get("conclusion")}',
            f'- 排雷重点：{fmt_join((fundamental.get("forensic_focus") or [])[:3])}',
            f'- 下一步：{fmt_join((fundamental.get("next_steps") or [])[:2])}',
            '',
            '五、消息面',
            f'- 状态：{news.get("status")}',
            f'- 倾向：{news.get("bias") or "暂无"}',
            f'- 判断：{news.get("conclusion")}',
            f'- 公告条数：{news.get("announcement_count")}',
            f'- 新闻条数：{news.get("news_count")}',
            f'- 研报条数：{news.get("research_count")}',
            f'- 最新公告：{news.get("latest_announcement_title") or "暂无"}',
            f'- 公告分类：{news.get("latest_announcement_category") or "暂无"}',
            f'- 公告时间：{news.get("latest_announcement_time") or "暂无"}',
            f'- 最新新闻：{news.get("latest_news_title") or "暂无"}',
            f'- 新闻时间：{news.get("latest_news_time") or "暂无"}',
            f'- 最新研报：{news.get("latest_research_title") or "暂无"}',
            f'- 研报机构/评级：{fmt_join([news.get("latest_research_org"), news.get("latest_research_rating")])}',
            f'- 重点消息：{news.get("event_summary") or "暂无"}',
            f'- 利多因子：{fmt_join(news.get("bullish_factors"))}',
            f'- 利空因子：{fmt_join(news.get("bearish_factors"))}',
            '',
            '六、综合预判',
            f'- 基准判断：{prediction.get("baseline_view")}',
            f'- T+1：{prediction.get("t1_view")}',
            f'- T+2~T+3：{prediction.get("t2_t3_view")}',
            f'- 关键观察点：{fmt_join(prediction.get("key_observations"))}',
            f'- 失效条件：{fmt_join(prediction.get("invalidations"))}',
            f'- 激进：{prediction.get("aggressive")}',
            f'- 稳健：{prediction.get("steady")}',
            f'- 保守：{prediction.get("conservative")}',
        ]
    )
    return '\n'.join(lines)
