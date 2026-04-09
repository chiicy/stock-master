#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import date, timedelta

from stock_master.common.symbols import code_only, normalize_symbol

from ..interface import ProviderPayload, ProviderResult
from .base import ModuleProvider, run_worker_cli


class AkshareProvider(ModuleProvider):
    module_name = 'stock_master.datasource.providers.akshare'

    def __init__(self, backend, available: bool) -> None:
        super().__init__('akshare', backend, available)

    def get_quote(self, symbol: str) -> ProviderResult:
        return self._run_action('get_quote', symbol=normalize_symbol(symbol))

    def get_kline(self, symbol: str, days: int = 120) -> ProviderResult:
        return self._run_action('get_kline', symbol=code_only(symbol), days=days)

    def get_money_flow(self, symbol: str) -> ProviderResult:
        normalized = normalize_symbol(symbol)
        market = 'sh' if normalized.startswith('SH') else 'sz'
        return self._run_action('get_money_flow', symbol=code_only(normalized), market=market)

    def get_north_flow(self) -> ProviderResult:
        return self._run_action('get_north_flow')

    def get_sector_money_flow(self) -> ProviderResult:
        return self._run_action('get_sector_money_flow')

    def get_financial(self, symbol: str) -> ProviderResult:
        return self._run_action('get_financial', symbol=code_only(symbol))

    def get_report(self, symbol: str) -> ProviderResult:
        return self._run_action('get_report', symbol=code_only(symbol), timeout=180)

    def get_income_statement(self, symbol: str, period: str = 'yearly') -> ProviderResult:
        return self._run_action('get_income_statement', symbol=normalize_symbol(symbol), period=period, timeout=180)

    def get_balance_sheet(self, symbol: str, period: str = 'yearly') -> ProviderResult:
        return self._run_action('get_balance_sheet', symbol=normalize_symbol(symbol), period=period, timeout=180)

    def get_cash_flow(self, symbol: str, period: str = 'yearly') -> ProviderResult:
        return self._run_action('get_cash_flow', symbol=normalize_symbol(symbol), period=period, timeout=180)

    def get_announcements(self, symbol: str, days: int = 180) -> ProviderResult:
        return self._run_action('get_announcements', symbol=code_only(symbol), days=days, timeout=180)

    def get_news(self, symbol: str | None = None) -> ProviderResult:
        if not symbol:
            return False
        return self._run_action('get_news', symbol=code_only(symbol), timeout=180)

    def get_research(self, symbol: str) -> ProviderResult:
        return self._run_action('get_research', symbol=code_only(symbol), timeout=180)

    def get_main_holders(self, symbol: str) -> ProviderResult:
        return self._run_action('get_main_holders', symbol=code_only(symbol), timeout=180)

    def get_shareholder_changes(self, symbol: str) -> ProviderResult:
        return self._run_action('get_shareholder_changes', symbol=code_only(symbol), timeout=180)

    def get_dividend(self, symbol: str) -> ProviderResult:
        return self._run_action('get_dividend', symbol=code_only(symbol), timeout=180)


def get_quote(symbol: str) -> ProviderPayload:
    import akshare as ak

    out: ProviderPayload = {'symbol': symbol}
    df = ak.stock_individual_spot_xq(symbol=symbol)
    pairs = {str(row['item']): row['value'] for _, row in df.iterrows()}
    out.update(
        {
            '代码': pairs.get('代码', symbol),
            '名称': pairs.get('名称'),
            '最新价': pairs.get('现价'),
            '现价': pairs.get('现价'),
            '涨跌幅': pairs.get('涨幅'),
            '涨跌额': pairs.get('涨跌'),
            '今开': pairs.get('今开'),
            '最高': pairs.get('最高'),
            '最低': pairs.get('最低'),
            '昨收': pairs.get('昨收'),
            '成交量': pairs.get('成交量'),
            '成交额': pairs.get('成交额'),
            '换手率': pairs.get('周转率'),
            '市盈率(TTM)': pairs.get('市盈率(TTM)'),
            '市净率': pairs.get('市净率'),
            '总市值': pairs.get('资产净值/总市值') or pairs.get('总市值'),
            '时间': pairs.get('时间'),
            'price': pairs.get('现价'),
            'current': pairs.get('现价'),
            'percent': pairs.get('涨幅'),
            'change': pairs.get('涨跌'),
            'open': pairs.get('今开'),
            'high': pairs.get('最高'),
            'low': pairs.get('最低'),
            'preClose': pairs.get('昨收'),
            'volume': pairs.get('成交量'),
            'amount': pairs.get('成交额'),
            'turnoverRate': pairs.get('周转率'),
            'pe_ttm': pairs.get('市盈率(TTM)'),
            'pb': pairs.get('市净率'),
            'marketValue': pairs.get('资产净值/总市值') or pairs.get('总市值'),
            'raw': pairs,
        }
    )
    return out


