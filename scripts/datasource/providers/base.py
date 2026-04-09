#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from typing import Any, Callable

from stock_common.symbols import code_only, normalize_symbol

from ..backend import CommandBackend
from ..interface import ProviderPayload, ProviderResult, StockDataProvider


def market_prefix(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    if normalized.startswith('SH'):
        return 'sh'
    if normalized.startswith('SZ'):
        return 'sz'
    if normalized.startswith('BJ'):
        return 'bj'
    return ''


def secucode(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    code = code_only(normalized)
    if normalized.startswith('SH'):
        return f'{code}.SH'
    if normalized.startswith('SZ'):
        return f'{code}.SZ'
    if normalized.startswith('BJ'):
        return f'{code}.BJ'
    return code


def xt_symbol(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    market = normalized[:2]
    code = code_only(normalized)
    if market in {'SH', 'SZ', 'BJ'}:
        return f'{code}.{market}'
    return code


def baostock_symbol(symbol: str) -> str:
    code = code_only(symbol)
    market = market_prefix(symbol) or ('sh' if code.startswith(('6', '9')) else 'sz')
    return f'{market}.{code}'


class BaseProvider(StockDataProvider):
    def __init__(self, name: str, backend: CommandBackend, available: bool) -> None:
        self.name = name
        self.backend = backend
        self.available = available

    def _normalize_payload(self, data: Any) -> ProviderResult:
        if data in (None, False):
            return False
        if isinstance(data, list):
            if not data:
                return False
            return {'items': data}
        if not isinstance(data, dict):
            return False
        if data.get('error'):
            return False
        if data.get('status') in {'error', 'empty'}:
            return False
        if 'items' in data and data.get('items') == [] and data.get('status') not in {'ok', 'placeholder'}:
            return False
        if 'rows' in data and data.get('rows') == [] and data.get('status') not in {'ok', 'placeholder'}:
            return False
        meaningful = any(
            value not in (None, '', [], {})
            for key, value in data.items()
            if key not in {'symbol', 'query', 'source', 'source_detail', 'fallback_path'}
        )
        if not meaningful and data.get('status') not in {'ok', 'placeholder'}:
            return False
        return data

    def _date_window(self, days: int, minimum_days: int = 90) -> tuple[str, str]:
        start = (date.today() - timedelta(days=max(days * 2, minimum_days)))
        end = date.today()
        return start.isoformat(), end.isoformat()

    def _date_window_compact(self, days: int, minimum_days: int = 90) -> tuple[str, str]:
        start = (date.today() - timedelta(days=max(days * 2, minimum_days)))
        end = date.today()
        return start.strftime('%Y%m%d'), end.strftime('%Y%m%d')

    def _opencli_json(self, *parts: str, wrap_items: bool = False) -> ProviderResult:
        if not self.available:
            return False
        try:
            data = self.backend.opencli_json(*parts)
        except Exception:
            return False
        if wrap_items and isinstance(data, list):
            data = {'items': data}
        return self._normalize_payload(data)

    def _opencli_first(self, calls: list[tuple[str, ...]], *, wrap_items: bool = False) -> ProviderResult:
        for parts in calls:
            result = self._opencli_json(*parts, wrap_items=wrap_items)
            if result is not False:
                return result
        return False


class ModuleProvider(BaseProvider):
    module_name: str

    def _run_action(self, action: str, *, timeout: int = 90, **payload: Any) -> ProviderResult:
        if not self.available:
            return False
        try:
            data = self.backend.run_module_json(self.module_name, action, payload, timeout=timeout)
        except Exception:
            return False
        return self._normalize_payload(data)


def run_worker_cli(actions: dict[str, Callable[..., ProviderPayload]]) -> int:
    parser = argparse.ArgumentParser(description='Run stock-master provider worker action.')
    parser.add_argument('action')
    parser.add_argument('payload_json', nargs='?', default='{}')
    args = parser.parse_args()

    payload = json.loads(args.payload_json)
    action = actions.get(args.action)
    if action is None:
        print(json.dumps({'error': f'unknown action: {args.action}'}, ensure_ascii=False))
        return 1

    try:
        result = action(**payload)
    except Exception as exc:
        result = {'error': str(exc)}

    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0


if __name__ == '__main__':
    raise SystemExit(run_worker_cli({}))
