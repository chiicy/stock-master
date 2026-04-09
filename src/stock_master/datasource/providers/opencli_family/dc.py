from __future__ import annotations

from stock_master.common.symbols import normalize_symbol

from ...interface import ProviderResult
from ...schema import ensure_payload_contract
from .base import OpenCliFamilyProvider


class OpenCliDcProvider(OpenCliFamilyProvider):
    def __init__(self, backend, available: bool) -> None:
        super().__init__("opencli-dc", backend, available)

    def get_search(self, query: str) -> ProviderResult:
        result = self._opencli_json("dc", "search", "--query", query, wrap_items=True)
        if result is False:
            return False
        return self._normalize_search_payload(result, query=query, source_channel="dc.search")

    def get_quote(self, symbol: str) -> ProviderResult:
        result = self._opencli_json("dc", "quote", "--symbol", normalize_symbol(symbol))
        if result is False:
            return False
        return self._normalize_quote_payload(result, symbol=symbol, source_channel="dc.quote")

    def get_kline(self, symbol: str, days: int = 120) -> ProviderResult:
        result = self._opencli_json("dc", "history", "--symbol", normalize_symbol(symbol), "--days", str(days), wrap_items=True)
        if result is False:
            return False
        return self._normalize_kline_payload(result, symbol=symbol, source_channel="dc.history")

    def get_money_flow(self, symbol: str) -> ProviderResult:
        normalized = normalize_symbol(symbol)
        result = self._opencli_json("dc", "stock-flow", "--symbol", normalized, wrap_items=True)
        if result is False:
            return False
        items = result.get("items") or []
        if not items:
            return False
        latest = items[-1]
        return ensure_payload_contract(
            {
                "symbol": normalized,
                "items": items,
                "latest": latest,
                "mainNetInflow": latest.get("mainNetInflow"),
                "superLargeNetInflow": latest.get("superLargeNetInflow"),
                "largeNetInflow": latest.get("largeNetInflow"),
                "mediumNetInflow": latest.get("mediumNetInflow"),
                "smallNetInflow": latest.get("smallNetInflow"),
                "source_channel": "dc.stock-flow",
            },
            capability="money_flow",
            symbol=normalized,
            source_channel="dc.stock-flow",
            include_record_raw=True,
        )

    def get_north_flow(self) -> ProviderResult:
        result = self._opencli_json("dc", "north-flow", wrap_items=True)
        if result is False:
            return False
        if isinstance(result, dict):
            result = dict(result)
            result["source_channel"] = "dc.north-flow"
        return ensure_payload_contract(
            result,
            capability="north_flow",
            source_channel="dc.north-flow",
            include_record_raw=True,
        )

    def get_sector_money_flow(self) -> ProviderResult:
        result = self._opencli_json("dc", "sector-flow", wrap_items=True)
        if result is False:
            return False
        if isinstance(result, dict):
            result = dict(result)
            result["source_channel"] = "dc.sector-flow"
        return ensure_payload_contract(
            result,
            capability="sector_money_flow",
            source_channel="dc.sector-flow",
            include_record_raw=True,
        )

    def get_sector_list(self) -> ProviderResult:
        result = self._opencli_json("dc", "search", "--query", "板块", wrap_items=True)
        if result is False:
            return False
        return self._normalize_search_payload(result, query="板块", source_channel="dc.search")

    def get_sector_members(self, sector_code: str) -> ProviderResult:
        result = self._opencli_json("dc", "sector-members", "--board_code", sector_code, "--limit", "30", wrap_items=True)
        if result is False:
            return False
        if isinstance(result, dict):
            result = dict(result)
            result["source_channel"] = "dc.sector-members"
        return ensure_payload_contract(
            result,
            capability="sector_members",
            source_channel="dc.sector-members",
            include_record_raw=True,
        )

    def get_limit_up(self, date: str | None = None) -> ProviderResult:
        result = self._opencli_json("dc", "top-gainers", "--limit", "30", wrap_items=True)
        if result is False:
            return False
        if isinstance(result, dict):
            result = dict(result)
            result["source_channel"] = "dc.top-gainers"
        return ensure_payload_contract(
            result,
            capability="limit_up",
            source_channel="dc.top-gainers",
            include_record_raw=True,
        )

    def get_limit_down(self, date: str | None = None) -> ProviderResult:
        result = self._opencli_json("dc", "top-losers", "--limit", "30", wrap_items=True)
        if result is False:
            return False
        if isinstance(result, dict):
            result = dict(result)
            result["source_channel"] = "dc.top-losers"
        return ensure_payload_contract(
            result,
            capability="limit_down",
            source_channel="dc.top-losers",
            include_record_raw=True,
        )
