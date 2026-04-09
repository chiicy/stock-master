#!/usr/bin/env python3
from __future__ import annotations

from abc import ABC
from typing import Any, Literal, TypeAlias

ProviderPayload: TypeAlias = dict[str, Any]
ProviderResult: TypeAlias = ProviderPayload | Literal[False]


class StockDataProvider(ABC):
    """Provider contract for stock-master datasource backends.

    All provider methods must follow the same rule:
    - success: return AkShare-style dict payload
    - unsupported / empty / exception / timeout: return False
    """

    name: str
    available: bool

    def get_search(self, query: str) -> ProviderResult:
        return False

    def get_quote(self, symbol: str) -> ProviderResult:
        return False

    def get_snapshot(self, symbol: str) -> ProviderResult:
        return self.get_quote(symbol)

    def get_kline(self, symbol: str, days: int = 120) -> ProviderResult:
        return False

    def get_intraday(self, symbol: str) -> ProviderResult:
        return self.get_quote(symbol)

    def get_money_flow(self, symbol: str) -> ProviderResult:
        return False

    def get_north_flow(self) -> ProviderResult:
        return False

    def get_sector_money_flow(self) -> ProviderResult:
        return False

    def get_financial(self, symbol: str) -> ProviderResult:
        return False

    def get_report(self, symbol: str) -> ProviderResult:
        return False

    def get_income_statement(self, symbol: str, period: str = 'yearly') -> ProviderResult:
        return False

    def get_balance_sheet(self, symbol: str, period: str = 'yearly') -> ProviderResult:
        return False

    def get_cash_flow(self, symbol: str, period: str = 'yearly') -> ProviderResult:
        return False

    def get_announcements(self, symbol: str, days: int = 180) -> ProviderResult:
        return False

    def get_main_holders(self, symbol: str) -> ProviderResult:
        return False

    def get_shareholder_changes(self, symbol: str) -> ProviderResult:
        return False

    def get_dividend(self, symbol: str) -> ProviderResult:
        return False

    def get_sector_list(self) -> ProviderResult:
        return False

    def get_sector_members(self, sector_code: str) -> ProviderResult:
        return False

    def get_limit_up(self, date: str | None = None) -> ProviderResult:
        return False

    def get_limit_down(self, date: str | None = None) -> ProviderResult:
        return False

    def get_news(self, symbol: str | None = None) -> ProviderResult:
        return False

    def get_research(self, symbol: str) -> ProviderResult:
        return False
