#!/usr/bin/env python3
from __future__ import annotations

from stock_common.symbols import code_only

from ..interface import ProviderPayload, ProviderResult
from .base import ModuleProvider, baostock_symbol, run_worker_cli


class BaoStockProvider(ModuleProvider):
    module_name = 'datasource.providers.baostock'

    def __init__(self, backend, available: bool) -> None:
        super().__init__('baostock', backend, available)

    def get_search(self, query: str) -> ProviderResult:
        return self._run_action('get_search', query=query, timeout=120)

    def get_quote(self, symbol: str) -> ProviderResult:
        return self._run_action('get_quote', symbol=baostock_symbol(symbol), timeout=120)

    def get_kline(self, symbol: str, days: int = 120) -> ProviderResult:
        return self._run_action('get_kline', symbol=baostock_symbol(symbol), code=code_only(symbol), days=days, timeout=120)


def _with_session(fn):
    def wrapped(*args, **kwargs):
        import baostock as bs

        bs.login()
        try:
            return fn(bs, *args, **kwargs)
        finally:
            try:
                bs.logout()
            except Exception:
                pass

    return wrapped


@_with_session
def get_search(bs, query: str) -> ProviderPayload:
    rs = bs.query_all_stock(day='')
    rows = []
    while rs.error_code == '0' and rs.next():
        rows.append(rs.get_row_data())
    items = []
    query_lower = str(query).lower()
    for row in rows:
        code_value = row[0]
        if query_lower in code_value.lower():
            items.append({'代码': code_value.split('.')[-1], '名称': code_value, '市场': code_value.split('.')[0].upper()})
        if len(items) >= 20:
            break
    if not items:
        return {'error': 'empty'}
    return {'query': query, 'items': items}


@_with_session
def get_quote(bs, symbol: str) -> ProviderPayload:
    rs = bs.query_history_k_data_plus(
        symbol,
        'date,code,open,high,low,close,volume,amount,turn',
        start_date='',
        end_date='',
        frequency='d',
        adjustflag='3',
    )
    rows = []
    while rs.error_code == '0' and rs.next():
        rows.append(rs.get_row_data())
    if not rows:
        return {'error': 'empty'}
    row = rows[-1]
    return {
        'symbol': symbol,
        '日期': row[0],
        '代码': row[1],
        '开盘': row[2],
        '最高': row[3],
        '最低': row[4],
        '收盘': row[5],
        '成交量': row[6],
        '成交额': row[7],
        '换手率': row[8],
        'price': row[5],
        'current': row[5],
        'open': row[2],
        'high': row[3],
        'low': row[4],
        'volume': row[6],
        'amount': row[7],
        'turnoverRate': row[8],
    }


@_with_session
def get_kline(bs, symbol: str, code: str, days: int) -> ProviderPayload:
    from datetime import date, timedelta

    start = (date.today() - timedelta(days=max(days * 2, 90))).isoformat()
    end = date.today().isoformat()
    rs = bs.query_history_k_data_plus(
        symbol,
        'date,code,open,high,low,close,volume,amount,pctChg,turn',
        start_date=start,
        end_date=end,
        frequency='d',
        adjustflag='3',
    )
    rows = []
    while rs.error_code == '0' and rs.next():
        rows.append(rs.get_row_data())
    if not rows:
        return {'error': 'empty'}
    items = []
    for row in rows[-days:]:
        items.append(
            {
                '日期': row[0],
                '股票代码': code,
                '开盘': row[2],
                '最高': row[3],
                '最低': row[4],
                '收盘': row[5],
                '成交量': row[6],
                '成交额': row[7],
                '涨跌幅': row[8],
                '换手率': row[9],
                'date': row[0],
                'code': row[1],
                'open': row[2],
                'high': row[3],
                'low': row[4],
                'close': row[5],
                'volume': row[6],
                'amount': row[7],
                'pctChg': row[8],
                'turn': row[9],
            }
        )
    return {'symbol': symbol, 'items': items}


if __name__ == '__main__':
    raise SystemExit(
        run_worker_cli(
            {
                'get_search': get_search,
                'get_quote': get_quote,
                'get_kline': get_kline,
            }
        )
    )
