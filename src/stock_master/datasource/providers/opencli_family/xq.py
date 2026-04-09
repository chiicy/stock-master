from __future__ import annotations

from stock_master.common.symbols import normalize_symbol

from ...interface import ProviderResult
from .base import OpenCliFamilyProvider


class OpenCliXqProvider(OpenCliFamilyProvider):
    def __init__(self, backend, available: bool) -> None:
        super().__init__("opencli-xq", backend, available)

    def get_search(self, query: str) -> ProviderResult:
        result = self._opencli_json("xq", "search", "--query", query, wrap_items=True)
        if result is False:
            return False
        return self._normalize_search_payload(result, query=query, source_channel="xq.search")

    def get_quote(self, symbol: str) -> ProviderResult:
        result = self._opencli_json("xq", "quote", "--symbol", normalize_symbol(symbol))
        if result is False:
            return False
        return self._normalize_quote_payload(result, symbol=symbol, source_channel="xq.quote")

    def get_kline(self, symbol: str, days: int = 120) -> ProviderResult:
        result = self._opencli_json("xq", "history", "--symbol", normalize_symbol(symbol), "--days", str(days), wrap_items=True)
        if result is False:
            return False
        return self._normalize_kline_payload(result, symbol=symbol, source_channel="xq.history")
