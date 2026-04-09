#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from .extractors import extract_closes_and_volumes, extract_rows, pick
from .indicators import calc_boll, calc_kdj, calc_ma, calc_macd, calc_rsi, calc_volume_ratio, find_support_resistance


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float))


def _fmt_level(value: Any) -> str:
    if _is_number(value):
        return f'{float(value):.2f}'
    return str(value)


def _derive_ma_structure(last: Any, ma5: Any, ma10: Any, ma20: Any) -> str:
    if not all(_is_number(value) for value in (last, ma5, ma10, ma20)):
        return '数据不足'
    if last > ma5 > ma10 > ma20:
        return '多头排列'
    if last < ma5 < ma10 < ma20:
        return '空头排列'
    return '均线粘合'


def _build_macd_signal(macd: dict[str, Any]) -> str:
    dif = macd.get('dif')
    dea = macd.get('dea')
    hist = macd.get('hist')
    if not all(_is_number(value) for value in (dif, dea, hist)):
        return 'MACD 数据不足'
    cross = '金叉' if dif > dea else '死叉' if dif < dea else '粘合'
    zone = '零轴上方' if dif > 0 and dea > 0 else '零轴下方' if dif < 0 and dea < 0 else '零轴附近'
    hist_view = '柱体扩张' if hist > 0 else '柱体转弱' if hist < 0 else '柱体走平'
    return f'{cross}，{zone}，{hist_view}'


def _build_kdj_signal(kdj: dict[str, Any]) -> str:
    k_value = kdj.get('k')
    d_value = kdj.get('d')
    if not all(_is_number(value) for value in (k_value, d_value)):
        return 'KDJ 数据不足'
    if k_value > 80:
        band = '偏超买'
    elif k_value < 20:
        band = '偏超卖'
    else:
        band = '中性'
    cross = 'K 上穿 D' if k_value > d_value else 'K 下穿 D' if k_value < d_value else 'K/D 粘合'
    return f'{band}，{cross}'


def _build_boll_signal(last: Any, boll: dict[str, Any]) -> str:
    upper = boll.get('upper')
    lower = boll.get('lower')
    mid = boll.get('mid')
    bandwidth = boll.get('bandwidth')
    if not all(_is_number(value) for value in (last, upper, lower, mid)):
        return '布林带数据不足'
    if last >= upper:
        position = '贴近上轨'
    elif last <= lower:
        position = '贴近下轨'
    elif last >= mid:
        position = '运行在中轨上方'
    else:
        position = '运行在中轨下方'
    if _is_number(bandwidth) and bandwidth < 0.1:
        volatility = '带宽收窄，警惕变盘'
    elif _is_number(bandwidth):
        volatility = '带宽正常'
    else:
        volatility = '带宽未知'
    return f'{position}，{volatility}'


def _build_volume_signal(volume_ratio: Any) -> str:
    if not _is_number(volume_ratio):
        return '量能数据不足'
    if volume_ratio >= 1.5:
        return '近 5 日量能明显放大'
    if volume_ratio <= 0.8:
        return '近 5 日量能偏弱'
    return '量能中性'


def _score_strength(trend: str, rsi: Any, macd: dict[str, Any], volume_ratio: Any) -> str:
    score = 0
    if '偏强' in trend:
        score += 2
    elif '偏弱' in trend:
        score -= 2
    if _is_number(rsi):
        if 55 <= rsi <= 75:
            score += 1
        elif 25 <= rsi <= 40:
            score -= 1
    dif = macd.get('dif')
    dea = macd.get('dea')
    if _is_number(dif) and _is_number(dea):
        score += 1 if dif > dea else -1 if dif < dea else 0
    if _is_number(volume_ratio):
        if volume_ratio >= 1.2:
            score += 1
        elif volume_ratio <= 0.8:
            score -= 1
    if score >= 3:
        return '强'
    if score <= -3:
        return '弱'
    return '中'


