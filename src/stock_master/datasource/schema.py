#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping

from stock_master.common.symbols import infer_market, normalize_symbol

SCHEMA_VERSION = 1

# Payload-level envelope keys that every provider result may expose. A provider
# can still return extra source-specific fields, but new code should start from
# these stable keys first.
PAYLOAD_ENVELOPE_KEYS = {
    'status',
    'capability',
    'symbol',
    'query',
    'market',
    'source',
    'source_detail',
    'source_channel',
    'sources',
    'fallback_path',
    'items',
    'rows',
    'latest',
    'meta',
    'extensions',
    'raw',
    'note',
    'days',
    'period',
    'routing_hint',
}

# Quote/search/event rows share many fields with top-level quote payloads, so
# we reserve the common aliases here as part of the public contract.
COMMON_RECORD_KEYS = {
    'id',
    'kind',
    'symbol',
    'code',
    'name',
    'title',
    'content',
    'summary',
    'date',
    'publish_time',
    'quote_time',
    'url',
    'author',
    'rating',
    'market',
    'source_channel',
    'meta',
    'extensions',
    'raw',
    'price',
    'current',
    'current_price',
    'latestPrice',
    'regularMarketPrice',
    'trade',
    'last_price',
    'close',
    'percent',
    'change',
    'open',
    'high',
    'low',
    'prevClose',
    'volume',
    'amount',
    'turnoverRate',
    'market_cap',
    'float_market_cap',
    'marketValue',
    'pe_ttm',
    'pb',
    '代码',
    '名称',
    '标题',
    '发布时间',
    '时间',
    '链接',
    '摘要',
    '新闻标题',
    '新闻内容',
    '报告名称',
    '机构',
    '公告标题',
    '公告时间',
    '最新价',
    '涨跌幅',
    '涨跌额',
    '开盘',
    '最高',
    '最低',
    '昨收',
    '成交量',
    '成交额',
    '换手率',
    '日期',
    '收盘',
    '总市值',
    '流通市值',
    '市盈率(TTM)',
    '市净率',
}

RESERVED_TOP_LEVEL_KEYS = PAYLOAD_ENVELOPE_KEYS | COMMON_RECORD_KEYS

CAPABILITY_PRIMARY_CONTAINER = {
    'search': 'items',
    'kline': 'items',
    'money_flow': 'items',
    'north_flow': 'items',
    'sector_money_flow': 'items',
    'financial': 'rows',
    'report': 'rows',
    'income_statement': 'rows',
    'balance_sheet': 'rows',
    'cash_flow': 'rows',
    'announcements': 'items',
    'main_holders': 'items',
    'shareholder_changes': 'items',
    'dividend': 'items',
    'sector_list': 'items',
    'sector_members': 'items',
    'limit_up': 'items',
    'limit_down': 'items',
    'news': 'items',
    'research': 'items',
}

CAPABILITY_DEFAULT_KIND = {
    'search': 'search_result',
    'kline': 'kline',
    'money_flow': 'money_flow',
    'north_flow': 'north_flow',
    'sector_money_flow': 'sector_money_flow',
    'financial': 'financial_row',
    'report': 'report_row',
    'income_statement': 'income_statement_row',
    'balance_sheet': 'balance_sheet_row',
    'cash_flow': 'cash_flow_row',
    'announcements': 'announcement',
    'main_holders': 'holder',
    'shareholder_changes': 'shareholder_change',
    'dividend': 'dividend',
    'sector_list': 'sector',
    'sector_members': 'sector_member',
    'limit_up': 'limit_up',
    'limit_down': 'limit_down',
    'news': 'news',
    'research': 'research',
}


def action_to_capability(action: str) -> str:
    return action.removeprefix('get_')


def infer_primary_container(payload: Mapping[str, Any], capability: str | None = None) -> str | None:
    for candidate in ('items', 'rows'):
        if isinstance(payload.get(candidate), list):
            return candidate
    if capability:
        return CAPABILITY_PRIMARY_CONTAINER.get(capability)
    return None


def default_record_kind(capability: str | None) -> str | None:
    if capability is None:
        return None
    return CAPABILITY_DEFAULT_KIND.get(capability)


def normalize_symbol_if_present(value: str | None) -> str | None:
    if value in (None, ''):
        return None
    return normalize_symbol(value)


