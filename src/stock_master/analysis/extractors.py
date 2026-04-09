#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

ROW_CONTAINER_KEYS = ('data', 'items', 'rows', 'result', 'list')


def pick(payload: Any, *keys: str, default: Any = None) -> Any:
    if not isinstance(payload, dict):
        return default
    for key in keys:
        if key in payload and payload[key] not in (None, ''):
            return payload[key]
    return default


def extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ROW_CONTAINER_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def extract_closes_and_volumes(kline: Any) -> tuple[list[float], list[float], list[dict[str, Any]]]:
    rows = extract_rows(kline)
    closes: list[float] = []
    volumes: list[float] = []
    for row in rows:
        close = pick(row, 'close', '收盘', '最新价')
        volume = pick(row, 'volume', '成交量', 'vol')
        try:
            if close is not None:
                closes.append(float(close))
            if volume is not None:
                volumes.append(float(volume))
        except Exception:
            continue
    return closes, volumes, rows
