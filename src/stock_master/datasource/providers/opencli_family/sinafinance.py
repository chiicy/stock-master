from __future__ import annotations

from typing import Any

from stock_master.common.symbols import normalize_symbol

from ...interface import ProviderResult
from ...schema import ensure_payload_contract
from .base import OpenCliFamilyProvider


class OpenCliSinaFinanceProvider(OpenCliFamilyProvider):
    def __init__(self, backend, available: bool) -> None:
        super().__init__("opencli-sinafinance", backend, available)

    def get_quote(self, symbol: str) -> ProviderResult:
        normalized = normalize_symbol(symbol)
        if not self._is_a_share_symbol(normalized):
            return False
        result = self._opencli_json("sinafinance", "stock", normalized)
        if result is False:
            return False
        return self._normalize_quote_payload(result, symbol=symbol, source_channel="sinafinance.stock")

    def get_news(self, symbol: str | None = None) -> ProviderResult:
        items: list[dict[str, Any]] = []
        items.extend(
            self._fetch_standardized_items(
                ("sinafinance", "news"),
                capability="news",
                source_channel="sinafinance.news",
                kind="news",
            )
        )
        items.extend(
            self._fetch_standardized_items(
                ("sinafinance", "rolling-news"),
                capability="news",
                source_channel="sinafinance.rolling-news",
                kind="news_flash",
            )
        )
        if not items:
            return False
        normalized_symbol = normalize_symbol(symbol) if symbol else None
        return ensure_payload_contract(
            {"symbol": normalized_symbol, "items": items, "status": "ok"},
            capability="news",
            symbol=normalized_symbol,
        )
