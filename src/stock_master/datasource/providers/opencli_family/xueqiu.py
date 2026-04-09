from __future__ import annotations

from typing import Any

from stock_master.common.symbols import normalize_symbol

from ...interface import ProviderResult
from ...schema import ensure_payload_contract
from .base import OpenCliFamilyProvider


class OpenCliXueqiuProvider(OpenCliFamilyProvider):
    def __init__(self, backend, available: bool) -> None:
        super().__init__("opencli-xueqiu", backend, available)

    def get_search(self, query: str) -> ProviderResult:
        result = self._opencli_json("xueqiu", "search", query, wrap_items=True)
        if result is False:
            return False
        return self._normalize_search_payload(result, query=query, source_channel="xueqiu.search")

    def get_quote(self, symbol: str) -> ProviderResult:
        result = self._opencli_json("xueqiu", "stock", normalize_symbol(symbol))
        if result is False:
            return False
        return self._normalize_quote_payload(result, symbol=symbol, source_channel="xueqiu.stock")

    def get_kline(self, symbol: str, days: int = 120) -> ProviderResult:
        result = self._opencli_json("xueqiu", "kline", normalize_symbol(symbol), wrap_items=True)
        if result is False:
            return False
        return self._normalize_kline_payload(result, symbol=symbol, source_channel="xueqiu.kline")

    def get_news(self, symbol: str | None = None) -> ProviderResult:
        if not symbol:
            return False
        normalized = normalize_symbol(symbol)
        items = self._fetch_standardized_items(
            ("xueqiu", "comments", normalized),
            capability="news",
            source_channel="xueqiu.comments",
            kind="commentary",
        )
        if not items:
            return False
        return ensure_payload_contract(
            {"symbol": normalized, "items": items, "status": "ok"},
            capability="news",
            symbol=normalized,
        )

    def get_research(self, symbol: str) -> ProviderResult:
        normalized = normalize_symbol(symbol)
        items: list[dict[str, Any]] = []
        items.extend(
            self._fetch_standardized_items(
                ("xueqiu", "comments", normalized),
                capability="research",
                source_channel="xueqiu.comments",
                kind="research",
            )
        )
        items.extend(
            self._fetch_standardized_items(
                ("xueqiu", "earnings-date", normalized),
                capability="research",
                source_channel="xueqiu.earnings-date",
                kind="earnings_date",
            )
        )
        if not items:
            return False
        return ensure_payload_contract(
            {"symbol": normalized, "items": items, "status": "ok"},
            capability="research",
            symbol=normalized,
        )

    def get_announcements(self, symbol: str, days: int = 180) -> ProviderResult:
        normalized = normalize_symbol(symbol)
        items: list[dict[str, Any]] = []
        items.extend(
            self._fetch_standardized_items(
                ("xueqiu", "earnings-date", normalized),
                capability="announcements",
                source_channel="xueqiu.earnings-date",
                kind="announcement",
            )
        )
        items.extend(
            self._fetch_standardized_items(
                ("xueqiu", "comments", normalized),
                capability="announcements",
                source_channel="xueqiu.comments",
                kind="announcement_commentary",
            )
        )
        if not items:
            return False
        return ensure_payload_contract(
            {"symbol": normalized, "days": days, "items": items, "status": "ok"},
            capability="announcements",
            symbol=normalized,
        )
