#!/usr/bin/env python3
from __future__ import annotations

from stock_common.symbols import normalize_symbol

from ..interface import ProviderResult
from .base import BaseProvider


class OpenCliProvider(BaseProvider):
    def __init__(self, backend, available: bool) -> None:
        super().__init__('opencli', backend, available)

    def get_search(self, query: str) -> ProviderResult:
        return self._opencli_first(
            [
                ('dc', 'search', '--query', query),
                ('xq', 'search', '--query', query),
            ],
            wrap_items=True,
        )

    def get_quote(self, symbol: str) -> ProviderResult:
        normalized = normalize_symbol(symbol)
        return self._opencli_first(
            [
                ('xq', 'quote', '--symbol', normalized),
                ('dc', 'quote', '--symbol', normalized),
            ]
        )

    def get_kline(self, symbol: str, days: int = 120) -> ProviderResult:
        normalized = normalize_symbol(symbol)
        return self._opencli_first(
            [
                ('dc', 'history', '--symbol', normalized, '--days', str(days)),
                ('xq', 'history', '--symbol', normalized, '--days', str(days)),
            ],
            wrap_items=True,
        )

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
