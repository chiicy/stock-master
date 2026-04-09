#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import asdict
import re
from typing import Any, Protocol, TypeAlias

from stock_master.datasource import DataSource
from stock_master.common.symbols import normalize_symbol

from .extractors import extract_rows, pick
from .intents import (
    INTENT_MARKET,
    INTENT_SECTOR,
    MODE_DEEP_FUNDAMENTAL,
    MODE_DEEP_TECHNICAL,
    AnalysisIntent,
    parse_analysis_intent,
)
from .summaries import (
    summarize_capital,
    summarize_fundamental,
    summarize_market_overview,
    summarize_news,
    summarize_prediction,
    summarize_technical,
)

BundlePayload: TypeAlias = dict[str, Any]
ReportPayload: TypeAlias = dict[str, Any]
DEFAULT_ANALYSIS_DAYS = 120
SECTOR_STOPWORDS = {'板块', '行业', '概念', '轮动', '怎么看', '怎么', '看', '分析', '一下', '今天', '当前', '走势'}


class BundleSource(Protocol):
    def get_bundle(self, symbol: str, days: int = DEFAULT_ANALYSIS_DAYS) -> BundlePayload: ...


class MarketBundleSource(Protocol):
    def get_market_bundle(self, *, date: str | None = None) -> BundlePayload: ...


class SearchSource(Protocol):
    def get_search(self, query: str) -> BundlePayload: ...


class DeepFundamentalSource(Protocol):
    def get_deep_fundamental_bundle(self, symbol: str, *, period: str = 'yearly', announcement_days: int = 180) -> BundlePayload: ...


def _select_resolved_symbol(search_payload: dict[str, Any], intent: AnalysisIntent) -> str | None:
    rows = extract_rows(search_payload)
    if not rows:
        return None
    if intent.market in {'a_share', 'unknown'}:
        for row in rows:
            symbol = pick(row, 'symbol', '代码')
            if symbol and normalize_symbol(str(symbol)).startswith(('SH', 'SZ', 'BJ')):
                return normalize_symbol(str(symbol))
    first_symbol = pick(rows[0], 'symbol', '代码')
    if first_symbol:
        return normalize_symbol(str(first_symbol))
    return None


def _resolve_symbol(intent: AnalysisIntent, datasource: SearchSource | None) -> tuple[str | None, str | None]:
    if intent.symbol:
        return normalize_symbol(intent.symbol), None
    if datasource is None or not intent.search_query:
        return None, '未提供可用的检索数据源，无法从自然语言请求中解析标的。'
    search_payload = datasource.get_search(intent.search_query)
    resolved = _select_resolved_symbol(search_payload, intent)
    if resolved:
        return resolved, None
    return None, f'未从检索结果中解析到可用标的：{intent.search_query}'


def _extract_sector_tokens(query: str) -> list[str]:
    normalized_query = str(query or '').lower()
    for stopword in sorted(SECTOR_STOPWORDS, key=len, reverse=True):
        normalized_query = normalized_query.replace(stopword, ' ')
    tokens = re.findall(r'[a-z]{2,}|[\u4e00-\u9fff]{2,}', normalized_query)
    cleaned: list[str] = []
    for token in tokens:
        normalized = token.strip()
        if not normalized or normalized in SECTOR_STOPWORDS:
            continue
        if normalized not in cleaned:
            cleaned.append(normalized)
    return cleaned


def build_stock_report(
    symbol: str,
    days: int = DEFAULT_ANALYSIS_DAYS,
    *,
    datasource: BundleSource | None = None,
    intent: AnalysisIntent | None = None,
) -> ReportPayload:
    ds = datasource or DataSource()
    bundle = ds.get_bundle(symbol, days=days)
    deep_mode = bool(intent and intent.mode == MODE_DEEP_TECHNICAL and intent.supported)
    deep_fundamental_bundle = None
    if intent and intent.mode == MODE_DEEP_FUNDAMENTAL and intent.supported and hasattr(ds, 'get_deep_fundamental_bundle'):
        deep_fundamental_bundle = ds.get_deep_fundamental_bundle(symbol, period='yearly', announcement_days=180)
    technical = summarize_technical(bundle, deep_mode=deep_mode)
    capital = summarize_capital(bundle)
    fundamental = summarize_fundamental(
        bundle,
        deep_bundle=deep_fundamental_bundle,
        deep_mode=bool(intent and intent.mode == MODE_DEEP_FUNDAMENTAL and intent.supported),
    )
    news = summarize_news(bundle)
    prediction = summarize_prediction(technical, capital, fundamental)
    return {
        'report_type': 'stock',
        'symbol': normalize_symbol(symbol),
        'intent': asdict(intent) if intent else None,
        'data_snapshot': {
            'quote': bundle.get('quote'),
            'snapshot': bundle.get('snapshot'),
        },
        'technical': technical,
        'fundamental': fundamental,
        'capital_flow': capital,
        'news': news,
        'prediction': prediction,
        'raw_bundle': bundle,
    }