def _build_three_day_view(
    trend: str,
    rsi: Any,
    macd: dict[str, Any],
    volume_ratio: Any,
    support_resistance: dict[str, Any],
) -> dict[str, Any]:
    baseline = '震荡倾向'
    basis: list[str] = []
    invalidations: list[str] = []
    dif = macd.get('dif')
    dea = macd.get('dea')

    if '偏强' in trend:
        baseline = '上涨倾向'
        basis.append('均线结构仍偏多')
    elif '偏弱' in trend:
        baseline = '回落倾向'
        basis.append('均线结构仍偏弱')
    else:
        basis.append('均线结构仍偏震荡')

    if _is_number(dif) and _is_number(dea):
        if dif > dea:
            basis.append('MACD 仍偏多头')
            if baseline == '回落倾向':
                baseline = '震荡倾向'
        elif dif < dea:
            basis.append('MACD 偏空或修复不足')
            if baseline == '上涨倾向':
                baseline = '震荡倾向'

    if _is_number(rsi):
        if rsi > 70:
            basis.append('RSI 偏高，短线追高风险上升')
            if baseline == '上涨倾向':
                baseline = '震荡倾向'
        elif rsi < 30:
            basis.append('RSI 偏低，留意超跌反抽')
            if baseline == '回落倾向':
                baseline = '震荡倾向'
        else:
            basis.append('RSI 位于相对中性区间')

    if _is_number(volume_ratio):
        if volume_ratio >= 1.2:
            basis.append('量能尚有配合')
        elif volume_ratio <= 0.8:
            basis.append('量能偏弱，趋势延续性待确认')

    support = support_resistance.get('support')
    resistance = support_resistance.get('resistance')
    if baseline == '上涨倾向':
        if _is_number(support):
            invalidations.append(f'跌破 {_fmt_level(support)} 附近支撑')
        invalidations.append('MACD 重新死叉或放量走弱')
    elif baseline == '回落倾向':
        if _is_number(resistance):
            invalidations.append(f'放量站回 {_fmt_level(resistance)} 附近压力位上方')
        invalidations.append('MACD 重新金叉并伴随量能回暖')
    else:
        if _is_number(support):
            invalidations.append(f'跌破 {_fmt_level(support)} 后震荡结构可能转弱')
        if _is_number(resistance):
            invalidations.append(f'放量突破 {_fmt_level(resistance)} 后可能转向上攻')

    return {
        'baseline': baseline,
        'basis': basis[:4],
        'invalidations': invalidations[:3],
    }


def summarize_technical(bundle: dict[str, Any]) -> dict[str, Any]:
    closes, volumes, _ = extract_closes_and_volumes(bundle.get('kline'))
    quote = bundle.get('quote') or {}
    last = pick(quote, 'price', 'current', '最新价', default=(closes[-1] if closes else None))
    ma5 = calc_ma(closes, 5)
    ma10 = calc_ma(closes, 10)
    ma20 = calc_ma(closes, 20)
    rsi = calc_rsi(closes, 14)
    macd = calc_macd(closes)
    kdj = calc_kdj(closes)
    boll = calc_boll(closes)
    volume_ratio = calc_volume_ratio(volumes)
    support_resistance = find_support_resistance(closes)
    ma_structure = _derive_ma_structure(last, ma5, ma10, ma20)

    trend = '数据不足'
    if all(_is_number(value) for value in (last, ma5, ma10, ma20)):
        if ma_structure == '多头排列':
            trend = '多头排列，趋势偏强'
        elif ma_structure == '空头排列':
            trend = '空头排列，趋势偏弱'
        else:
            trend = '均线纠结，偏震荡'

    macd_signal = _build_macd_signal(macd)
    kdj_signal = _build_kdj_signal(kdj)
    boll_signal = _build_boll_signal(last, boll)
    volume_signal = _build_volume_signal(volume_ratio)
    strength = _score_strength(trend, rsi, macd, volume_ratio)

    signals = [
        f'均线结构：{ma_structure}',
        f'MACD：{macd_signal}',
        f'KDJ：{kdj_signal}',
        f'布林带：{boll_signal}',
        f'量能：{volume_signal}',
    ]
    risks: list[str] = []
    if _is_number(rsi):
        if rsi > 70:
            risks.append('RSI 偏高，短线追高回撤风险上升')
        elif rsi < 30:
            risks.append('RSI 偏低，但仍需等待企稳确认')
    if _is_number(volume_ratio) and volume_ratio <= 0.8:
        risks.append('量能暂未有效放大，趋势延续性仍需确认')
    support = support_resistance.get('support')
    resistance = support_resistance.get('resistance')
    if _is_number(last) and _is_number(resistance) and last >= resistance * 0.98:
        risks.append('价格接近短线压力位，冲高后可能反复')
    if _is_number(last) and _is_number(support) and last <= support * 1.02:
        risks.append('价格贴近短线支撑，破位会削弱当前判断')
    three_day_view = _build_three_day_view(trend, rsi, macd, volume_ratio, support_resistance)

    return {
        'trend': trend,
        'strength': strength,
        'ma_structure': ma_structure,
        'last': last,
        'ma5': ma5,
        'ma10': ma10,
        'ma20': ma20,
        'rsi14': rsi,
        'macd': macd,
        'macd_signal': macd_signal,
        'kdj': kdj,
        'kdj_signal': kdj_signal,
        'boll': boll,
        'boll_signal': boll_signal,
        'volume_ratio': volume_ratio,
        'volume_signal': volume_signal,
        'signals': signals,
        'risks': risks,
        'gap_view': '当前工具未直接返回缺口明细，因此这里只做保守观察。',
        'three_day_view': three_day_view,
        'support_resistance': support_resistance,
    }


