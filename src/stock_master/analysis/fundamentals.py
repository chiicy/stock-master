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
