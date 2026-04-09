#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any

QUERY_KIND_EMPTY = 'empty'
QUERY_KIND_SYMBOL = 'symbol'
QUERY_KIND_NUMERIC_CODE = 'numeric_code'
QUERY_KIND_TICKER = 'ticker'
QUERY_KIND_BOARD_CODE = 'board_code'
QUERY_KIND_THEME = 'theme'
QUERY_KIND_NATURAL_LANGUAGE = 'natural_language'
QUERY_KIND_KEYWORD = 'keyword'


def normalize_symbol(symbol: str) -> str:
    text = str(symbol).strip().upper()
    if re.fullmatch(r'\d{6}', text):
        if text.startswith(('6', '9')):
            return f'SH{text}'
        if text.startswith(('0', '3')):
            return f'SZ{text}'
        if text.startswith(('4', '8')):
            return f'BJ{text}'
    return text


def code_only(symbol: str) -> str:
    return re.sub(r'^(SH|SZ|BJ)', '', normalize_symbol(symbol))


def is_a_share_symbol(symbol: str) -> bool:
    normalized = normalize_symbol(symbol)
    return normalized.startswith(('SH', 'SZ', 'BJ'))


def infer_market(symbol: str | None) -> str:
    if symbol in (None, ''):
        return 'unknown'
    normalized = normalize_symbol(symbol)
    if normalized.startswith(('SH', 'SZ', 'BJ')):
        return 'a_share'
    if re.fullmatch(r'HK\d{4,5}|\d{4,5}\.HK', normalized):
        return 'hk'
    if re.fullmatch(r'\^?[A-Z][A-Z0-9.\-]{0,9}', normalized):
        return 'global'
    return 'unknown'


def looks_like_natural_language_query(text: str) -> bool:
    query = str(text).strip()
    if not query:
        return False
    if any(token in query for token in ('？', '?', '怎么看', '如何', '什么', '为何', '为什么', '市场', '情绪', '消息', '新闻', '怎么判断', '是否值得')):
        return True
    if len(query) >= 12 and bool(re.search(r'[\u4e00-\u9fff]{4,}', query)):
        return True
    return bool(re.search(r'[\u4e00-\u9fff]{6,}', query))


def infer_instrument(symbol: str | None) -> str:
    if symbol in (None, ''):
        return 'unknown'
    normalized = normalize_symbol(symbol)
    if normalized.startswith(('SH', 'SZ', 'BJ')):
        return 'equity'
    if normalized.startswith('^'):
        return 'index'
    if normalized.endswith(('.HK',)) or normalized.startswith('HK'):
        return 'equity'
    if re.fullmatch(r'[A-Z]{1,6}', normalized):
        return 'equity'
    return 'unknown'


def routing_profile(value: str | None) -> tuple[str, str]:
    return infer_market(value), infer_instrument(value)


def looks_like_theme_query(text: str) -> bool:
    query = str(text).strip()
    if not query:
        return False
    if looks_like_natural_language_query(query):
        return False
    upper = query.upper()
    if re.fullmatch(r'BK\d{4,6}', upper):
        return False
    if re.search(r'[\u4e00-\u9fff]{2,}', query):
        return True
    return any(token in query.lower() for token in ('theme', 'sector', 'concept', 'screen', 'leader', 'dividend', 'bank'))


def classify_query_input(value: Any) -> dict[str, str]:
    text = str(value or '').strip()
    if not text:
        return {'kind': QUERY_KIND_EMPTY, 'normalized': ''}
    normalized = normalize_symbol(text)
    upper = normalized.upper()
    if re.fullmatch(r'BK\d{4,6}', upper):
        return {'kind': QUERY_KIND_BOARD_CODE, 'normalized': upper}
    if re.fullmatch(r'(SH|SZ|BJ)\d{6}', normalized):
        return {'kind': QUERY_KIND_SYMBOL, 'normalized': normalized}
    if re.fullmatch(r'\d{6}', text):
        return {'kind': QUERY_KIND_NUMERIC_CODE, 'normalized': normalized}
    if re.fullmatch(r'[A-Z]{1,6}(\.[A-Z]{1,4})?', normalized) or re.fullmatch(r'\^?[A-Z][A-Z0-9.\-]{0,9}', normalized):
        return {'kind': QUERY_KIND_TICKER, 'normalized': normalized}
    if looks_like_natural_language_query(text):
        return {'kind': QUERY_KIND_NATURAL_LANGUAGE, 'normalized': normalized}
    if looks_like_theme_query(text):
        return {'kind': QUERY_KIND_THEME, 'normalized': normalized}
    return {'kind': QUERY_KIND_KEYWORD, 'normalized': normalized}


def query_shape(value: Any) -> str:
    return classify_query_input(value)['kind']