def summarize_capital(bundle: dict[str, Any]) -> dict[str, Any]:
    flow_rows = extract_rows(bundle.get('money_flow'))
    north_rows = extract_rows(bundle.get('north_flow'))
    sector_rows = extract_rows(bundle.get('sector_flow'))
    latest_flow = flow_rows[0] if flow_rows else {}
    main_flow = pick(latest_flow, 'mainNetInflow', '主力净流入')
    north_flow = pick(north_rows[0], '净流入', 'netInflow') if north_rows else None
    sector_focus = pick(sector_rows[0], '板块', '行业', '名称') if sector_rows else None

    if _is_number(main_flow):
        main_attitude = '流入' if main_flow > 0 else '流出' if main_flow < 0 else '观望'
        abs_flow = abs(float(main_flow))
        strength = '强' if abs_flow >= 100000000 else '中' if abs_flow >= 10000000 else '弱'
    else:
        main_attitude = '未知'
        strength = '未知'

    conclusion_bits = []
    if main_attitude != '未知':
        conclusion_bits.append(f'主力资金当前偏{main_attitude}')
    if _is_number(north_flow):
        conclusion_bits.append(f'北向资金最新口径为{"净流入" if north_flow > 0 else "净流出" if north_flow < 0 else "中性"}')
    if sector_focus:
        conclusion_bits.append(f'板块关注点可先看 {sector_focus}')
    if not conclusion_bits:
        conclusion_bits.append('主看个股主力资金方向，北向资金仅作市场风险偏好辅助。')

    return {
        'main_flow': bundle.get('money_flow') or {},
        'north_flow': bundle.get('north_flow') or {},
        'sector_flow': bundle.get('sector_flow') or {},
        'main_attitude': main_attitude,
        'strength': strength,
        'north_value': north_flow,
        'sector_focus': sector_focus,
        'conclusion': '；'.join(conclusion_bits),
    }


