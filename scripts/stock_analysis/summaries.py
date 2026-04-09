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
    return {
        'conclusion': '消息面入口已预留；当前若无额外资讯源，只能保守地视为信息不完整。',
        'news': bundle.get('news') or {},
        'research': bundle.get('research') or {},
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
