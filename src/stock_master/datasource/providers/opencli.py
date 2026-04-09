#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from stock_master.common.symbols import (
    QUERY_KIND_NATURAL_LANGUAGE,
    QUERY_KIND_THEME,
    classify_query_input,
    preferred_provider_groups,
    normalize_symbol,
)

from ..interface import ProviderPayload, ProviderResult
from .base import BaseProvider

OPENCLI_PROVIDER_NAMES = [
    'opencli-dc',
    'opencli-xq',
    'opencli-xueqiu',
    'opencli-sinafinance',
    'opencli-bloomberg',
    'opencli-yahoo-finance',
    'opencli-iwc',
]


class OpenCliFamilyProvider(BaseProvider):
    def _fetch_standardized_items(self, parts: tuple[str, ...], *, source_channel: str, kind: str) -> list[dict[str, Any]]:
        result = self._opencli_json(*parts, wrap_items=True)
        if result is False:
            return []
        rows = result.get('items') or []
        if isinstance(result, dict) and not rows:
            rows = [result]
        return [self._normalize_item(row, source_channel=source_channel, kind=kind) for row in rows if isinstance(row, dict)]

    def _normalize_item(
        self,
        row: ProviderPayload,
        *,
        source_channel: str,
        kind: str,
        default_title: str | None = None,
    ) -> ProviderPayload:
        title = self._first_str(
            row,
            'title',
            'text',
            'content',
            'report_name',
            'name',
            'question',
            'company',
            default=default_title or '',
        )
        item_date = self._first_str(
            row,
            'date',
            'time',
            'datetime',
            'created_at',
            'published_at',
            'publish_time',
            'pub_time',
            'ctime',
            'earnings_date',
        )
        url = self._first_str(row, 'url', 'link', 'href')
        normalized = dict(row)
        normalized.setdefault('title', title)
        normalized.setdefault('date', item_date)
        normalized.setdefault('url', url)
        normalized['source_channel'] = source_channel
        normalized['kind'] = kind
        return normalized

    def _first_str(self, row: ProviderPayload, *keys: str, default: str | None = None) -> str | None:
        for key in keys:
            value = row.get(key)
            if value not in (None, ''):
                return str(value)
        return default

    def _looks_like_question(self, query: str) -> bool:
        query_kind = classify_query_input(query)['kind']
        return query_kind in {QUERY_KIND_NATURAL_LANGUAGE, QUERY_KIND_THEME}

    def _is_a_share_symbol(self, symbol: str) -> bool:
        normalized = normalize_symbol(symbol)
        return normalized.startswith(('SH', 'SZ', 'BJ'))


class OpenCliDcProvider(OpenCliFamilyProvider):
    def __init__(self, backend, available: bool) -> None:
        super().__init__('opencli-dc', backend, available)

    def get_search(self, query: str) -> ProviderResult:
        return self._opencli_json('dc', 'search', '--query', query, wrap_items=True)

    def get_quote(self, symbol: str) -> ProviderResult:
        return self._opencli_json('dc', 'quote', '--symbol', normalize_symbol(symbol))

    def get_kline(self, symbol: str, days: int = 120) -> ProviderResult:
        return self._opencli_json('dc', 'history', '--symbol', normalize_symbol(symbol), '--days', str(days), wrap_items=True)

    def get_money_flow(self, symbol: str) -> ProviderResult:
        normalized = normalize_symbol(symbol)
        result = self._opencli_json('dc', 'stock-flow', '--symbol', normalized, wrap_items=True)
        if result is False:
            return False
        items = result.get('items') or []
        if not items:
            return False
        latest = items[-1]
        return {
            'symbol': normalized,
            'items': items,
            'latest': latest,
            'mainNetInflow': latest.get('mainNetInflow'),
            'superLargeNetInflow': latest.get('superLargeNetInflow'),
            'largeNetInflow': latest.get('largeNetInflow'),
            'mediumNetInflow': latest.get('mediumNetInflow'),
            'smallNetInflow': latest.get('smallNetInflow'),
        }

    def get_north_flow(self) -> ProviderResult:
        return self._opencli_json('dc', 'north-flow', wrap_items=True)

    def get_sector_money_flow(self) -> ProviderResult:
        return self._opencli_json('dc', 'sector-flow', wrap_items=True)

    def get_sector_list(self) -> ProviderResult:
        return self._opencli_json('dc', 'search', '--query', '板块', wrap_items=True)

    def get_sector_members(self, sector_code: str) -> ProviderResult:
        return self._opencli_json('dc', 'sector-members', '--board_code', sector_code, '--limit', '30', wrap_items=True)

    def get_limit_up(self, date: str | None = None) -> ProviderResult:
        return self._opencli_json('dc', 'top-gainers', '--limit', '30', wrap_items=True)

    def get_limit_down(self, date: str | None = None) -> ProviderResult:
        return self._opencli_json('dc', 'top-losers', '--limit', '30', wrap_items=True)


