#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from stock_master.common.cache import cache_get, cache_set
from stock_master.common.symbols import capability_routing_hint, normalize_symbol, preferred_provider_groups

from .backend import CommandBackend
from .interface import StockDataProvider, get_capability_spec
from .providers import build_provider_map, order_providers, reorder_provider_sequence
from .runtime import ProviderRouter
from .schema import wrap_placeholder_payload

DEFAULT_PYTHON_VENV = str(Path(__file__).resolve().parents[3] / '.venv' / 'bin' / 'python')
DEFAULT_PRIORITY = [
    'akshare',
    'adata',
    'baostock',
    'opencli-dc',
    'opencli-xq',
    'opencli-xueqiu',
    'opencli-sinafinance',
    'opencli-bloomberg',
    'opencli-yahoo-finance',
    'opencli-iwc',
]

CACHE_TTLS = {
    # Query/search routing is interactive but not tick-level.
    'search': 300,
    # Quote-like views should stay short-lived.
    'quote': 20,
    'kline': 180,
    # Capital flow and market breadth are short-cache market monitors.
    'money_flow': 120,
    'north_flow': 120,
    'sector_flow': 180,
    'limit_pool': 120,
    # Fundamental payloads are slow-moving and safe to cache longer.
    'statement': 43200,
    'event': 21600,
    'holder': 43200,
}


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
            'opencli-dc': self.backend.opencli_available,
            'opencli-xq': self.backend.opencli_available,
            'opencli-xueqiu': self.backend.opencli_available,
            'opencli-sinafinance': self.backend.opencli_available,
            'opencli-bloomberg': self.backend.opencli_available,
            'opencli-yahoo-finance': self.backend.opencli_available,
            'opencli-iwc': self.backend.opencli_available,
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
            'opencli_family': {
                'opencli-dc': self.provider_available.get('opencli-dc', False),
                'opencli-xq': self.provider_available.get('opencli-xq', False),
                'opencli-xueqiu': self.provider_available.get('opencli-xueqiu', False),
                'opencli-sinafinance': self.provider_available.get('opencli-sinafinance', False),
                'opencli-bloomberg': self.provider_available.get('opencli-bloomberg', False),
                'opencli-yahoo-finance': self.provider_available.get('opencli-yahoo-finance', False),
                'opencli-iwc': self.provider_available.get('opencli-iwc', False),
            },
            'akshare_available': self.akshare_available,
            'adata_available': self.adata_available,
            'baostock_available': self.baostock_available,
            'priority': self.priority,
            'providers': [provider.name for provider in self.providers],
        }

    def _placeholder(self, capability: str, symbol: str | None, note: str, fallback_path: list[str]) -> dict[str, Any]:
        return wrap_placeholder_payload(
            capability=capability.removeprefix('get_'),
            symbol=symbol,
            note=note,
            fallback_path=fallback_path,
        )

    def _cache_get(self, key: str, ttl_seconds: int) -> Any:
        if not self.cache_enabled:
            return None
        return self.cache_reader(key, ttl_seconds=ttl_seconds)

    def _cache_set(self, key: str, data: Any) -> None:
        if not self.cache_enabled:
            return
        self.cache_writer(key, data)

    def _providers_for(self, capability: str, first_arg: Any = None) -> list[StockDataProvider]:
        preferred_groups = preferred_provider_groups(capability, first_arg)
        return reorder_provider_sequence(self.providers, preferred_groups)

    def _dispatch(self, capability: str, *args: Any) -> dict[str, Any]:
        spec = get_capability_spec(capability)
        first_arg = args[0] if args else None
        routing_hint = capability_routing_hint(capability, first_arg)
        providers = self._providers_for(capability, first_arg)
        return self.router.dispatch(capability, *args, spec=spec, providers=providers, routing_hint=routing_hint)

    def _dispatch_with_cache(self, cache_key: str, ttl_seconds: int, capability: str, *args: Any) -> dict[str, Any]:
        cached = self._cache_get(cache_key, ttl_seconds=ttl_seconds)
        if cached is not None:
            return cached
        data = self._dispatch(capability, *args)
        self._cache_set(cache_key, data)
        return data

    def get_search(self, query: str) -> dict[str, Any]:
        return self._dispatch_with_cache(f'search_{query}', CACHE_TTLS['search'], 'get_search', query)

    def get_quote(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        return self._dispatch_with_cache(f'quote_{normalized}', CACHE_TTLS['quote'], 'get_quote', normalized)

    def get_snapshot(self, symbol: str) -> dict[str, Any]:
        return self.get_quote(symbol)

    def get_kline(self, symbol: str, days: int = 120) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        return self._dispatch_with_cache(f'kline_{normalized}_{days}', CACHE_TTLS['kline'], 'get_kline', normalized, days)

    def get_intraday(self, symbol: str) -> dict[str, Any]:
        return self.get_quote(symbol)

    def get_money_flow(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        return self._dispatch_with_cache(f'flow_{normalized}', CACHE_TTLS['money_flow'], 'get_money_flow', normalized)

    def get_north_flow(self) -> dict[str, Any]:
        return self._dispatch_with_cache('north_flow', CACHE_TTLS['north_flow'], 'get_north_flow')

    def get_sector_money_flow(self) -> dict[str, Any]:
        return self._dispatch_with_cache('sector_flow', CACHE_TTLS['sector_flow'], 'get_sector_money_flow')

    def get_financial(self, symbol: str) -> dict[str, Any]:
        return self._dispatch('get_financial', normalize_symbol(symbol))

    def get_report(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch('get_report', normalized)
        if data.get('status') == 'empty':
            return self._placeholder('get_report', normalized, '财报摘要未命中可用数据源', data.get('fallback_path', []))
        return data

    def get_income_statement(self, symbol: str, period: str = 'yearly') -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch_with_cache(f'income_{normalized}_{period}', CACHE_TTLS['statement'], 'get_income_statement', normalized, period)
        if data.get('status') == 'empty':
            return self._placeholder('get_income_statement', normalized, '利润表暂未命中可用数据源', data.get('fallback_path', []))
        return data

    def get_balance_sheet(self, symbol: str, period: str = 'yearly') -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch_with_cache(f'balance_{normalized}_{period}', CACHE_TTLS['statement'], 'get_balance_sheet', normalized, period)
        if data.get('status') == 'empty':
            return self._placeholder('get_balance_sheet', normalized, '资产负债表暂未命中可用数据源', data.get('fallback_path', []))
        return data

    def get_cash_flow(self, symbol: str, period: str = 'yearly') -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch_with_cache(f'cash_{normalized}_{period}', CACHE_TTLS['statement'], 'get_cash_flow', normalized, period)
        if data.get('status') == 'empty':
            return self._placeholder('get_cash_flow', normalized, '现金流量表暂未命中可用数据源', data.get('fallback_path', []))
        return data

    def get_announcements(self, symbol: str, days: int = 180) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch_with_cache(f'announcements_{normalized}_{days}', CACHE_TTLS['event'], 'get_announcements', normalized, days)
        if data.get('status') != 'empty':
            return data
        return self._placeholder('get_announcements', normalized, '公告真实源尚未接通或未命中数据。', data.get('fallback_path', []))

    def get_main_holders(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch_with_cache(f'holders_{normalized}', CACHE_TTLS['holder'], 'get_main_holders', normalized)
        if data.get('status') != 'empty':
            return data
        return self._placeholder('get_main_holders', normalized, '主要股东数据暂未命中可用数据源。', data.get('fallback_path', []))

    def get_shareholder_changes(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch_with_cache(f'shareholder_changes_{normalized}', CACHE_TTLS['event'], 'get_shareholder_changes', normalized)
        if data.get('status') != 'empty':
            return data
        return self._placeholder('get_shareholder_changes', normalized, '股东变动数据暂未命中可用数据源。', data.get('fallback_path', []))

    def get_dividend(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        data = self._dispatch_with_cache(f'dividend_{normalized}', CACHE_TTLS['holder'], 'get_dividend', normalized)
        if data.get('status') != 'empty':
            return data
        return self._placeholder('get_dividend', normalized, '历史分红数据暂未命中可用数据源。', data.get('fallback_path', []))

    def get_sector_list(self) -> dict[str, Any]:
        return self._dispatch('get_sector_list')

    def get_sector_members(self, sector_code: str) -> dict[str, Any]:
        return self._dispatch('get_sector_members', sector_code)

    def get_limit_up(self, date: str | None = None) -> dict[str, Any]:
        cache_key = f'limit_up_{date or "latest"}'
        return self._dispatch_with_cache(cache_key, CACHE_TTLS['limit_pool'], 'get_limit_up', date)

    def get_limit_down(self, date: str | None = None) -> dict[str, Any]:
        cache_key = f'limit_down_{date or "latest"}'
        return self._dispatch_with_cache(cache_key, CACHE_TTLS['limit_pool'], 'get_limit_down', date)

    def get_news(self, symbol: str | None = None) -> dict[str, Any]:
        data = self._dispatch('get_news', symbol)
        if data.get('status') != 'empty':
            return data
        return self._placeholder('get_news', symbol, '消息面真实源尚未接通；当前不伪造新闻数据。', data.get('fallback_path', []))

    def get_research(self, symbol: str) -> dict[str, Any]:
        data = self._dispatch('get_research', symbol)
        if data.get('status') != 'empty':
            return data
        return self._placeholder('get_research', symbol, '研报真实源尚未接通；当前不伪造研报数据。', data.get('fallback_path', []))

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
            'announcements': self.get_announcements(normalized, days=180),
            'news': self.get_news(normalized),
            'research': self.get_research(normalized),
        }

    def get_market_bundle(self, *, date: str | None = None) -> dict[str, Any]:
        return {
            'date': date,
            'north_flow': self.get_north_flow(),
            'sector_flow': self.get_sector_money_flow(),
            'limit_up': self.get_limit_up(date),
            'limit_down': self.get_limit_down(date),
        }
