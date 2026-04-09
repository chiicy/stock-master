#!/usr/bin/env python3
from __future__ import annotations

from importlib import import_module
from typing import Callable

from ..backend import CommandBackend
from ..interface import StockDataProvider

__all__ = [
    'build_provider_map',
    'order_providers',
]

ProviderFactory = Callable[[CommandBackend, bool], StockDataProvider]


class MissingDependencyProvider(StockDataProvider):
    def __init__(self, name: str, missing_dependency: str) -> None:
        self.name = name
        self.available = False
        self.missing_dependency = missing_dependency


_PROVIDER_SPECS: dict[str, tuple[str, str]] = {
    'akshare': ('.akshare', 'AkshareProvider'),
    'adata': ('.adata', 'AdataProvider'),
    'baostock': ('.baostock', 'BaoStockProvider'),
    'opencli': ('.opencli', 'OpenCliProvider'),
}


def _load_provider_factory(module_name: str, class_name: str) -> ProviderFactory:
    module = import_module(module_name, package=__name__)
    provider_cls = getattr(module, class_name)
    return provider_cls


def build_provider_map(backend: CommandBackend, availability: dict[str, bool]) -> dict[str, StockDataProvider]:
    provider_map: dict[str, StockDataProvider] = {}
    for name, (module_name, class_name) in _PROVIDER_SPECS.items():
        is_available = availability.get(name, False)
        if not is_available:
            provider_map[name] = MissingDependencyProvider(name, name)
            continue
        try:
            provider_factory = _load_provider_factory(module_name, class_name)
        except ModuleNotFoundError as exc:
            provider_map[name] = MissingDependencyProvider(name, exc.name or name)
            continue
        provider_map[name] = provider_factory(backend, True)
    return provider_map


def order_providers(provider_map: dict[str, StockDataProvider], priority: list[str]) -> list[StockDataProvider]:
    return [provider_map[name] for name in priority if name in provider_map]
