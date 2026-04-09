#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from stock_common.cache import cache_get, cache_set
from stock_common.symbols import normalize_symbol

from .backend import CommandBackend
from .interface import StockDataProvider
from .providers import build_provider_map, order_providers
from .runtime import ProviderRouter

DEFAULT_PYTHON_VENV = str(Path(__file__).resolve().parents[2] / '.venv' / 'bin' / 'python')
DEFAULT_PRIORITY = ['akshare', 'adata', 'baostock', 'opencli']


class DataSource:
    """Facade for the stock-master datasource layer."""

    def __init__(
        self,
        *,
        backend: CommandBackend | None = None,
        python_venv: str = DEFAULT_PYTHON_VENV,
        provider_available: Mapping[str, bool] | None = None,
        providers: Sequence[StockDataProvider] | None = None,
        priority: Sequence[str] | None = None,
        cache_reader: Callable[..., Any] = cache_get,
        cache_writer: Callable[[str, Any], None] = cache_set,
        cache_enabled: bool = True,
        per_source_timeout: float = 15,
    ) -> None:
        self.backend = backend or CommandBackend(python_venv=python_venv)
        detected = {
            'akshare': self.backend.check_module('akshare'),
            'adata': self.backend.check_module('adata'),
            'baostock': self.backend.check_module('baostock'),
            'opencli': self.backend.opencli_available,
        }
        if provider_available:
            detected.update(provider_available)
        self.provider_available = detected
        self.priority = list(priority or DEFAULT_PRIORITY)

        self.akshare_available = detected['akshare']
        self.adata_available = detected['adata']
        self.baostock_available = detected['baostock']
        self.opencli_available = detected['opencli']

        self.provider_map = build_provider_map(self.backend, detected)
        self.providers = list(providers or order_providers(self.provider_map, self.priority))
        self.router = ProviderRouter(self.providers, per_provider_timeout=per_source_timeout)
        self.cache_reader = cache_reader
        self.cache_writer = cache_writer
        self.cache_enabled = cache_enabled

    def diagnostics(self) -> dict[str, Any]:
        return {
            'opencli_available': self.opencli_available,
            'akshare_available': self.akshare_available,
            'adata_available': self.adata_available,
            'baostock_available': self.baostock_available,
            'priority': self.priority,
            'providers': [provider.name for provider in self.providers],
        }

    def _placeholder(self, symbol: str | None, note: str, fallback_path: list[str]) -> dict[str, Any]:
        return {
            'symbol': symbol,
            'status': 'placeholder',
            'note': note,
            'fallback_path': fallback_path,
        }

    def _cache_get(self, key: str, ttl_seconds: int) -> Any:
        if not self.cache_enabled:
            return None
        return self.cache_reader(key, ttl_seconds=ttl_seconds)

    def _cache_set(self, key: str, data: Any) -> None:
        if not self.cache_enabled:
            return
        self.cache_writer(key, data)

    def _dispatch(self, capability: str, *args: Any) -> dict[str, Any]:
        return self.router.dispatch(capability, *args)

    def _dispatch_with_cache(self, cache_key: str, ttl_seconds: int, capability: str, *args: Any) -> dict[str, Any]:
        cached = self._cache_get(cache_key, ttl_seconds=ttl_seconds)
        if cached is not None:
            return cached
        data = self._dispatch(capability, *args)
        self._cache_set(cache_key, data)
        return data

    def get_search(self, query: str) -> dict[str, Any]:
        return self._dispatch_with_cache(f'search_{query}', 300, 'get_search', query)

    def get_quote(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        return self._dispatch_with_cache(f'quote_{normalized}', 20, 'get_quote', normalized)

    def get_snapshot(self, symbol: str) -> dict[str, Any]:
        return self.get_quote(symbol)

    def get_kline(self, symbol: str, days: int = 120) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        return self._dispatch_with_cache(f'kline_{normalized}_{days}', 180, 'get_kline', normalized, days)

    def get_intraday(self, symbol: str) -> dict[str, Any]:
        return self.get_quote(symbol)

    def get_money_flow(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        return self._dispatch_with_cache(f'flow_{normalized}', 120, 'get_money_flow', normalized)

    def get_north_flow(self) -> dict[str, Any]:
        return self._dispatch_with_cache('north_flow', 120, 'get_north_flow')

    def get_sector_money_flow(self) -> dict[str, Any]:
        return self._dispatch_with_cache('sector_flow', 180, 'get_sector_money_flow')

    def get_financial(self, symbol: str) -> dict[str, Any]:
        return self._dispatch('get_financial', normalize_symbol(symbol))

    def get_report(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch('get_report', normalized)
        if data.get('status') == 'empty':
            return self._placeholder(normalized, '财报摘要未命中可用数据源', data.get('fallback_path', []))
        return data

    def get_income_statement(self, symbol: str, period: str = 'yearly') -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch_with_cache(f'income_{normalized}_{period}', 43200, 'get_income_statement', normalized, period)
        if data.get('status') == 'empty':
            return self._placeholder(normalized, '利润表暂未命中可用数据源', data.get('fallback_path', []))
        return data

    def get_balance_sheet(self, symbol: str, period: str = 'yearly') -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch_with_cache(f'balance_{normalized}_{period}', 43200, 'get_balance_sheet', normalized, period)
        if data.get('status') == 'empty':
            return self._placeholder(normalized, '资产负债表暂未命中可用数据源', data.get('fallback_path', []))
        return data

    def get_cash_flow(self, symbol: str, period: str = 'yearly') -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch_with_cache(f'cash_{normalized}_{period}', 43200, 'get_cash_flow', normalized, period)
        if data.get('status') == 'empty':
            return self._placeholder(normalized, '现金流量表暂未命中可用数据源', data.get('fallback_path', []))
        return data

    def get_announcements(self, symbol: str, days: int = 180) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch_with_cache(f'announcements_{normalized}_{days}', 21600, 'get_announcements', normalized, days)
        if data.get('status') != 'empty':
            return data
        return self._placeholder(normalized, '公告真实源尚未接通或未命中数据。', data.get('fallback_path', []))

    def get_main_holders(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch_with_cache(f'holders_{normalized}', 43200, 'get_main_holders', normalized)
        if data.get('status') != 'empty':
            return data
        return self._placeholder(normalized, '主要股东数据暂未命中可用数据源。', data.get('fallback_path', []))

    def get_shareholder_changes(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch_with_cache(f'shareholder_changes_{normalized}', 21600, 'get_shareholder_changes', normalized)
        if data.get('status') != 'empty':
            return data
        return self._placeholder(normalized, '股东变动数据暂未命中可用数据源。', data.get('fallback_path', []))

    def get_dividend(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch_with_cache(f'dividend_{normalized}', 43200, 'get_dividend', normalized)
        if data.get('status') != 'empty':
            return data
        return self._placeholder(normalized, '历史分红数据暂未命中可用数据源。', data.get('fallback_path', []))

    def get_sector_list(self) -> dict[str, Any]:
        return self._dispatch('get_sector_list')

    def get_sector_members(self, sector_code: str) -> dict[str, Any]:
        return self._dispatch('get_sector_members', sector_code)

    def get_limit_up(self, date: str | None = None) -> dict[str, Any]:
        return self._dispatch('get_limit_up', date)

    def get_limit_down(self, date: str | None = None) -> dict[str, Any]:
        return self._dispatch('get_limit_down', date)

    def get_news(self, symbol: str | None = None) -> dict[str, Any]:
        data = self._dispatch('get_news', symbol)
        if data.get('status') != 'empty':
            return data
        return self._placeholder(symbol, '消息面真实源尚未接通；当前不伪造新闻数据。', data.get('fallback_path', []))

    def get_research(self, symbol: str) -> dict[str, Any]:
        data = self._dispatch('get_research', symbol)
        if data.get('status') != 'empty':
            return data
        return self._placeholder(symbol, '研报真实源尚未接通；当前不伪造研报数据。', data.get('fallback_path', []))

    def get_deep_fundamental_bundle(self, symbol: str, *, period: str = 'yearly', announcement_days: int = 180) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        return {
            'symbol': normalized,
            'income_statement': self.get_income_statement(normalized, period=period),
            'balance_sheet': self.get_balance_sheet(normalized, period=period),
            'cash_flow': self.get_cash_flow(normalized, period=period),
            'announcements': self.get_announcements(normalized, days=announcement_days),
            'news': self.get_news(normalized),
            'research': self.get_research(normalized),
            'main_holders': self.get_main_holders(normalized),
            'shareholder_changes': self.get_shareholder_changes(normalized),
            'dividend': self.get_dividend(normalized),
        }

    def get_bundle(self, symbol: str, days: int = 120) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        return {
            'symbol': normalized,
            'quote': self.get_quote(normalized),
            'snapshot': self.get_snapshot(normalized),
            'kline': self.get_kline(normalized, days=days),
            'money_flow': self.get_money_flow(normalized),
            'north_flow': self.get_north_flow(),
            'sector_flow': self.get_sector_money_flow(),
            'financial': self.get_financial(normalized),
            'report': self.get_report(normalized),
            'news': self.get_news(normalized),
            'research': self.get_research(normalized),
        }