def build_routing_context(value: Any) -> dict[str, str]:
    text = str(value or '').strip()
    market, instrument = routing_profile(text if text else None)
    classified = classify_query_input(text)
    return {
        'market': market,
        'instrument': instrument,
        'query_shape': classified['kind'],
        'normalized': classified['normalized'],
    }


def capability_routing_hint(capability: str, first_arg: Any = None) -> dict[str, str]:
    context = build_routing_context(first_arg)
    context['capability'] = capability
    return context


def is_information_capability(capability: str) -> bool:
    return capability in {'get_news', 'get_research', 'get_announcements'}


def is_market_data_capability(capability: str) -> bool:
    return capability in {
        'get_quote',
        'get_snapshot',
        'get_intraday',
        'get_kline',
        'get_money_flow',
        'get_north_flow',
        'get_sector_money_flow',
        'get_sector_list',
        'get_sector_members',
        'get_limit_up',
        'get_limit_down',
        'get_search',
    }


def prefers_global_market_sources(capability: str, first_arg: Any = None) -> bool:
    hint = capability_routing_hint(capability, first_arg)
    return hint['market'] in {'global', 'hk'} and capability in {'get_quote', 'get_snapshot', 'get_intraday', 'get_kline', 'get_search', 'get_news'}


def prefers_natural_language_source(capability: str, first_arg: Any = None) -> bool:
    hint = capability_routing_hint(capability, first_arg)
    return capability == 'get_search' and hint['query_shape'] in {QUERY_KIND_NATURAL_LANGUAGE, QUERY_KIND_THEME}


def prefers_a_share_news_mix(capability: str, first_arg: Any = None) -> bool:
    hint = capability_routing_hint(capability, first_arg)
    return capability in {'get_news', 'get_research', 'get_announcements'} and hint['market'] == 'a_share'


def prefers_global_news_mix(capability: str, first_arg: Any = None) -> bool:
    hint = capability_routing_hint(capability, first_arg)
    return capability in {'get_news', 'get_research', 'get_announcements'} and hint['market'] in {'global', 'hk'}


def prefers_a_share_quote_stack(capability: str, first_arg: Any = None) -> bool:
    hint = capability_routing_hint(capability, first_arg)
    return capability in {'get_quote', 'get_snapshot', 'get_intraday', 'get_kline'} and hint['market'] == 'a_share'


def prefers_global_quote_stack(capability: str, first_arg: Any = None) -> bool:
    hint = capability_routing_hint(capability, first_arg)
    return capability in {'get_quote', 'get_snapshot', 'get_intraday', 'get_kline'} and hint['market'] in {'global', 'hk'}


def prefers_sector_flow_stack(capability: str, first_arg: Any = None) -> bool:
    return capability in {'get_money_flow', 'get_north_flow', 'get_sector_money_flow', 'get_sector_list', 'get_sector_members', 'get_limit_up', 'get_limit_down'}


def prefers_fundamental_stack(capability: str, first_arg: Any = None) -> bool:
    return capability in {
        'get_financial',
        'get_report',
        'get_income_statement',
        'get_balance_sheet',
        'get_cash_flow',
        'get_main_holders',
        'get_shareholder_changes',
        'get_dividend',
    }


def preferred_provider_groups(capability: str, first_arg: Any = None) -> list[list[str]]:
    if prefers_natural_language_source(capability, first_arg):
        return [['opencli-iwc'], ['opencli-dc', 'opencli-xq', 'opencli-xueqiu']]
    if prefers_a_share_quote_stack(capability, first_arg):
        return [['akshare', 'adata', 'baostock'], ['opencli-xq', 'opencli-dc', 'opencli-xueqiu', 'opencli-sinafinance']]
    if prefers_global_quote_stack(capability, first_arg):
        return [['opencli-yahoo-finance', 'opencli-xq', 'opencli-xueqiu', 'opencli-bloomberg', 'opencli-dc']]
    if prefers_a_share_news_mix(capability, first_arg):
        return [['opencli-sinafinance', 'opencli-xueqiu'], ['opencli-bloomberg', 'opencli-iwc'], ['akshare', 'adata', 'baostock']]
    if prefers_global_news_mix(capability, first_arg):
        return [['opencli-bloomberg', 'opencli-xueqiu'], ['opencli-sinafinance', 'opencli-iwc']]
    if prefers_sector_flow_stack(capability, first_arg):
        return [['akshare', 'adata', 'baostock'], ['opencli-dc']]
    if prefers_fundamental_stack(capability, first_arg):
        return [['akshare', 'adata', 'baostock'], ['opencli-xueqiu', 'opencli-iwc']]
    if capability == 'get_search':
        return [['opencli-dc', 'opencli-xq', 'opencli-xueqiu'], ['akshare', 'adata', 'baostock'], ['opencli-iwc']]
    return []