def build_market_report(
    query: str,
    *,
    date: str | None = None,
    datasource: MarketBundleSource | None = None,
) -> ReportPayload:
    ds = datasource or DataSource()
    bundle = ds.get_market_bundle(date=date)
    overview = summarize_market_overview(bundle)
    return {
        'report_type': 'market',
        'query': query,
        'market_overview': overview,
        'raw_bundle': bundle,
    }


def build_sector_report(
    query: str,
    *,
    date: str | None = None,
    datasource: MarketBundleSource | None = None,
) -> ReportPayload:
    ds = datasource or DataSource()
    bundle = ds.get_market_bundle(date=date)
    sector_rows = extract_rows(bundle.get('sector_flow'))
    sector_names = [str(pick(row, '板块', '行业', '名称')).strip() for row in sector_rows if pick(row, '板块', '行业', '名称')]
    tokens = _extract_sector_tokens(query)
    matched = [
        name
        for name in sector_names
        if any(token in name.lower() for token in tokens)
    ]
    observations: list[str] = []
    if matched:
        observations.append(f'当前命中的板块候选：{"；".join(matched[:3])}')
    elif tokens:
        observations.append(f'未从当前板块资金流里直接匹配到关键词：{" / ".join(tokens)}')
    if sector_names:
        observations.append(f'实时强势板块样本：{"；".join(sector_names[:3])}')
    else:
        observations.append('当前板块资金流数据暂未命中，无法给出真实轮动强弱。')
    return {
        'report_type': 'sector',
        'query': query,
        'sector_overview': {
            'status': 'ok' if sector_rows else 'empty',
            'query_tokens': tokens,
            'matched_sectors': matched,
            'top_sectors': sector_names[:5],
            'observations': observations,
            'limitations': [
                '当前板块报告仅基于实时板块资金流关键词匹配，不伪装支持完整板块画像或龙头扩散分析。'
            ],
            'conclusion': observations[-1] if observations else '暂无板块结论。',
        },
        'raw_bundle': bundle,
    }


def build_analysis_report(query: str, days: int = DEFAULT_ANALYSIS_DAYS, datasource: BundleSource | MarketBundleSource | None = None) -> ReportPayload:
    intent = parse_analysis_intent(query)
    if intent.kind == INTENT_MARKET:
        return build_market_report(query, datasource=datasource)  # type: ignore[arg-type]
    if intent.kind == INTENT_SECTOR:
        return build_sector_report(query, datasource=datasource)  # type: ignore[arg-type]
    ds = datasource or DataSource()
    resolved_symbol, resolution_note = _resolve_symbol(intent, ds if hasattr(ds, 'get_search') else None)
    if resolved_symbol is None:
        return {
            'report_type': 'stock',
            'symbol': query,
            'intent': asdict(intent),
            'resolution_note': resolution_note,
            'data_snapshot': {'quote': {}, 'snapshot': {}},
            'technical': {'trend': '数据不足', 'signals': [], 'gap_view': '未解析到标的，无法生成技术面。'},
            'fundamental': {
                'status': 'empty',
                'analysis_mode': '轻量模式',
                'data_completeness': '明显不足',
                'conclusion': resolution_note,
            },
            'capital_flow': {'conclusion': '未解析到标的，无法生成资金面。'},
            'news': {'status': 'empty', 'conclusion': resolution_note},
            'prediction': {'baseline_view': resolution_note, 'invalidations': []},
            'raw_bundle': {},
        }
    report = build_stock_report(resolved_symbol, days=days, datasource=ds, intent=intent)  # type: ignore[arg-type]
    report['resolution_note'] = resolution_note
    return report


def build_report(symbol: str, days: int = DEFAULT_ANALYSIS_DAYS, datasource: BundleSource | None = None) -> ReportPayload:
    return build_stock_report(symbol, days=days, datasource=datasource)