def get_kline(symbol: str, days: int) -> ProviderPayload:
    import akshare as ak
    from datetime import date, timedelta

    start = (date.today() - timedelta(days=max(days * 2, 90))).strftime('%Y%m%d')
    end = date.today().strftime('%Y%m%d')
    df = ak.stock_zh_a_hist(symbol=symbol, start_date=start, end_date=end, adjust='')
    if df is None or df.empty:
        return {'error': 'empty'}
    return {
        'symbol': symbol,
        'items': json.loads(df.tail(days).to_json(orient='records', force_ascii=False)),
    }


def get_money_flow(symbol: str, market: str) -> ProviderPayload:
    import akshare as ak

    df = ak.stock_individual_fund_flow(stock=symbol, market=market)
    if df is None or df.empty:
        return {'error': 'empty'}
    df = df.tail(20).copy()
    latest = df.iloc[-1].to_dict()
    return {
        'symbol': symbol,
        'items': json.loads(df.to_json(orient='records', force_ascii=False)),
        'latest': latest,
        'mainNetInflow': latest.get('主力净流入-净额'),
        'superLargeNetInflow': latest.get('超大单净流入-净额'),
        'smallNetInflow': latest.get('小单净流入-净额'),
    }


def get_north_flow() -> ProviderPayload:
    import akshare as ak

    df = ak.stock_hsgt_fund_flow_summary_em()
    if df is None or df.empty:
        return {'error': 'empty'}
    return {'items': json.loads(df.head(20).to_json(orient='records', force_ascii=False))}


def get_sector_money_flow() -> ProviderPayload:
    import akshare as ak

    df = ak.stock_sector_fund_flow_rank(indicator='今日', sector_type='行业资金流')
    if df is None or df.empty:
        return {'error': 'empty'}
    return {'items': json.loads(df.head(30).to_json(orient='records', force_ascii=False))}


def get_financial(symbol: str) -> ProviderPayload:
    import akshare as ak

    df = ak.stock_financial_analysis_indicator(symbol=symbol)
    return {
        'symbol': symbol,
        'status': 'ok',
        'rows': json.loads(df.tail(8).to_json(orient='records', force_ascii=False)),
    }


def get_report(symbol: str) -> ProviderPayload:
    import akshare as ak

    tries: list[str] = []
    for name, expr in (
        ('stock_yjbb_em', lambda: ak.stock_yjbb_em(symbol='全部')),
        ('stock_yjyg_em', lambda: ak.stock_yjyg_em(symbol='全部')),
    ):
        try:
            df = expr()
            if '股票代码' not in df.columns:
                tries.append(f'{name}:miss')
                continue
            hit = df[df['股票代码'].astype(str) == symbol]
            if not hit.empty:
                return {
                    'symbol': symbol,
                    'status': 'ok',
                    'source_detail': name,
                    'rows': json.loads(hit.head(3).to_json(orient='records', force_ascii=False)),
                }
            tries.append(f'{name}:miss')
        except Exception as exc:
            tries.append(f'{name}:{exc}')
    return {
        'symbol': symbol,
        'status': 'placeholder',
        'tries': tries,
        'note': '未命中财报摘要行',
    }


def _statement_rows(df, symbol: str, period: str) -> ProviderPayload:
    if df is None or df.empty:
        return {'status': 'empty', 'symbol': symbol}
    rows = json.loads(df.to_json(orient='records', force_ascii=False))
    return {
        'symbol': symbol,
        'status': 'ok',
        'period': period,
        'rows': rows,
    }


