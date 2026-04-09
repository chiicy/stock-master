from __future__ import annotations

from typing import Any

from stock_master.common.symbols import normalize_symbol, preferred_provider_groups

from ...interface import ProviderResult
from ...schema import ensure_payload_contract
from .base import OpenCliFamilyProvider
from .bloomberg import OpenCliBloombergProvider
from .dc import OpenCliDcProvider
from .iwc import OpenCliIwcProvider
from .sinafinance import OpenCliSinaFinanceProvider
from .xq import OpenCliXqProvider
from .xueqiu import OpenCliXueqiuProvider
from .yahoo_finance import OpenCliYahooFinanceProvider


class OpenCliProvider(OpenCliFamilyProvider):
    """Legacy composite provider kept for backwards-compatible direct imports/tests."""

    def __init__(self, backend, available: bool) -> None:
        super().__init__("opencli", backend, available)
        self._provider_map = {
            "dc": OpenCliDcProvider(backend, available),
            "xq": OpenCliXqProvider(backend, available),
            "xueqiu": OpenCliXueqiuProvider(backend, available),
            "sinafinance": OpenCliSinaFinanceProvider(backend, available),
            "bloomberg": OpenCliBloombergProvider(backend, available),
            "yahoo-finance": OpenCliYahooFinanceProvider(backend, available),
            "iwc": OpenCliIwcProvider(backend, available),
        }

    def _ordered_providers(self, capability: str, *args: Any) -> list[OpenCliFamilyProvider]:
        first_arg = args[0] if args else None
        groups = preferred_provider_groups(capability, first_arg)
        family_names = {f"opencli-{name}" for name in self._provider_map}
        ordered_names: list[str] = []
        seen: set[str] = set()

        for group in groups:
            for provider_name in group:
                if provider_name not in family_names:
                    continue
                short_name = provider_name.removeprefix("opencli-")
                if short_name in seen or short_name not in self._provider_map:
                    continue
                ordered_names.append(short_name)
                seen.add(short_name)

        for short_name in self._provider_map:
            if short_name in seen:
                continue
            ordered_names.append(short_name)
            seen.add(short_name)
        return [self._provider_map[name] for name in ordered_names if name in self._provider_map]

    def _first_supported(self, capability: str, *args: Any) -> ProviderResult:
        for provider in self._ordered_providers(capability, *args):
            handler = getattr(provider, capability)
            result = handler(*args)
            if result is not False:
                return result
        return False

    def get_search(self, query: str) -> ProviderResult:
        return self._first_supported("get_search", query)

    def get_quote(self, symbol: str) -> ProviderResult:
        return self._first_supported("get_quote", symbol)

    def get_kline(self, symbol: str, days: int = 120) -> ProviderResult:
        return self._first_supported("get_kline", symbol, days)

    def get_news(self, symbol: str | None = None) -> ProviderResult:
        items: list[dict[str, Any]] = []
        for provider in self._ordered_providers("get_news", symbol):
            result = getattr(provider, "get_news")(symbol)
            if result is False:
                continue
            items.extend(result.get("items") or [])
        if not items:
            return False
        normalized_symbol = normalize_symbol(symbol) if symbol else None
        return ensure_payload_contract(
            {"symbol": normalized_symbol, "items": items, "status": "ok"},
            capability="news",
            symbol=normalized_symbol,
        )

    def get_research(self, symbol: str) -> ProviderResult:
        result = self._first_supported("get_research", symbol)
        if result is False:
            return False
        return ensure_payload_contract(result, capability="research", symbol=normalize_symbol(symbol))

    def get_announcements(self, symbol: str, days: int = 180) -> ProviderResult:
        result = self._first_supported("get_announcements", symbol, days)
        if result is False:
            return False
        return ensure_payload_contract(result, capability="announcements", symbol=normalize_symbol(symbol))

    def get_money_flow(self, symbol: str) -> ProviderResult:
        result = self._first_supported("get_money_flow", symbol)
        if result is False:
            return False
        return ensure_payload_contract(result, capability="money_flow", symbol=normalize_symbol(symbol))

    def get_north_flow(self) -> ProviderResult:
        result = self._first_supported("get_north_flow")
        if result is False:
            return False
        return ensure_payload_contract(result, capability="north_flow")

    def get_sector_money_flow(self) -> ProviderResult:
        result = self._first_supported("get_sector_money_flow")
        if result is False:
            return False
        return ensure_payload_contract(result, capability="sector_money_flow")

    def get_sector_list(self) -> ProviderResult:
        result = self._first_supported("get_sector_list")
        if result is False:
            return False
        return ensure_payload_contract(result, capability="sector_list")

    def get_sector_members(self, sector_code: str) -> ProviderResult:
        result = self._first_supported("get_sector_members", sector_code)
        if result is False:
            return False
        return ensure_payload_contract(result, capability="sector_members")

    def get_limit_up(self, date: str | None = None) -> ProviderResult:
        result = self._first_supported("get_limit_up", date)
        if result is False:
            return False
        return ensure_payload_contract(result, capability="limit_up")

    def get_limit_down(self, date: str | None = None) -> ProviderResult:
        result = self._first_supported("get_limit_down", date)
        if result is False:
            return False
        return ensure_payload_contract(result, capability="limit_down")