class OpenCliXqProvider(OpenCliFamilyProvider):
    def __init__(self, backend, available: bool) -> None:
        super().__init__('opencli-xq', backend, available)

    def get_search(self, query: str) -> ProviderResult:
        return self._opencli_json('xq', 'search', '--query', query, wrap_items=True)

    def get_quote(self, symbol: str) -> ProviderResult:
        return self._opencli_json('xq', 'quote', '--symbol', normalize_symbol(symbol))

    def get_kline(self, symbol: str, days: int = 120) -> ProviderResult:
        return self._opencli_json('xq', 'history', '--symbol', normalize_symbol(symbol), '--days', str(days), wrap_items=True)


class OpenCliXueqiuProvider(OpenCliFamilyProvider):
    def __init__(self, backend, available: bool) -> None:
        super().__init__('opencli-xueqiu', backend, available)

    def get_search(self, query: str) -> ProviderResult:
        return self._opencli_json('xueqiu', 'search', query, wrap_items=True)

    def get_quote(self, symbol: str) -> ProviderResult:
        return self._opencli_json('xueqiu', 'stock', normalize_symbol(symbol))

    def get_kline(self, symbol: str, days: int = 120) -> ProviderResult:
        return self._opencli_json('xueqiu', 'kline', normalize_symbol(symbol), wrap_items=True)

    def get_news(self, symbol: str | None = None) -> ProviderResult:
        if not symbol:
            return False
        items = self._fetch_standardized_items(
            ('xueqiu', 'comments', normalize_symbol(symbol)),
            source_channel='xueqiu.comments',
            kind='commentary',
        )
        if not items:
            return False
        return {'symbol': normalize_symbol(symbol), 'items': items, 'status': 'ok'}

    def get_research(self, symbol: str) -> ProviderResult:
        normalized = normalize_symbol(symbol)
        items: list[dict[str, Any]] = []
        items.extend(
            self._fetch_standardized_items(
                ('xueqiu', 'comments', normalized),
                source_channel='xueqiu.comments',
                kind='research',
            )
        )
        items.extend(
            self._fetch_standardized_items(
                ('xueqiu', 'earnings-date', normalized),
                source_channel='xueqiu.earnings-date',
                kind='earnings_date',
            )
        )
        if not items:
            return False
        return {'symbol': normalized, 'items': items, 'status': 'ok'}

    def get_announcements(self, symbol: str, days: int = 180) -> ProviderResult:
        normalized = normalize_symbol(symbol)
        items: list[dict[str, Any]] = []
        items.extend(
            self._fetch_standardized_items(
                ('xueqiu', 'earnings-date', normalized),
                source_channel='xueqiu.earnings-date',
                kind='announcement',
            )
        )
        items.extend(
            self._fetch_standardized_items(
                ('xueqiu', 'comments', normalized),
                source_channel='xueqiu.comments',
                kind='announcement_commentary',
            )
        )
        if not items:
            return False
        return {'symbol': normalized, 'days': days, 'items': items, 'status': 'ok'}


class OpenCliSinaFinanceProvider(OpenCliFamilyProvider):
    def __init__(self, backend, available: bool) -> None:
        super().__init__('opencli-sinafinance', backend, available)

    def get_quote(self, symbol: str) -> ProviderResult:
        normalized = normalize_symbol(symbol)
        if not self._is_a_share_symbol(normalized):
            return False
        return self._opencli_json('sinafinance', 'stock', normalized)

    def get_news(self, symbol: str | None = None) -> ProviderResult:
        items: list[dict[str, Any]] = []
        items.extend(self._fetch_standardized_items(('sinafinance', 'news'), source_channel='sinafinance.news', kind='news'))
        items.extend(self._fetch_standardized_items(('sinafinance', 'rolling-news'), source_channel='sinafinance.rolling-news', kind='news_flash'))
        if not items:
            return False
        return {'symbol': normalize_symbol(symbol) if symbol else None, 'items': items, 'status': 'ok'}


class OpenCliBloombergProvider(OpenCliFamilyProvider):
    def __init__(self, backend, available: bool) -> None:
        super().__init__('opencli-bloomberg', backend, available)

    def get_news(self, symbol: str | None = None) -> ProviderResult:
        items = self._fetch_standardized_items(('bloomberg', 'markets'), source_channel='bloomberg.markets', kind='market_news')
        if not items:
            return False
        return {'symbol': normalize_symbol(symbol) if symbol else None, 'items': items, 'status': 'ok'}


