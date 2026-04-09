#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

CACHE_DIR = Path.home() / '.openclaw' / 'cache' / 'stock-master'
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: str | Path, default: Any = None) -> Any:
    target = Path(path)
    if not target.exists():
        return default
    return json.loads(target.read_text())


def write_json(path: str | Path, data: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def cache_get(key: str, ttl_seconds: int = 60, cache_dir: str | Path = CACHE_DIR) -> Any:
    path = Path(cache_dir) / f'{key}.json'
    if not path.exists():
        return None
    raw = read_json(path, default=None)
    if not raw:
        return None
    if time.time() - raw.get('_ts', 0) > ttl_seconds:
        return None
    return raw.get('data')


def cache_set(key: str, data: Any, cache_dir: str | Path = CACHE_DIR) -> None:
    write_json(Path(cache_dir) / f'{key}.json', {'_ts': time.time(), 'data': data})
