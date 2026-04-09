#!/usr/bin/env python3
from __future__ import annotations

from typing import Callable, Iterable

from stock_master.datasource.backend import CommandBackend
from stock_master.datasource.interface import StockDataProvider

from .adata import AdataProvider
from .akshare import AkshareProvider
from .baostock import BaoStockProvider
from .opencli import (
    OPENCLI_PROVIDER_NAMES,
    OpenCliBloombergProvider,
    OpenCliDcProvider,
    OpenCliIwcProvider,
    OpenCliProvider,
    OpenCliSinaFinanceProvider,
    OpenCliXqProvider,
    OpenCliXueqiuProvider,
    OpenCliYahooFinanceProvider,
)

__all__ = [
    'build_provider_map',
    'order_providers',
    'reorder_provider_sequence',
]

ProviderFactory = Callable[[CommandBackend, bool], StockDataProvider]


def build_provider_map(backend: CommandBackend, availability: dict[str, bool]) -> dict[str, StockDataProvider]:
    provider_factories: dict[str, ProviderFactory] = {
        'akshare': AkshareProvider,
        'adata': AdataProvider,
        'baostock': BaoStockProvider,
        'opencli-dc': OpenCliDcProvider,
        'opencli-xq': OpenCliXqProvider,
        'opencli-xueqiu': OpenCliXueqiuProvider,
        'opencli-sinafinance': OpenCliSinaFinanceProvider,
        'opencli-bloomberg': OpenCliBloombergProvider,
        'opencli-yahoo-finance': OpenCliYahooFinanceProvider,
        'opencli-iwc': OpenCliIwcProvider,
        'opencli': OpenCliProvider,
    }
    return {
        name: factory(backend, availability.get(name, availability.get('opencli', False) if name in OPENCLI_PROVIDER_NAMES else False))
        for name, factory in provider_factories.items()
    }


def order_providers(provider_map: dict[str, StockDataProvider], priority: list[str]) -> list[StockDataProvider]:
    return [provider_map[name] for name in priority if name in provider_map]


def reorder_provider_sequence(
    providers: Iterable[StockDataProvider],
    preferred_groups: list[list[str]] | None = None,
) -> list[StockDataProvider]:
    provider_list = list(providers)
    if not preferred_groups:
        return provider_list

    grouped_names = {name for group in preferred_groups for name in group}
    provider_by_name = {provider.name: provider for provider in provider_list}
    ordered: list[StockDataProvider] = []
    seen: set[str] = set()

    for group in preferred_groups:
        for name in group:
            provider = provider_by_name.get(name)
            if provider is None or name in seen:
                continue
            ordered.append(provider)
            seen.add(name)

    for provider in provider_list:
        if provider.name in seen:
            continue
        if provider.name in grouped_names:
            continue
        ordered.append(provider)
        seen.add(provider.name)

    for provider in provider_list:
        if provider.name in seen:
            continue
        ordered.append(provider)
        seen.add(provider.name)

    return ordered