def summarize_fundamental(bundle: dict[str, Any]) -> dict[str, Any]:
    financial = bundle.get('financial') or {}
    report = bundle.get('report') or {}
    status = pick(financial, 'status', default='unknown')
    report_status = pick(report, 'status', default='unknown')
    financial_rows = extract_rows(financial)
    report_rows = extract_rows(report)
    detective_inputs = ['最近 3 年三张表', 'MD&A / 管理层讨论', '至少 3 家同业', '最近 30 天股价区间']
    if status != 'ok':
        return {
            'status': status,
            'data_completeness': '明显不足',
            'analysis_mode': '轻量模式',
            'conclusion': '基本面数据暂不完整，只能做轻量判断，不宜给出重价值结论。',
            'detective_status': '未满足深度价投模式',
            'detective_inputs': detective_inputs,
            'forensic_focus': ['先核对现金流与利润是否匹配', '优先排查应收、存货、商誉是否异常'],
            'next_steps': ['补齐最近 3 年财报和财务指标后，再做杜邦、ROIC/WACC 和估值分析。'],
            'financial': financial,
            'report': report,
        }
    analysis_mode = '轻量模式'
    data_completeness = '部分完整'
    conclusion = '已接入财务指标，可先做盈利能力、成长性和现金流质量筛查。'
    next_steps = ['若要做深度价投判断，仍需补齐最近 3 年三张表、同业可比和更完整的财报摘要。']
    if financial_rows and report_status == 'ok' and report_rows:
        analysis_mode = '侦探式增强模式'
        conclusion = '财务指标与财报摘要均已接入，可做盈利质量、成长、现金流、轻量估值和部分侦探式分析。'
        next_steps = ['若继续补齐三张表口径、同业样本与资本成本假设，可进一步做杜邦、ROIC/WACC 和 DCF。']
    return {
        'status': 'ok',
        'data_completeness': data_completeness,
        'analysis_mode': analysis_mode,
        'detective_status': '可进入侦探式增强模式' if analysis_mode == '侦探式增强模式' else '仅覆盖轻量深挖前置条件',
        'detective_inputs': detective_inputs,
        'forensic_focus': ['核对 CFO / 净利润', '排查应收与存货是否跑赢营收', '关注非经常性损益和商誉'],
        'report_status': report_status,
        'rows_count': len(financial_rows),
        'report_rows_count': len(report_rows),
        'conclusion': conclusion,
        'next_steps': next_steps,
        'financial': financial,
        'report': report,
    }