def get_income_statement(symbol: str, period: str = 'yearly') -> ProviderPayload:
    import akshare as ak

    if period == 'report':
        df = ak.stock_profit_sheet_by_report_em(symbol=symbol)
    else:
        df = ak.stock_profit_sheet_by_yearly_em(symbol=symbol)
    return _statement_rows(df, symbol, period)


def get_balance_sheet(symbol: str, period: str = 'yearly') -> ProviderPayload:
    import akshare as ak

    if period == 'report':
        df = ak.stock_balance_sheet_by_report_em(symbol=symbol)
    else:
        df = ak.stock_balance_sheet_by_yearly_em(symbol=symbol)
    return _statement_rows(df, symbol, period)


def get_cash_flow(symbol: str, period: str = 'yearly') -> ProviderPayload:
    import akshare as ak

    if period == 'report':
        df = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)
    else:
        df = ak.stock_cash_flow_sheet_by_yearly_em(symbol=symbol)
    return _statement_rows(df, symbol, period)


def get_announcements(symbol: str, days: int = 180) -> ProviderPayload:
    import akshare as ak

    end = date.today()
    start = end - timedelta(days=max(days, 30))
    df = ak.stock_zh_a_disclosure_report_cninfo(
        symbol=symbol,
        start_date=start.strftime('%Y%m%d'),
        end_date=end.strftime('%Y%m%d'),
    )
    if df is None or df.empty:
        return {'status': 'empty', 'symbol': symbol}
    return {
        'symbol': symbol,
        'status': 'ok',
        'items': json.loads(df.head(100).to_json(orient='records', force_ascii=False)),
    }


def get_news(symbol: str) -> ProviderPayload:
    import akshare as ak

    df = ak.stock_news_em(symbol=symbol)
    if df is None or df.empty:
        return {'status': 'empty', 'symbol': symbol}
    return {
        'symbol': symbol,
        'status': 'ok',
        'items': json.loads(df.head(100).to_json(orient='records', force_ascii=False)),
    }


def get_research(symbol: str) -> ProviderPayload:
    import akshare as ak

    df = ak.stock_research_report_em(symbol=symbol)
    if df is None or df.empty:
        return {'status': 'empty', 'symbol': symbol}
    return {
        'symbol': symbol,
        'status': 'ok',
        'items': json.loads(df.head(50).to_json(orient='records', force_ascii=False)),
    }


def get_main_holders(symbol: str) -> ProviderPayload:
    import akshare as ak

    df = ak.stock_main_stock_holder(stock=symbol)
    if df is None or df.empty:
        return {'status': 'empty', 'symbol': symbol}
    return {
        'symbol': symbol,
        'status': 'ok',
        'items': json.loads(df.head(50).to_json(orient='records', force_ascii=False)),
    }


def get_shareholder_changes(symbol: str) -> ProviderPayload:
    import akshare as ak

    df = ak.stock_shareholder_change_ths(symbol=symbol)
    if df is None or df.empty:
        return {'status': 'empty', 'symbol': symbol}
    return {
        'symbol': symbol,
        'status': 'ok',
        'items': json.loads(df.head(50).to_json(orient='records', force_ascii=False)),
    }


def get_dividend(symbol: str) -> ProviderPayload:
    import akshare as ak

    df = ak.stock_history_dividend_detail(symbol=symbol, indicator='分红')
    if df is None or df.empty:
        return {'status': 'empty', 'symbol': symbol}
    return {
        'symbol': symbol,
        'status': 'ok',
        'items': json.loads(df.head(50).to_json(orient='records', force_ascii=False)),
    }


if __name__ == '__main__':
    raise SystemExit(
        run_worker_cli(
            {
                'get_quote': get_quote,
                'get_kline': get_kline,
                'get_money_flow': get_money_flow,
                'get_north_flow': get_north_flow,
                'get_sector_money_flow': get_sector_money_flow,
                'get_financial': get_financial,
                'get_report': get_report,
                'get_income_statement': get_income_statement,
                'get_balance_sheet': get_balance_sheet,
                'get_cash_flow': get_cash_flow,
                'get_announcements': get_announcements,
                'get_news': get_news,
                'get_research': get_research,
                'get_main_holders': get_main_holders,
                'get_shareholder_changes': get_shareholder_changes,
                'get_dividend': get_dividend,
            }
        )
    )
