#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
import re

from stock_master.common.symbols import classify_query_input, infer_market, normalize_symbol

INTENT_STOCK = 'stock_report'
INTENT_MARKET = 'market_overview'
INTENT_SECTOR = 'sector_overview'
MODE_STANDARD = 'standard'
MODE_DEEP_TECHNICAL = 'deep_technical'
MODE_DEEP_FUNDAMENTAL = 'deep_fundamental'

MARKET_KEYWORDS = (
    '大盘',
    '市场',
    '指数',
    '北向',
    '涨幅榜',
    '跌幅榜',
    '涨停',
    '跌停',
    '连板',
    '情绪',
)
SECTOR_KEYWORDS = (
    '板块',
    '行业',
    '概念',
    '轮动',
    '题材',
)
DEEP_TECHNICAL_KEYWORDS = (
    '像虾评一样',
    '支撑位',
    '压力位',
    '未来三天',
    '未来3天',
    '预测未来几天',
    '看看走势',
    '缺口',
    '技术分析',
)
DEEP_FUNDAMENTAL_KEYWORDS = (
    '财报侦探',
    '价值投资',
    '深度估值',
    '价值分析',
    'roic',
    'wacc',
    'dcf',
    '杜邦',
)


@dataclass(frozen=True)
class AnalysisIntent:
    kind: str
    raw_query: str
    symbol: str | None = None
    query_shape: str = 'unknown'
    search_query: str | None = None
    market: str = 'unknown'
    mode: str = MODE_STANDARD
    supported: bool = True
    notes: tuple[str, ...] = ()
    wants_market_context: bool = False
    wants_sector_context: bool = False


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _extract_symbol_candidate(text: str) -> str | None:
    match = re.search(r'\b(?:SH|SZ|BJ)\d{6}\b', text, flags=re.IGNORECASE)
    if match:
        return normalize_symbol(match.group())
    match = re.search(r'(?<!\d)(\d{6})(?!\d)', text)
    if match:
        return normalize_symbol(match.group(1))
    match = re.search(r'\b[A-Z]{2,5}(?:\.[A-Z]{1,4})?\b', text)
    if match:
        return normalize_symbol(match.group())
    return None


def parse_analysis_intent(query: str) -> AnalysisIntent:
    text = str(query or '').strip()
    classified = classify_query_input(text)
    query_shape = classified['kind']
    normalized = _extract_symbol_candidate(text) or classified['normalized']
    market = infer_market(normalized if normalized else text)
    wants_market_context = _contains_any(text, MARKET_KEYWORDS)
    wants_sector_context = _contains_any(text, SECTOR_KEYWORDS)
    lower_text = text.lower()
    mode = MODE_STANDARD
    if _contains_any(text, DEEP_TECHNICAL_KEYWORDS):
        mode = MODE_DEEP_TECHNICAL
    elif any(keyword in lower_text for keyword in DEEP_FUNDAMENTAL_KEYWORDS):
        mode = MODE_DEEP_FUNDAMENTAL

    notes: list[str] = []
    supported = True

    if query_shape in {'symbol', 'numeric_code', 'ticker'}:
        symbol = normalize_symbol(normalized)
    elif normalized and infer_market(normalized) != 'unknown':
        symbol = normalize_symbol(normalized)
    else:
        symbol = None

    if wants_sector_context:
        return AnalysisIntent(
            kind=INTENT_SECTOR,
            raw_query=text,
            symbol=symbol,
            query_shape=query_shape,
            search_query=text if symbol is None else None,
            market=market,
            mode=mode,
            supported=supported,
            notes=tuple(notes),
            wants_market_context=True,
            wants_sector_context=True,
        )

    if wants_market_context and symbol is None:
        return AnalysisIntent(
            kind=INTENT_MARKET,
            raw_query=text,
            query_shape=query_shape,
            search_query=text,
            market=market,
            mode=MODE_STANDARD,
            supported=True,
            notes=tuple(notes),
            wants_market_context=True,
            wants_sector_context=wants_sector_context,
        )

    if mode in {MODE_DEEP_TECHNICAL, MODE_DEEP_FUNDAMENTAL} and market not in {'a_share', 'unknown'}:
        supported = False
        notes.append('当前深度技术面 / 深度基本面模式仅面向 A 股，已自动降级为通用股票报告。')

    return AnalysisIntent(
        kind=INTENT_STOCK,
        raw_query=text,
        symbol=symbol,
        query_shape=query_shape,
        search_query=text if symbol is None else None,
        market=market,
        mode=mode,
        supported=supported,
        notes=tuple(notes),
        wants_market_context=wants_market_context,
        wants_sector_context=wants_sector_context,
    )