def summarize_news(bundle: dict[str, Any]) -> dict[str, Any]:
    announcements = bundle.get('announcements') or {}
    news = bundle.get('news') or {}
    research = bundle.get('research') or {}

    announcement_rows = extract_rows(announcements)
    news_rows = extract_rows(news)
    research_rows = extract_rows(research)

    def _clean_text(value: Any) -> str:
        return str(value or '').strip()

    def _parse_time_value(value: Any) -> tuple[int, str]:
        text = _clean_text(value)
        digits = ''.join(ch for ch in text if ch.isdigit())
        return (int(digits) if digits else 0, text)

    quote = bundle.get('quote') or {}
    symbol = str(bundle.get('symbol') or pick(quote, '代码', 'symbol', default='') or '')
    code_token = symbol[-6:] if len(symbol) >= 6 else symbol
    name_token = _clean_text(pick(quote, '名称', 'name', default=''))

    positive_terms = ('回购', '增持', '中标', '订单', '盈利增长', '扭亏', '买入', '增持评级', '股权激励', '分红', '提质增效', '预增', '签订', '落地')
    negative_terms = ('减持', '诉讼', '终止', '亏损', '下滑', '处罚', '问询函', '质押', '商誉减值', '跌停', '风险提示', '预亏', '延期', '失信')
    company_event_terms = ('回购', '年报', '季报', '业绩', '公告', '项目', '股东', '订单', '诉讼', '分红', '激励', '并购', '募投', '减持', '增持')
    noisy_terms = ('主力资金净流入', '概念涨', '板块涨', '板块跌', '概念涨幅', '资金净流入', '资金净流出')

    def _score_text(text: str) -> int:
        score = 0
        for term in positive_terms:
            if term in text:
                score += 1
        for term in negative_terms:
            if term in text:
                score -= 1
        return score

    def _classify_announcement(row: dict[str, Any]) -> str:
        title = _clean_text(pick(row, '公告标题', 'title', '标题'))
        if '回购' in title:
            return '回购'
        if '年报' in title or '半年报' in title or '季报' in title or '业绩' in title or '快报' in title:
            return '业绩'
        if '分红' in title or '利润分配' in title or '派息' in title:
            return '分红'
        if '减持' in title:
            return '减持'
        if '增持' in title:
            return '增持'
        if '诉讼' in title or '仲裁' in title:
            return '诉讼'
        if '股东大会' in title or '董事会' in title or '监事会' in title:
            return '治理'
        if '项目' in title or '投资' in title or '募投' in title:
            return '项目'
        if '激励' in title:
            return '激励'
        return '其他'

    def _rank_announcement(row: dict[str, Any]) -> tuple[int, int, int, str]:
        title = _clean_text(pick(row, '公告标题', 'title', '标题'))
        category = _classify_announcement(row)
        time_value = _parse_time_value(pick(row, '公告时间', 'publish_time', '时间', '日期'))[0]
        category_weight = {
            '回购': 0,
            '业绩': 0,
            '增持': 1,
            '减持': 1,
            '诉讼': 2,
            '项目': 2,
            '激励': 2,
            '分红': 2,
            '治理': 3,
            '其他': 4,
        }.get(category, 4)
        impact_weight = -abs(_score_text(title))
        return (category_weight, impact_weight, -time_value, title)

    def _event_key(category: str, title: str) -> str:
        normalized = title.replace('关于', '').replace('公告', '').replace('的', '').replace('暨', '')
        if category == '回购':
            return '回购'
        if category == '业绩':
            return '业绩'
        if category in {'减持', '增持', '诉讼', '分红', '激励', '项目'}:
            return category
        if '进展' in normalized:
            return f'{category}:进展'
        return f'{category}:{normalized[:12]}'

    def _dedup_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for event in events:
            key = _clean_text(event.get('dedup_key')) or _clean_text(event.get('title'))
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(event)
        return deduped

    def _classify_research_bias(row: dict[str, Any]) -> tuple[list[str], list[str]]:
        title = _clean_text(pick(row, '报告名称', 'title', '标题'))
        rating = _clean_text(pick(row, '东财评级', '评级', 'rating'))
        positives: list[str] = []
        negatives: list[str] = []
        if rating in {'买入', '增持', '强烈推荐', '推荐'}:
            positives.append(f'研报评级偏正面（{rating}）')
        elif rating in {'减持', '卖出', '回避'}:
            negatives.append(f'研报评级偏谨慎（{rating}）')
        title_score = _score_text(title)
        if title_score > 0 and not positives:
            positives.append(f'研报标题偏正面（{title}）')
        elif title_score < 0 and not negatives:
            negatives.append(f'研报标题偏谨慎（{title}）')
        return positives, negatives

    def _news_priority(row: dict[str, Any]) -> tuple[int, int, int, int, str]:
        title = _clean_text(pick(row, '新闻标题', 'title', '标题')).lower()
        body = _clean_text(pick(row, '新闻内容', 'content', '摘要')).lower()
        kind = _clean_text(pick(row, 'kind'))
        source_channel = _clean_text(pick(row, 'source_channel'))
        time_value = _parse_time_value(pick(row, '发布时间', 'publish_time', '时间', '日期'))[0]
        text = f'{title} {body}'
        company_terms = tuple(term.lower() for term in (name_token, code_token, *company_event_terms) if term)
        company_hit = any(term in text for term in company_terms)
        noisy_hit = any(term in text for term in noisy_terms)
        source_rank = 1 if kind == 'commentary' or source_channel.endswith('.comments') else 0
        if noisy_hit and not company_hit:
            return (source_rank + 2, 1, 0, -time_value, title)
        if company_hit:
            return (source_rank, 0, -abs(_score_text(text)), -time_value, title)
        return (source_rank + 1, 0, -abs(_score_text(text)), -time_value, title)

    ranked_announcements = sorted(announcement_rows, key=_rank_announcement)
    filtered_news_rows = sorted(news_rows, key=_news_priority)
    preferred_news_rows = [row for row in filtered_news_rows if _news_priority(row)[0] < 2] or filtered_news_rows

    latest_announcement_title = None
    latest_announcement_time = None
    latest_announcement_category = None
    if ranked_announcements:
        latest_announcement = ranked_announcements[0]
        latest_announcement_title = pick(latest_announcement, '公告标题', 'title', '标题')
        latest_announcement_time = pick(latest_announcement, '公告时间', 'publish_time', '时间', '日期')
        latest_announcement_category = _classify_announcement(latest_announcement)

    latest_news_title = None
    latest_news_time = None
    if preferred_news_rows:
        latest = preferred_news_rows[0]
        latest_news_title = pick(latest, '新闻标题', 'title', '标题')
        latest_news_time = pick(latest, '发布时间', 'publish_time', '时间', '日期')

    latest_research_title = None
    latest_research_org = None
    latest_research_rating = None
    if research_rows:
        latest_report = research_rows[0]
        latest_research_title = pick(latest_report, '报告名称', 'title', '标题')
        latest_research_org = pick(latest_report, '机构', '机构名称', 'org')
        latest_research_rating = pick(latest_report, '东财评级', '评级', 'rating')

    score = 0
    scored_texts = [
        _clean_text(latest_announcement_title),
        _clean_text(latest_news_title),
        _clean_text(latest_research_title),
        _clean_text(latest_research_rating),
    ]
    for text in scored_texts:
        score += _score_text(text)

    if score >= 2:
        bias = '偏多'
    elif score <= -1:
        bias = '偏空'
    else:
        bias = '中性'

    top_events: list[dict[str, Any]] = []
    for row in ranked_announcements:
        category = _classify_announcement(row)
        title = _clean_text(pick(row, '公告标题', 'title', '标题'))
        if title:
            top_events.append(
                {
                    'type': '公告',
                    'category': category,
                    'title': title,
                    'time': pick(row, '公告时间', 'publish_time', '时间', '日期'),
                    'dedup_key': _event_key(category, title),
                }
            )
    for row in preferred_news_rows:
        title = _clean_text(pick(row, '新闻标题', 'title', '标题'))
        if title:
            top_events.append(
                {
                    'type': '新闻',
                    'category': '公司新闻',
                    'title': title,
                    'time': pick(row, '发布时间', 'publish_time', '时间', '日期'),
                    'dedup_key': f'新闻:{title[:18]}',
                }
            )
    if research_rows:
        row = research_rows[0]
        title = _clean_text(pick(row, '报告名称', 'title', '标题'))
        if title:
            top_events.append(
                {
                    'type': '研报',
                    'category': _clean_text(pick(row, '东财评级', '评级', 'rating')) or '机构观点',
                    'title': title,
                    'time': pick(row, '发布时间', 'publish_time', '时间', '日期'),
                    'dedup_key': f'研报:{title[:18]}',
                }
            )
    top_events = _dedup_events(top_events)[:3]

    if top_events:
        event_summary = '；'.join(f'{event["type"]}{event.get("category") and f"[{event["category"]}]" or ""}：{event["title"]}' for event in top_events)
    else:
        event_summary = '暂无高优先级消息。'

    bullish_factors: list[str] = []
    bearish_factors: list[str] = []
    for row in ranked_announcements[:4]:
        title = _clean_text(pick(row, '公告标题', 'title', '标题'))
        category = _classify_announcement(row)
        score_value = _score_text(title)
        if category in {'回购', '增持', '分红', '激励'} or score_value > 0:
            bullish_factors.append(f'{category}公告：{title}')
        if category in {'减持', '诉讼'} or score_value < 0:
            bearish_factors.append(f'{category}公告：{title}')
    if latest_news_title:
        news_score = _score_text(_clean_text(latest_news_title))
        if news_score > 0:
            bullish_factors.append(f'公司新闻：{latest_news_title}')
        elif news_score < 0:
            bearish_factors.append(f'公司新闻：{latest_news_title}')
    if research_rows:
        research_pos, research_neg = _classify_research_bias(research_rows[0])
        bullish_factors.extend(research_pos)
        bearish_factors.extend(research_neg)

    def _unique_keep_order(items: list[str]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for item in items:
            if item and item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered

    bullish_factors = _unique_keep_order(bullish_factors)[:3]
    bearish_factors = _unique_keep_order(bearish_factors)[:3]
    if bullish_factors and bearish_factors:
        factor_summary = f'利多：{"；".join(bullish_factors)}。利空：{"；".join(bearish_factors)}。'
    elif bullish_factors:
        factor_summary = f'利多：{"；".join(bullish_factors)}。'
    elif bearish_factors:
        factor_summary = f'利空：{"；".join(bearish_factors)}。'
    else:
        factor_summary = '利多利空因子暂不突出。'

    if announcement_rows and preferred_news_rows and research_rows:
        conclusion = f'当前消息面整体{bias}，先看公告、再看公司新闻、最后用研报校验预期。最值得盯的三条是：{event_summary}'
    elif announcement_rows and preferred_news_rows:
        conclusion = f'当前消息面偏{bias}，核心仍在公告和公司直接新闻。重点事件：{event_summary}'
    elif preferred_news_rows and research_rows:
        conclusion = f'当前消息面偏{bias}，新闻与研报都能参考，但缺公告确认，最好不要只凭一条新闻下结论。重点事件：{event_summary}'
    elif preferred_news_rows:
        conclusion = f'当前只能看到新闻流，整体偏{bias}，更适合做短线情绪跟踪。重点事件：{event_summary}'
    elif research_rows:
        conclusion = f'当前主要依赖研报视角，整体偏{bias}，更适合看机构预期，不适合拿来替代公告验证。重点事件：{event_summary}'
    else:
        conclusion = '消息面入口已预留；当前若无额外资讯源，只能保守地视为信息不完整。'

    if conclusion != '消息面入口已预留；当前若无额外资讯源，只能保守地视为信息不完整。':
        conclusion = f'{conclusion} {factor_summary}'

    return {
        'status': 'ok' if (ranked_announcements or preferred_news_rows or research_rows) else 'partial',
        'bias': bias,
        'bias_score': score,
        'conclusion': conclusion,
        'announcement_count': len(announcement_rows),
        'news_count': len(preferred_news_rows),
        'research_count': len(research_rows),
        'latest_announcement_title': latest_announcement_title,
        'latest_announcement_time': latest_announcement_time,
        'latest_announcement_category': latest_announcement_category,
        'latest_news_title': latest_news_title,
        'latest_news_time': latest_news_time,
        'latest_research_title': latest_research_title,
        'latest_research_org': latest_research_org,
        'latest_research_rating': latest_research_rating,
        'top_events': top_events,
        'event_summary': event_summary,
        'bullish_factors': bullish_factors,
        'bearish_factors': bearish_factors,
        'factor_summary': factor_summary,
        'announcements': {**announcements, 'items': ranked_announcements},
        'news': {**news, 'items': preferred_news_rows},
        'research': research,
    }


def summarize_prediction(technical: dict[str, Any], capital: dict[str, Any], fundamental: dict[str, Any]) -> dict[str, Any]:
    trend = technical.get('trend', '')
    rsi = technical.get('rsi14')
    three_day_view = technical.get('three_day_view') or {}
    baseline_label = three_day_view.get('baseline', '震荡倾向')
    if '偏强' in trend:
        baseline = '短线偏强，但需防高位波动。'
    elif '偏弱' in trend:
        baseline = '短线偏弱，宜先看企稳信号。'
    else:
        baseline = '短线更像震荡，等待方向确认。'
    if isinstance(rsi, (int, float)):
        if rsi > 70:
            baseline += ' RSI 偏高，注意追高风险。'
        elif rsi < 30:
            baseline += ' RSI 偏低，留意超跌反弹。'
    if baseline_label != '震荡倾向':
        baseline += f' 未来 3 个交易日基准判断偏向{baseline_label}。'

    consistent_signals: list[str] = []
    conflicting_signals: list[str] = []
    if '偏强' in trend:
        consistent_signals.append('均线结构偏强')
    elif '偏弱' in trend:
        consistent_signals.append('均线结构偏弱')
    main_attitude = capital.get('main_attitude')
    if main_attitude == '流入':
        if '偏弱' in trend:
            conflicting_signals.append('技术偏弱，但资金边际回流')
        else:
            consistent_signals.append('主力资金边际配合')
    elif main_attitude == '流出':
        if '偏强' in trend:
            conflicting_signals.append('技术偏强，但资金未明显配合')
        else:
            consistent_signals.append('资金面偏谨慎')
    if fundamental.get('status') != 'ok':
        baseline += ' 基本面结论暂不完整，应降低中长线确定性。'
        conflicting_signals.append('基本面数据仍不完整，中长线确定性不足')

    if not consistent_signals:
        consistent_signals.append('当前更依赖技术面与关键位观察')
    invalidations = three_day_view.get('invalidations') or ['关键位失守时需重评判断']
    return {
        'baseline_view': baseline,
        'support_resistance': technical.get('support_resistance'),
        't1_view': '偏强' if '偏强' in trend else '承压' if '偏弱' in trend else '反复',
        't2_t3_view': baseline_label,
        'key_observations': (three_day_view.get('basis') or [])[:3],
        'consistent_signals': consistent_signals,
        'conflicting_signals': conflicting_signals,
        'invalidations': invalidations,
        'aggressive': '只在放量突破且关键位不失守时考虑跟随。',
        'steady': '优先等待回踩支撑后的确认信号。',
        'conservative': '在基本面与消息面未补齐前，控制仓位。',
    }
