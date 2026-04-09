from __future__ import annotations

from stock_master.common.symbols import normalize_symbol

from ...interface import ProviderResult
from ...schema import ensure_payload_contract
from .base import OpenCliFamilyProvider


class OpenCliBloombergProvider(OpenCliFamilyProvider):
    def __init__(self, backend, available: bool) -> None:
        super().__init__("opencli-bloomberg", backend, available)

    def get_news(self, symbol: str | None = None) -> ProviderResult:
        items = self._fetch_standardized_items(
            ("bloomberg", "markets"),
            capability="news",
            source_channel="bloomberg.markets",
            kind="market_news",
        )
        if not items:
            return False
        normalized_symbol = normalize_symbol(symbol) if symbol else None
        return ensure_payload_contract(
            {"symbol": normalized_symbol, "items": items, "status": "ok"},
            capability="news",
            symbol=normalized_symbol,
        )
