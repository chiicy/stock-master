#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from .extractors import extract_rows, pick


def fmt_num(value: Any, digits: int = 2) -> str:
    if value in (None, ''):
        return '暂无'
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
    if report.get('report_type') == 'market':
        overview = report.get('market_overview') or {}
        return '\n'.join(
            [
                '【市场概览】',
                '',
                f'- 请求：{report.get("query") or "市场概览"}',
                f'- 市场倾向：{overview.get("bias") or "暂无"}',
                f'- 北向资金：{fmt_num(overview.get("north_value"), 0)}',
                f'- 强势板块：{fmt_join(overview.get("top_sectors"))}',
                f'- 涨停 / 跌停：{overview.get("limit_up_count")} / {overview.get("limit_down_count")}',
                f'- 市场广度：{overview.get("breadth") or "暂无"}',
                f'- 观察点：{fmt_join(overview.get("observations"))}',
                f'- 能力边界：{fmt_join(overview.get("limitations"))}',
                f'- 结论：{overview.get("conclusion") or "暂无"}',
            ]
        )

    if report.get('report_type') == 'sector':
        overview = report.get('sector_overview') or {}
        return '\n'.join(
            [
                '【板块概览】',
                '',
                f'- 请求：{report.get("query") or "板块概览"}',
                f'- 命中板块：{fmt_join(overview.get("matched_sectors"))}',
                f'- 当前强势板块：{fmt_join(overview.get("top_sectors"))}',
                f'- 观察点：{fmt_join(overview.get("observations"))}',
                f'- 能力边界：{fmt_join(overview.get("limitations"))}',
                f'- 结论：{overview.get("conclusion") or "暂无"}',
            ]
        )

    symbol = report['symbol']
    quote = report.get('data_snapshot', {}).get('quote') or {}
    technical = report.get('technical') or {}
    fundamental = report.get('fundamental') or {}
    capital = report.get('capital_flow') or {}
    news = report.get('news') or {}
    prediction = report.get('prediction') or {}
    intent = report.get('intent') or {}

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
        f'- 模式：{"深度技术面" if technical.get("mode") == "deep_technical" else "综合技术面"}',
        f'- 趋势：{technical.get("trend")}',
        f'- 强度：{technical.get("strength")}',
        f'- 综合评分：{technical.get("comprehensive_score") if technical.get("comprehensive_score") is not None else "暂无"}（{technical.get("comprehensive_label") or "暂无"}）',
        f'- MA5 / MA10 / MA20：{fmt_num(technical.get("ma5"))} / {fmt_num(technical.get("ma10"))} / {fmt_num(technical.get("ma20"))}',
        f'- EMA50 / EMA200：{fmt_num(technical.get("ema50"))} / {fmt_num(technical.get("ema200"))}',
        f'- RSI14 / ADX14：{fmt_num(technical.get("rsi14"))} / {fmt_num(technical.get("adx14"))}',
        f'- 关键信号：{fmt_join((technical.get("signals") or [])[:4])}',
        f'- 市场联读：{fmt_join(technical.get("market_context"))}',
    ]
    if report.get('resolution_note'):
        lines.insert(7, f'- 标的解析：{report.get("resolution_note")}')
    if intent.get('notes'):
        lines.insert(8, f'- 模式说明：{fmt_join(intent.get("notes"))}')
    if technical.get('quote_note'):
        lines.append(f'- 快照说明：{technical.get("quote_note")}')

    support_resistance = technical.get('support_resistance')
    if support_resistance:
        lines.append(f'- 支撑 / 压力：{fmt_num(support_resistance.get("support"))} / {fmt_num(support_resistance.get("resistance"))}')
    if technical.get('gap_view'):
        lines.append(f'- 缺口观察：{technical.get("gap_view")}')
    lines.extend(
        [
            f'- 未来 3 个交易日：{technical.get("three_day_view", {}).get("baseline") or "暂无"}',
            f'- 主要依据：{fmt_join(technical.get("three_day_view", {}).get("basis"))}',
            f'- 失效条件：{fmt_join(technical.get("three_day_view", {}).get("invalidations"))}',
        ]
    )

    lines.extend(['', '三、资金面'])
    flow_rows = extract_rows(capital.get('main_flow'))
    main_net_inflow = capital.get('main_net_inflow')
    super_large_net_inflow = capital.get('super_large_net_inflow')
    small_net_inflow = capital.get('small_net_inflow')
    if any(value is not None for value in (main_net_inflow, super_large_net_inflow, small_net_inflow)) or flow_rows:
        row = flow_rows[-1] if flow_rows else {}
        lines.extend(
            [
                f'- 主力净流入：{fmt_num(main_net_inflow if main_net_inflow is not None else pick(row, "mainNetInflow", "主力净流入", "主力净流入-净额"), 0)}',
                f'- 超大单净流入：{fmt_num(super_large_net_inflow if super_large_net_inflow is not None else pick(row, "superLargeNetInflow", "超大单净流入", "超大单净流入-净额"), 0)}',
                f'- 小单净流入：{fmt_num(small_net_inflow if small_net_inflow is not None else pick(row, "smallNetInflow", "小单净流入", "小单净流入-净额"), 0)}',
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
            f'- 证据质量：{fundamental.get("evidence_quality") or "暂无"}',
            f'- 估值准备度：{fundamental.get("valuation_readiness") or "暂无"}',
            f'- 同业对比准备度：{"已就绪" if fundamental.get("peer_compare_ready") else "未就绪"}',
            f'- 判断：{fundamental.get("conclusion")}',
            f'- 30 日价格区间：{fmt_join([pick(fundamental.get("price_range_30d") or {}, "low"), pick(fundamental.get("price_range_30d") or {}, "high")])}',
            f'- 数据缺口：{fmt_join((fundamental.get("detective_readiness") or {}).get("missing_items"))}',
            f'- 排雷重点：{fmt_join((fundamental.get("forensic_focus") or [])[:3])}',
            f'- 法证 / ESG：{fmt_join((fundamental.get("forensic_flags") or [])[:3])}',
            f'- 逆向质疑：{fmt_join((fundamental.get("reverse_questions") or [])[:2])}',
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
