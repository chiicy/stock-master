#!/usr/bin/env python3
from __future__ import annotations

from statistics import mean, pstdev
from typing import Any


def calc_ma(prices: list[float], period: int) -> float | None:
    if len(prices) < period or period <= 0:
        return None
    return sum(prices[-period:]) / period


def calc_rsi(prices: list[float], period: int = 14) -> float | None:
    if len(prices) < period + 1:
        return None
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    recent = changes[-period:]
    gains = [value for value in recent if value > 0]
    losses = [-value for value in recent if value < 0]
    avg_gain = sum(gains) / period if gains else 0.0
    avg_loss = sum(losses) / period if losses else 0.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2 / (period + 1)
    output = [values[0]]
    for value in values[1:]:
        output.append(alpha * value + (1 - alpha) * output[-1])
    return output


def calc_macd(prices: list[float]) -> dict[str, Any]:
    if len(prices) < 35:
        return {}
    ema12 = ema(prices, 12)
    ema26 = ema(prices, 26)
    dif = [left - right for left, right in zip(ema12, ema26)]
    dea = ema(dif, 9)
    hist = [(left - right) * 2 for left, right in zip(dif, dea)]
    return {'dif': dif[-1], 'dea': dea[-1], 'hist': hist[-1]}


def calc_kdj(prices: list[float], period: int = 9) -> dict[str, Any]:
    if len(prices) < period:
        return {}
    window = prices[-period:]
    low_n = min(window)
    high_n = max(window)
    if high_n == low_n:
        rsv = 50.0
    else:
        rsv = (prices[-1] - low_n) / (high_n - low_n) * 100
    k_value = 2 / 3 * 50 + 1 / 3 * rsv
    d_value = 2 / 3 * 50 + 1 / 3 * k_value
    j_value = 3 * k_value - 2 * d_value
    return {'k': k_value, 'd': d_value, 'j': j_value}


def calc_boll(prices: list[float], period: int = 20) -> dict[str, Any]:
    if len(prices) < period:
        return {}
    window = prices[-period:]
    mid = mean(window)
    std = pstdev(window)
    return {
        'mid': mid,
        'upper': mid + 2 * std,
        'lower': mid - 2 * std,
        'bandwidth': (4 * std / mid) if mid else None,
    }


def calc_volume_ratio(volumes: list[float]) -> float | None:
    if len(volumes) < 20:
        return None
    avg5 = sum(volumes[-5:]) / 5
    avg20 = sum(volumes[-20:]) / 20
    if avg20 == 0:
        return None
    return avg5 / avg20


def find_support_resistance(prices: list[float]) -> dict[str, Any]:
    if len(prices) < 20:
        return {}
    recent = prices[-20:]
    return {'support': min(recent), 'resistance': max(recent), 'last': prices[-1]}