def _merge_extensions(existing: Any, extra: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    if isinstance(existing, Mapping):
        merged.update({str(key): value for key, value in existing.items()})
    merged.update({key: value for key, value in extra.items() if value not in (None, '', [], {})})
    return merged


def _extensions_from(source: Mapping[str, Any], reserved_keys: set[str]) -> dict[str, Any]:
    return {
        key: value
        for key, value in source.items()
        if key not in reserved_keys and key not in {'meta', 'extensions', 'raw'} and value not in (None, '', [], {})
    }


def ensure_record_contract(
    record: Mapping[str, Any],
    *,
    capability: str | None = None,
    kind: str | None = None,
    symbol: str | None = None,
    source_channel: str | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    original = dict(record)
    normalized = dict(original)

    symbol_value = normalize_symbol_if_present(str(normalized.get('symbol') or symbol)) if (normalized.get('symbol') or symbol) else None
    if symbol_value:
        normalized['symbol'] = symbol_value

    market = infer_market(symbol_value) if symbol_value else None
    if market and normalized.get('market') in (None, '', 'unknown'):
        normalized['market'] = market

    if kind and normalized.get('kind') in (None, ''):
        normalized['kind'] = kind
    if source_channel and normalized.get('source_channel') in (None, ''):
        normalized['source_channel'] = source_channel

    meta = dict(original.get('meta') or {})
    meta.setdefault('schema_version', SCHEMA_VERSION)
    if capability:
        meta['capability'] = capability
    if normalized.get('kind'):
        meta['kind'] = normalized['kind']
    if normalized.get('source_channel'):
        meta['source_channel'] = normalized['source_channel']
    if market:
        meta['market'] = market
    normalized['meta'] = meta

    extensions = _merge_extensions(
        original.get('extensions'),
        _extensions_from(original, COMMON_RECORD_KEYS),
    )
    if extensions:
        normalized['extensions'] = extensions
    else:
        normalized.pop('extensions', None)
    if include_raw and 'raw' not in normalized:
        normalized['raw'] = original
    return normalized


def ensure_payload_contract(
    payload: Mapping[str, Any],
    *,
    capability: str | None = None,
    symbol: str | None = None,
    query: str | None = None,
    source_channel: str | None = None,
    status: str | None = None,
    default_item_kind: str | None = None,
    include_record_raw: bool = False,
    include_raw: bool = False,
) -> dict[str, Any]:
    original = dict(payload)
    normalized = dict(original)

    symbol_value = normalized.get('symbol') or symbol
    if symbol_value not in (None, ''):
        normalized['symbol'] = normalize_symbol(str(symbol_value))
    if query is not None and normalized.get('query') in (None, ''):
        normalized['query'] = query

    market = infer_market(normalized['symbol']) if normalized.get('symbol') else None
    if market and normalized.get('market') in (None, '', 'unknown'):
        normalized['market'] = market

    if capability:
        normalized['capability'] = capability
    if source_channel and normalized.get('source_channel') in (None, ''):
        normalized['source_channel'] = source_channel
    if status and normalized.get('status') in (None, ''):
        normalized['status'] = status
    elif normalized.get('status') in (None, ''):
        normalized['status'] = 'ok'

    container = infer_primary_container(normalized, capability)
    record_kind = default_item_kind or default_record_kind(capability)
    if container and isinstance(normalized.get(container), list):
        normalized[container] = [
            ensure_record_contract(
                item,
                capability=capability,
                kind=item.get('kind') or record_kind if isinstance(item, Mapping) else record_kind,
                symbol=normalized.get('symbol'),
                source_channel=item.get('source_channel') if isinstance(item, Mapping) else source_channel,
                include_raw=include_record_raw,
            )
            for item in normalized[container]
            if isinstance(item, Mapping)
        ]

    meta = dict(original.get('meta') or {})
    meta.setdefault('schema_version', SCHEMA_VERSION)
    if capability:
        meta['capability'] = capability
    if source_channel:
        meta.setdefault('source_channel', source_channel)
    if market:
        meta['market'] = market
    if container:
        meta['primary_container'] = container
        meta[f'{container}_count'] = len(normalized.get(container) or [])
    normalized['meta'] = meta

    extensions = _merge_extensions(
        original.get('extensions'),
        _extensions_from(original, RESERVED_TOP_LEVEL_KEYS),
    )
    if extensions:
        normalized['extensions'] = extensions
    else:
        normalized.pop('extensions', None)
    if include_raw and 'raw' not in normalized:
        normalized['raw'] = original
    return normalized


def wrap_placeholder_payload(
    *,
    capability: str,
    symbol: str | None = None,
    note: str,
    fallback_path: list[str],
) -> dict[str, Any]:
    return ensure_payload_contract(
        {
            'status': 'placeholder',
            'symbol': symbol,
            'note': note,
            'fallback_path': fallback_path,
        },
        capability=capability,
        symbol=symbol,
        status='placeholder',
    )