class OpenCliYahooFinanceProvider(OpenCliFamilyProvider):
    def __init__(self, backend, available: bool) -> None:
        super().__init__('opencli-yahoo-finance', backend, available)

    def get_quote(self, symbol: str) -> ProviderResult:
        normalized = normalize_symbol(symbol)
        if self._is_a_share_symbol(normalized):
            return False
        return self._opencli_json('yahoo-finance', 'quote', normalized)


class OpenCliIwcProvider(OpenCliFamilyProvider):
    def __init__(self, backend, available: bool) -> None:
        super().__init__('opencli-iwc', backend, available)

    def get_search(self, query: str) -> ProviderResult:
        if not self._looks_like_question(query):
            return False
        iwc = self._opencli_json('iwc', 'query', '--question', query)
        if iwc is False:
            return False
        return {
            'query': query,
            'items': [self._normalize_item(iwc, source_channel='iwc.query', kind='qa', default_title=query)],
        }


class OpenCliProvider(OpenCliFamilyProvider):
    """Legacy composite provider kept for backwards-compatible direct imports/tests."""

    def __init__(self, backend, available: bool) -> None:
        super().__init__('opencli', backend, available)
        self._provider_map = {
            'dc': OpenCliDcProvider(backend, available),
            'xq': OpenCliXqProvider(backend, available),
            'xueqiu': OpenCliXueqiuProvider(backend, available),
            'sinafinance': OpenCliSinaFinanceProvider(backend, available),
            'bloomberg': OpenCliBloombergProvider(backend, available),
            'yahoo-finance': OpenCliYahooFinanceProvider(backend, available),
            'iwc': OpenCliIwcProvider(backend, available),
        }

    def _ordered_providers(self, capability: str, *args: Any) -> list[OpenCliFamilyProvider]:
        first_arg = args[0] if args else None
        groups = preferred_provider_groups(capability, first_arg)
        family_names = {f'opencli-{name}' for name in self._provider_map}
        ordered_names: list[str] = []
        seen: set[str] = set()

        for group in groups:
            for provider_name in group:
                if provider_name not in family_names:
                    continue
                short_name = provider_name.removeprefix('opencli-')
                if short_name in seen or short_name not in self._provider_map:
                    continue
                ordered_names.append(short_name)
                seen.add(short_name)

        for short_name in self._provider_map:
            if short_name in seen:
                continue
            ordered_names.append(short_name)
            seen.add(short_name)
        return [self._provider_map[name] for name in ordered_names if name in self._provider_map]

    def _first_supported(self, capability: str, *args: Any) -> ProviderResult:
        for provider in self._ordered_providers(capability, *args):
            handler = getattr(provider, capability)
            result = handler(*args)
            if result is not False:
                return result
        return False

    def get_search(self, query: str) -> ProviderResult:
        return self._first_supported('get_search', query)

    def get_quote(self, symbol: str) -> ProviderResult:
        return self._first_supported('get_quote', symbol)

    def get_kline(self, symbol: str, days: int = 120) -> ProviderResult:
        return self._first_supported('get_kline', symbol, days)

    def get_news(self, symbol: str | None = None) -> ProviderResult:
        items: list[dict[str, Any]] = []
        for provider in self._ordered_providers('get_news', symbol):
            result = getattr(provider, 'get_news')(symbol)
            if result is False:
                continue
            items.extend(result.get('items') or [])
        if not items:
            return False
        return {'symbol': normalize_symbol(symbol) if symbol else None, 'items': items, 'status': 'ok'}

    def get_research(self, symbol: str) -> ProviderResult:
        return self._first_supported('get_research', symbol)

    def get_announcements(self, symbol: str, days: int = 180) -> ProviderResult:
        return self._first_supported('get_announcements', symbol, days)

    def get_money_flow(self, symbol: str) -> ProviderResult:
        return self._first_supported('get_money_flow', symbol)

    def get_north_flow(self) -> ProviderResult:
        return self._first_supported('get_north_flow')

    def get_sector_money_flow(self) -> ProviderResult:
        return self._first_supported('get_sector_money_flow')

    def get_sector_list(self) -> ProviderResult:
        return self._first_supported('get_sector_list')

    def get_sector_members(self, sector_code: str) -> ProviderResult:
        return self._first_supported('get_sector_members', sector_code)

    def get_limit_up(self, date: str | None = None) -> ProviderResult:
        return self._first_supported('get_limit_up', date)

    def get_limit_down(self, date: str | None = None) -> ProviderResult:
        return self._first_supported('get_limit_down', date)
