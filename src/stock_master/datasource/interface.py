#!/usr/bin/env python3
from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Any, Callable, Literal, TypeAlias

SufficientFieldGroup: TypeAlias = tuple[str, ...]
SufficientFields: TypeAlias = tuple[SufficientFieldGroup, ...]

ProviderPayload: TypeAlias = dict[str, Any]
ProviderResult: TypeAlias = ProviderPayload | Literal[False]
DispatchStrategy: TypeAlias = Literal['first_success', 'aggregate']


@dataclass(frozen=True)
class CapabilitySpec:
    strategy: DispatchStrategy = 'first_success'
    merge_keys: tuple[str, ...] = ()
    dedupe_by: str | None = None
    sort_by: str | None = None
    sufficient_fields: SufficientFields = ()


DEFAULT_CAPABILITY_SPEC = CapabilitySpec()


def capability(
    *,
    strategy: DispatchStrategy = 'first_success',
    merge_keys: tuple[str, ...] = (),
    dedupe_by: str | None = None,
    sort_by: str | None = None,
    sufficient_fields: SufficientFields = (),
) -> Callable[[Callable[..., ProviderResult]], Callable[..., ProviderResult]]:
    def decorator(func: Callable[..., ProviderResult]) -> Callable[..., ProviderResult]:
        setattr(
            func,
            '__capability_spec__',
            CapabilitySpec(
                strategy=strategy,
                merge_keys=merge_keys,
                dedupe_by=dedupe_by,
                sort_by=sort_by,
                sufficient_fields=sufficient_fields,
            ),
        )
        return func

    return decorator


def get_capability_spec(capability_name: str) -> CapabilitySpec:
    method = getattr(StockDataProvider, capability_name, None)
    if method is None:
        return DEFAULT_CAPABILITY_SPEC
    return getattr(method, '__capability_spec__', DEFAULT_CAPABILITY_SPEC)


class StockDataProvider(ABC):
    """Provider contract for stock-master datasource backends.

    All provider methods must follow the same rule:
    - success: return the shared datasource envelope defined in
      ``stock_master.datasource.schema``. The payload keeps stable common
      fields for analysis and may attach provider-specific extras via
      ``extensions`` / ``raw``.
    - unsupported / empty / exception / timeout: return False
    """

    name: str
    available: bool

    @capability(sufficient_fields=(('items', 'rows'),))
    def get_search(self, query: str) -> ProviderResult:
        return False

    @capability(sufficient_fields=(('price', 'close', 'current', 'current_price', 'trade', 'last_price', 'latestPrice', 'regularMarketPrice'),))
    def get_quote(self, symbol: str) -> ProviderResult:
        return False

    @capability(sufficient_fields=(('price', 'close', 'current', 'current_price', 'trade', 'last_price', 'latestPrice', 'regularMarketPrice'),))
    def get_snapshot(self, symbol: str) -> ProviderResult:
        return self.get_quote(symbol)

    @capability()
    def get_kline(self, symbol: str, days: int = 120) -> ProviderResult:
        return False

    @capability()
    def get_intraday(self, symbol: str) -> ProviderResult:
        return self.get_quote(symbol)

    @capability()
    def get_money_flow(self, symbol: str) -> ProviderResult:
        return False

    @capability()
    def get_north_flow(self) -> ProviderResult:
        return False

    @capability()
    def get_sector_money_flow(self) -> ProviderResult:
        return False

    @capability()
    def get_financial(self, symbol: str) -> ProviderResult:
        return False

    @capability()
    def get_report(self, symbol: str) -> ProviderResult:
        return False

    @capability()
    def get_income_statement(self, symbol: str, period: str = 'yearly') -> ProviderResult:
        return False

    @capability()
    def get_balance_sheet(self, symbol: str, period: str = 'yearly') -> ProviderResult:
        return False

    @capability()
    def get_cash_flow(self, symbol: str, period: str = 'yearly') -> ProviderResult:
        return False

    @capability(strategy='aggregate', merge_keys=('items', 'rows'), dedupe_by='record_identity', sort_by='date_desc')
    def get_announcements(self, symbol: str, days: int = 180) -> ProviderResult:
        return False

    @capability()
    def get_main_holders(self, symbol: str) -> ProviderResult:
        return False

    @capability()
    def get_shareholder_changes(self, symbol: str) -> ProviderResult:
        return False

    @capability()
    def get_dividend(self, symbol: str) -> ProviderResult:
        return False

    @capability()
    def get_sector_list(self) -> ProviderResult:
        return False

    @capability()
    def get_sector_members(self, sector_code: str) -> ProviderResult:
        return False

    @capability()
    def get_limit_up(self, date: str | None = None) -> ProviderResult:
        return False

    @capability()
    def get_limit_down(self, date: str | None = None) -> ProviderResult:
        return False

    @capability(strategy='aggregate', merge_keys=('items', 'rows'), dedupe_by='record_identity', sort_by='date_desc')
    def get_news(self, symbol: str | None = None) -> ProviderResult:
        return False

    @capability(strategy='aggregate', merge_keys=('items', 'rows'), dedupe_by='record_identity', sort_by='date_desc')
    def get_research(self, symbol: str) -> ProviderResult:
        return False
