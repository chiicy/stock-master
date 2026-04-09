#!/usr/bin/env python3
from __future__ import annotations

import threading
from typing import Any, Sequence

from .interface import ProviderPayload, ProviderResult, StockDataProvider


def is_provider_success(data: ProviderResult) -> bool:
    if data is False:
        return False
    if not isinstance(data, dict):
        return False
    if data.get('error'):
        return False
    if data.get('status') in {'error', 'empty'}:
        return False
    return True


def tag_payload(payload: ProviderPayload, source: str, fallback_path: list[str]) -> ProviderPayload:
    tagged = dict(payload)
    existing_source = tagged.get('source')
    if existing_source and existing_source != source:
        tagged.setdefault('source_detail', existing_source)
    tagged['source'] = source
    tagged['fallback_path'] = fallback_path
    return tagged


class ProviderRouter:
    def __init__(self, providers: Sequence[StockDataProvider], per_provider_timeout: float = 15) -> None:
        self.providers = list(providers)
        self.per_provider_timeout = per_provider_timeout

    def _invoke_with_timeout(self, provider: StockDataProvider, capability: str, *args: Any) -> ProviderResult:
        result: dict[str, Any] = {'value': False}

        def worker() -> None:
            try:
                handler = getattr(provider, capability)
                result['value'] = handler(*args)
            except Exception:
                result['value'] = False

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout=self.per_provider_timeout)
        if thread.is_alive():
            return False
        return result.get('value', False)

    def dispatch(self, capability: str, *args: Any) -> ProviderPayload:
        path: list[str] = []
        for provider in self.providers:
            if not provider.available:
                continue
            path.append(provider.name)
            value = self._invoke_with_timeout(provider, capability, *args)
            if is_provider_success(value):
                return tag_payload(value, provider.name, path.copy())
        return {
            'status': 'empty',
            'fallback_path': path,
        }
