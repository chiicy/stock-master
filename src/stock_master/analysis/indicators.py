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


def calc_ema_last(values: list[float], period: int) -> float | None:
    if len(values) < period or period <= 0:
        return None
    series = ema(values, period)
    return series[-1] if series else None


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


def calc_adx(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    if period <= 0 or min(len(highs), len(lows), len(closes)) < period + 1:
        return None

    true_ranges: list[float] = []
    plus_dm_values: list[float] = []
    minus_dm_values: list[float] = []
    for index in range(1, len(closes)):
        high_diff = highs[index] - highs[index - 1]
        low_diff = lows[index - 1] - lows[index]
        plus_dm = high_diff if high_diff > low_diff and high_diff > 0 else 0.0
        minus_dm = low_diff if low_diff > high_diff and low_diff > 0 else 0.0
        true_range = max(
            highs[index] - lows[index],
            abs(highs[index] - closes[index - 1]),
            abs(lows[index] - closes[index - 1]),
        )
        true_ranges.append(true_range)
        plus_dm_values.append(plus_dm)
        minus_dm_values.append(minus_dm)

    if len(true_ranges) < period:
        return None

    dx_values: list[float] = []
    for start in range(0, len(true_ranges) - period + 1):
        tr_sum = sum(true_ranges[start:start + period])
        if tr_sum == 0:
            continue
        plus_di = 100 * sum(plus_dm_values[start:start + period]) / tr_sum
        minus_di = 100 * sum(minus_dm_values[start:start + period]) / tr_sum
        denominator = plus_di + minus_di
        if denominator == 0:
            continue
        dx_values.append(abs(plus_di - minus_di) / denominator * 100)
    if not dx_values:
        return None
    recent = dx_values[-period:]
    return sum(recent) / len(recent)


def find_support_resistance(prices: list[float]) -> dict[str, Any]:
    if len(prices) < 20:
        return {}
    recent = prices[-20:]
    return {'support': min(recent), 'resistance': max(recent), 'last': prices[-1]}
