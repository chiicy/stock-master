#!/usr/bin/env python3
from __future__ import annotations

import json

from stock_master.common.symbols import code_only

from ..interface import ProviderPayload, ProviderResult
from .base import ModuleProvider, run_worker_cli, secucode


class AdataProvider(ModuleProvider):
    module_name = 'stock_master.datasource.providers.adata'

    def __init__(self, backend, available: bool) -> None:
        super().__init__('adata', backend, available)

    def get_search(self, query: str) -> ProviderResult:
        return self._run_action('get_search', query=query)

    def get_quote(self, symbol: str) -> ProviderResult:
        return self._run_action('get_quote', symbol=code_only(symbol))

    def get_kline(self, symbol: str, days: int = 120) -> ProviderResult:
        return self._run_action('get_kline', symbol=code_only(symbol), days=days)

    def get_money_flow(self, symbol: str) -> ProviderResult:
        return self._run_action('get_money_flow', symbol=code_only(symbol))

    def get_financial(self, symbol: str) -> ProviderResult:
        return self._run_action('get_financial', symbol=secucode(symbol))


def get_search(query: str) -> ProviderPayload:
    import adata

    out: ProviderPayload = {'query': query}
    df = adata.stock.info.all_code()
    query_lower = str(query).lower()
    mask = df['stock_code'].astype(str).str.contains(query_lower, case=False, regex=False)
    mask = mask | df['short_name'].astype(str).str.contains(query_lower, case=False, regex=False)
    hit = df[mask].head(20).copy()
    if hit.empty:
        return {'error': 'empty'}
    hit['代码'] = hit['stock_code']
    hit['名称'] = hit['short_name']
    hit['市场'] = hit['exchange']
    out['items'] = json.loads(hit[['代码', '名称', '市场', 'list_date']].to_json(orient='records', force_ascii=False))
    return out


def get_quote(symbol: str) -> ProviderPayload:
    import adata

    out: ProviderPayload = {'symbol': symbol}
    df = adata.stock.market.get_market_bar(stock_code=symbol)
    if df is None or df.empty:
        return {'error': 'empty'}
    last = df.iloc[-1].to_dict()
    out.update(
        {
            '代码': symbol,
            '最新价': last.get('price'),
            '现价': last.get('price'),
            '成交量': last.get('volume'),
            '时间': last.get('trade_time'),
            'price': last.get('price'),
            'current': last.get('price'),
            'volume': last.get('volume'),
            'trade_time': last.get('trade_time'),
            'bs_type': last.get('bs_type'),
            'raw': last,
        }
    )
    return out


def get_kline(symbol: str, days: int) -> ProviderPayload:
    import adata
    from datetime import date, timedelta

    start = (date.today() - timedelta(days=max(days * 2, 90))).isoformat()
    end = date.today().isoformat()
    df = adata.stock.market.get_market(stock_code=symbol, start_date=start, end_date=end)
    if df is None or df.empty:
        return {'error': 'empty'}
    df = df.tail(days).copy()
    df['日期'] = df['trade_date']
    df['股票代码'] = df['stock_code']
    df['开盘'] = df['open']
    df['收盘'] = df['close']
    df['最高'] = df['high']
    df['最低'] = df['low']
    df['成交量'] = df['volume']
    df['成交额'] = df['amount']
    df['涨跌幅'] = df['change_pct']
    df['涨跌额'] = df['change']
    df['换手率'] = df['turnover_ratio']
    return {
        'symbol': symbol,
        'items': json.loads(
            df[
                [
                    '日期',
                    '股票代码',
                    '开盘',
                    '收盘',
                    '最高',
                    '最低',
                    '成交量',
                    '成交额',
                    '涨跌幅',
                    '涨跌额',
                    '换手率',
                    'trade_date',
                    'open',
                    'close',
                    'high',
                    'low',
                    'volume',
                    'amount',
                    'change_pct',
                    'change',
                    'turnover_ratio',
                ]
            ].to_json(orient='records', force_ascii=False)
        ),
    }


def get_money_flow(symbol: str) -> ProviderPayload:
    import adata

    df = adata.stock.market.get_capital_flow(stock_code=symbol)
    if df is None or df.empty:
        return {'error': 'empty'}
    df = df.tail(20).copy()
    df['日期'] = df['trade_date']
    df['主力净流入-净额'] = df['main_net_inflow']
    df['超大单净流入-净额'] = df['max_net_inflow']
    df['大单净流入-净额'] = df['lg_net_inflow']
    df['中单净流入-净额'] = df['mid_net_inflow']
    df['小单净流入-净额'] = df['sm_net_inflow']
    latest = df.iloc[-1].to_dict()
    return {
        'symbol': symbol,
        'items': json.loads(df.to_json(orient='records', force_ascii=False)),
        'latest': latest,
        'mainNetInflow': latest.get('main_net_inflow'),
        'superLargeNetInflow': latest.get('max_net_inflow'),
        'smallNetInflow': latest.get('sm_net_inflow'),
    }


def get_financial(symbol: str) -> ProviderPayload:
    import adata

    df = adata.stock.finance.get_core_index(stock_code=symbol)
    if df is None or df.empty:
        return {'error': 'empty'}
    return {
        'symbol': symbol,
        'status': 'ok',
        'rows': json.loads(df.tail(8).to_json(orient='records', force_ascii=False)),
    }


if __name__ == '__main__':
    raise SystemExit(
        run_worker_cli(
            {
                'get_search': get_search,
                'get_quote': get_quote,
                'get_kline': get_kline,
                'get_money_flow': get_money_flow,
                'get_financial': get_financial,
            }
        )
    )
