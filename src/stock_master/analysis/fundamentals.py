#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


def safe_div(a: float | int | None, b: float | int | None) -> float | None:
    if a is None or b in (None, 0):
        return None
    return float(a) / float(b)


def calc_roe(net_income: float, equity: float) -> float | None:
    return safe_div(net_income, equity)


def calc_roic(nopat: float, invested_capital: float) -> float | None:
    return safe_div(nopat, invested_capital)


def calc_margin(numerator: float | int | None, revenue: float | int | None) -> float | None:
    return safe_div(numerator, revenue)


def calc_turnover(revenue_or_cost: float | int | None, average_balance: float | int | None) -> float | None:
    return safe_div(revenue_or_cost, average_balance)


def calc_days_sales_outstanding(revenue: float | int | None, average_receivables: float | int | None) -> float | None:
    turnover = calc_turnover(revenue, average_receivables)
    return safe_div(365, turnover)


def calc_days_inventory_outstanding(cost: float | int | None, average_inventory: float | int | None) -> float | None:
    turnover = calc_turnover(cost, average_inventory)
    return safe_div(365, turnover)


def calc_cash_conversion_ratio(cfo: float | int | None, net_income: float | int | None) -> float | None:
    return safe_div(cfo, net_income)


def calc_free_cash_flow(cfo: float | int | None, capex: float | int | None) -> float | None:
    if cfo is None or capex is None:
        return None
    return float(cfo) - float(capex)


def calc_net_debt(total_debt: float | int | None, cash: float | int | None) -> float | None:
    if total_debt is None or cash is None:
        return None
    return float(total_debt) - float(cash)


def calc_net_debt_ratio(total_debt: float | int | None, cash: float | int | None, equity: float | int | None) -> float | None:
    net_debt = calc_net_debt(total_debt, cash)
    return safe_div(net_debt, equity)


def calc_nopat(ebit: float | int | None, tax_rate: float | int | None) -> float | None:
    if ebit is None or tax_rate is None:
        return None
    return float(ebit) * (1 - float(tax_rate))


def calc_asset_turnover(revenue: float | int | None, average_assets: float | int | None) -> float | None:
    return calc_turnover(revenue, average_assets)


def calc_equity_multiplier(average_assets: float | int | None, average_equity: float | int | None) -> float | None:
    return safe_div(average_assets, average_equity)


def calc_cagr(values: list[float], years: int | None = None) -> float | None:
    if not values or len(values) < 2:
        return None
    start, end = values[0], values[-1]
    if start <= 0 or end <= 0:
        return None
    periods = years or (len(values) - 1)
    if periods <= 0:
        return None
    return (end / start) ** (1 / periods) - 1


def calc_dcf(cash_flows: list[float], discount_rate: float) -> float | None:
    if not cash_flows:
        return None
    total = 0.0
    for period, cash_flow in enumerate(cash_flows, start=1):
        total += cash_flow / ((1 + discount_rate) ** period)
    return total


def calc_peg(pe: float, growth_rate: float) -> float | None:
    if growth_rate in (None, 0):
        return None
    return pe / (growth_rate * 100)


def analyze_dupont(
    roe: float | None,
    net_margin: float | None = None,
    asset_turnover: float | None = None,
    leverage: float | None = None,
) -> dict[str, Any]:
    return {
        'roe': roe,
        'net_margin': net_margin,
        'asset_turnover': asset_turnover,
        'leverage': leverage,
        'complete': all(value is not None for value in [roe, net_margin, asset_turnover, leverage]),
    }


def build_detective_readiness(checks: dict[str, bool]) -> dict[str, Any]:
    ready = [name for name, status in checks.items() if status]
    missing = [name for name, status in checks.items() if not status]
    ratio = safe_div(len(ready), len(checks)) or 0.0
    if ratio >= 0.8:
        label = '较完整'
    elif ratio >= 0.5:
        label = '部分完整'
    else:
        label = '明显不足'
    return {
        'label': label,
        'ready_items': ready,
        'missing_items': missing,
        'ready_ratio': ratio,
    }
